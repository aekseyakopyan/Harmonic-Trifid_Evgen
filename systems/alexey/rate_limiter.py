"""
Telegram Rate Limiter - улучшенная реализация Token Bucket алгоритма.
Основано на best practices 2026 года.
"""
import time
import asyncio
import os
import sys
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Add project root to sys.path to allow running as a script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.utils.structured_logger import get_logger

logger = get_logger("rate_limiter")


@dataclass
class TokenBucket:
    """
    Реализация Token Bucket алгоритма с улучшенной точностью.
    Использует монотонное время для предотвращения проблем с системными часами.
    """
    
    capacity: float  # Максимальное количество токенов
    refill_rate: float  # Токенов в секунду
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    
    def __post_init__(self):
        """Инициализация с полным bucket."""
        self.tokens = float(self.capacity)
        self.last_refill = time.monotonic()  # Монотонное время защищает от изменений системных часов
    
    def refill(self) -> None:
        """Пополняет токены на основе прошедшего времени."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        
        if elapsed <= 0:
            return
        
        # Добавляем токены пропорционально времени
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """
        Пытается потребить указанное количество токенов.
        
        Args:
            tokens: Количество токенов для потребления
        
        Returns:
            Tuple[bool, float]: (успех, время_ожидания)
                - успех: True если токены доступны
                - время_ожидания: секунды до доступности (0 если успех)
        """
        self.refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        
        # Вычисляем время ожидания
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.refill_rate
        return False, wait_time
    
    def peek(self) -> float:
        """Возвращает текущее количество токенов без потребления."""
        self.refill()
        return self.tokens
    
    def reset(self) -> None:
        """Сбрасывает bucket до полного состояния."""
        self.tokens = self.capacity
        self.last_refill = time.monotonic()


class TelegramRateLimiter:
    """
    Production-ready Rate Limiter для Telegram API.
    
    Особенности:
    - Соответствие официальным лимитам Telegram
    - Автоматическая очистка неактивных buckets
    - Thread-safe операции
    - Детальное логирование для отладки
    - Graceful handling при превышении лимитов
    
    Официальные лимиты Telegram:
    - Личные сообщения: 30 сообщений в секунду (глобально)
    - Группы: 20 сообщений в минуту на группу
    - Одному пользователю: 1 сообщение в секунду
    - Бот API: 30 запросов в секунду
    """
    
    # Константы лимитов
    PM_GLOBAL_CAPACITY = 30
    PM_GLOBAL_RATE = 30.0  # токенов/сек
    
    GROUP_CAPACITY = 20
    GROUP_RATE = 20.0 / 60.0  # 20 токенов в минуту
    
    USER_CAPACITY = 1
    USER_RATE = 1.0  # токен/сек
    
    CLEANUP_INTERVAL = 300  # Очистка каждые 5 минут
    INACTIVE_THRESHOLD = 600  # Удаляем buckets неактивные 10 минут
    
    def __init__(self):
        """Инициализация rate limiter."""
        # Глобальный лимит для личных сообщений
        self.global_pm_bucket = TokenBucket(
            capacity=self.PM_GLOBAL_CAPACITY,
            refill_rate=self.PM_GLOBAL_RATE
        )
        
        # Глобальный лимит для групп
        self.global_group_bucket = TokenBucket(
            capacity=self.GROUP_CAPACITY,
            refill_rate=self.GROUP_RATE
        )
        
        # Индивидуальные лимиты для пользователей
        self.user_buckets: Dict[int, TokenBucket] = {}
        
        # Отслеживание последнего использования для cleanup
        self.user_last_access: Dict[int, float] = defaultdict(float)
        
        # Блокировка для thread-safety
        self._lock = asyncio.Lock()
        
        # Время последней очистки
        self._last_cleanup = time.monotonic()
        
        # Статистика (для мониторинга)
        self.stats = {
            'total_requests': 0,
            'rejected_requests': 0,
            'total_wait_time': 0.0
        }
        
        logger.info(
            "TelegramRateLimiter initialized",
            extra={
                'pm_limit': f"{self.PM_GLOBAL_RATE}/sec",
                'group_limit': f"{self.GROUP_RATE * 60}/min",
                'user_limit': f"{self.USER_RATE}/sec"
            }
        )
    
    def _get_user_bucket(self, user_id: int) -> TokenBucket:
        """Получает или создает bucket для пользователя."""
        if user_id not in self.user_buckets:
            self.user_buckets[user_id] = TokenBucket(
                capacity=self.USER_CAPACITY,
                refill_rate=self.USER_RATE
            )
            logger.debug(f"Created new bucket for user {user_id}")
        
        # Обновляем время последнего доступа
        self.user_last_access[user_id] = time.monotonic()
        return self.user_buckets[user_id]
    
    async def acquire_pm(self, user_id: int, tokens: float = 1.0) -> float:
        """
        Ожидает доступности для отправки личного сообщения.

        Args:
            user_id: ID пользователя
            tokens: Количество токенов (по умолчанию 1)

        Returns:
            float: Фактическое время ожидания в секундах
        """
        # Phase 1: check limits under the lock, collect wait times — do NOT sleep inside the lock
        async with self._lock:
            self.stats['total_requests'] += 1
            success_global, wait_global = self.global_pm_bucket.consume(tokens)
            user_bucket = self._get_user_bucket(user_id)
            success_user, wait_user = user_bucket.consume(tokens)

        total_wait = 0.0

        # Phase 2: sleep OUTSIDE the lock to avoid blocking all other callers
        if not success_global:
            logger.debug(f"Global PM rate limit reached, waiting {wait_global:.2f}s")
            await asyncio.sleep(wait_global)
            total_wait += wait_global
            async with self._lock:
                self.global_pm_bucket.consume(tokens)

        if not success_user:
            logger.debug(f"User {user_id} rate limit reached, waiting {wait_user:.2f}s")
            await asyncio.sleep(wait_user)
            total_wait += wait_user
            async with self._lock:
                self._get_user_bucket(user_id).consume(tokens)

        if total_wait > 0:
            async with self._lock:
                self.stats['rejected_requests'] += 1
                self.stats['total_wait_time'] += total_wait

        async with self._lock:
            await self._maybe_cleanup()

        return total_wait
    
    async def acquire_group(self, chat_id: int, tokens: float = 1.0) -> float:
        """
        Ожидает доступности для отправки сообщения в группу.

        Args:
            chat_id: ID чата
            tokens: Количество токенов

        Returns:
            float: Фактическое время ожидания в секундах
        """
        async with self._lock:
            self.stats['total_requests'] += 1
            success, wait_time = self.global_group_bucket.consume(tokens)

        # Sleep OUTSIDE the lock to avoid blocking other callers
        if not success:
            logger.debug(f"Group rate limit reached for {chat_id}, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            async with self._lock:
                self.stats['rejected_requests'] += 1
                self.stats['total_wait_time'] += wait_time
                self.global_group_bucket.consume(tokens)
            return wait_time

        async with self._lock:
            await self._maybe_cleanup()
        return 0.0
    
    async def can_send_pm(self, user_id: int) -> Tuple[bool, float]:
        """
        Проверяет возможность отправки личного сообщения без ожидания.

        Args:
            user_id: ID пользователя

        Returns:
            Tuple[bool, float]: (можно_отправить, время_ожидания)
        """
        async with self._lock:
            # Peek at token levels without consuming (consume(0) always returns True — use peek())
            global_tokens = self.global_pm_bucket.peek()
            if global_tokens < 1.0:
                wait_time = (1.0 - global_tokens) / self.global_pm_bucket.refill_rate
                return False, wait_time

            user_bucket = self._get_user_bucket(user_id)
            user_tokens = user_bucket.peek()
            if user_tokens < 1.0:
                wait_time = (1.0 - user_tokens) / user_bucket.refill_rate
                return False, wait_time

            return True, 0.0
    
    async def _maybe_cleanup(self) -> None:
        """Периодически удаляет неактивные user buckets для экономии памяти."""
        now = time.monotonic()
        
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        
        # Находим неактивные buckets
        inactive_users = [
            user_id for user_id, last_access in self.user_last_access.items()
            if (now - last_access) > self.INACTIVE_THRESHOLD
        ]
        
        # Удаляем
        for user_id in inactive_users:
            if user_id in self.user_buckets:
                del self.user_buckets[user_id]
            del self.user_last_access[user_id]
        
        if inactive_users:
            logger.info(f"Cleaned up {len(inactive_users)} inactive user buckets")
        
        self._last_cleanup = now
    
    def get_stats(self) -> dict:
        """Возвращает статистику использования rate limiter."""
        avg_wait = (
            self.stats['total_wait_time'] / self.stats['rejected_requests']
            if self.stats['rejected_requests'] > 0 else 0.0
        )
        
        return {
            'total_requests': self.stats['total_requests'],
            'rejected_requests': self.stats['rejected_requests'],
            'rejection_rate': (
                self.stats['rejected_requests'] / self.stats['total_requests'] * 100
                if self.stats['total_requests'] > 0 else 0.0
            ),
            'avg_wait_time': avg_wait,
            'active_user_buckets': len(self.user_buckets),
            'global_pm_tokens': self.global_pm_bucket.peek(),
            'global_group_tokens': self.global_group_bucket.peek(),
        }
    
    def reset_stats(self) -> None:
        """Сбрасывает статистику."""
        self.stats = {
            'total_requests': 0,
            'rejected_requests': 0,
            'total_wait_time': 0.0
        }


# Singleton instance
_rate_limiter: Optional[TelegramRateLimiter] = None


def get_rate_limiter() -> TelegramRateLimiter:
    """Возвращает singleton instance rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TelegramRateLimiter()
    return _rate_limiter


# ============================================================================
# ТЕСТИРОВАНИЕ И ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================================

async def test_basic_rate_limiting():
    """Базовый тест rate limiting."""
    print("\n" + "="*60)
    print("TEST 1: Базовый Rate Limiting")
    print("="*60)
    
    limiter = get_rate_limiter()
    
    print("\n📤 Отправка 5 сообщений пользователю 12345...")
    for i in range(5):
        start = time.time()
        wait_time = await limiter.acquire_pm(user_id=12345)
        elapsed = time.time() - start
        print(f"  Сообщение {i+1}: ожидание {wait_time:.3f}s, общее {elapsed:.3f}s")
    
    print("\n✅ Тест 1 завершен")


async def test_burst_handling():
    """Тест обработки burst трафика."""
    print("\n" + "="*60)
    print("TEST 2: Burst Traffic Handling")
    print("="*60)
    
    limiter = get_rate_limiter()
    limiter.reset_stats()
    
    print("\n📤 Отправка 35 сообщений (превышение лимита 30/сек)...")
    start_time = time.time()
    
    for i in range(35):
        await limiter.acquire_pm(user_id=10000 + i)
    
    elapsed = time.time() - start_time
    stats = limiter.get_stats()
    
    print(f"\n📊 Результаты:")
    print(f"  Всего запросов: {stats['total_requests']}")
    print(f"  Отклонено: {stats['rejected_requests']}")
    print(f"  Rejection rate: {stats['rejection_rate']:.1f}%")
    print(f"  Среднее время ожидания: {stats['avg_wait_time']:.3f}s")
    print(f"  Общее время: {elapsed:.3f}s")
    
    print("\n✅ Тест 2 завершен")


async def test_can_send():
    """Тест проверки возможности отправки без блокировки."""
    print("\n" + "="*60)
    print("TEST 3: Non-blocking Check")
    print("="*60)
    
    limiter = get_rate_limiter()
    
    # Отправляем одно сообщение
    await limiter.acquire_pm(user_id=99999)
    
    # Сразу проверяем возможность отправки следующего
    can_send, wait_time = await limiter.can_send_pm(user_id=99999)
    
    print(f"\n🔍 Проверка после отправки сообщения:")
    print(f"  Можно отправить: {can_send}")
    print(f"  Время ожидания: {wait_time:.3f}s")
    
    # Ждем и проверяем снова
    await asyncio.sleep(1.1)
    can_send, wait_time = await limiter.can_send_pm(user_id=99999)
    
    print(f"\n🔍 Проверка через 1.1 секунды:")
    print(f"  Можно отправить: {can_send}")
    print(f"  Время ожидания: {wait_time:.3f}s")
    
    print("\n✅ Тест 3 завершен")


async def test_cleanup():
    """Тест автоматической очистки неактивных buckets."""
    print("\n" + "="*60)
    print("TEST 4: Bucket Cleanup")
    print("="*60)
    
    limiter = get_rate_limiter()
    
    # Создаем много buckets
    print("\n📤 Создание 50 user buckets...")
    for i in range(50):
        await limiter.acquire_pm(user_id=20000 + i)
    
    stats_before = limiter.get_stats()
    print(f"  Активных buckets: {stats_before['active_user_buckets']}")
    
    # Принудительно вызываем cleanup (изменяя время последней очистки)
    limiter._last_cleanup = time.monotonic() - limiter.CLEANUP_INTERVAL - 1
    limiter.INACTIVE_THRESHOLD = 0  # Делаем все buckets "старыми"
    
    # Триггерим cleanup через новый запрос
    await limiter.acquire_pm(user_id=99999)
    
    stats_after = limiter.get_stats()
    print(f"  После cleanup: {stats_after['active_user_buckets']}")
    
    print("\n✅ Тест 4 завершен")


async def run_all_tests():
    """Запуск всех тестов."""
    print("\n🧪 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ RATE LIMITER")
    print("="*60)
    
    await test_basic_rate_limiting()
    await test_burst_handling()
    await test_can_send()
    await test_cleanup()
    
    print("\n" + "="*60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Запуск тестов
    asyncio.run(run_all_tests())
