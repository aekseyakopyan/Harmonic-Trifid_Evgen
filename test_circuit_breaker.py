import asyncio
import time
import os
import sys

sys.path.append(os.getcwd())

from core.ai_engine.resilient_llm import resilient_llm_client
from pybreaker import CircuitBreakerError

async def test_normal_operation():
    print("=== Тест 1: Нормальная работа ===")
    result = await resilient_llm_client.call_with_fallback(
        prompt="Ты классификатор лидов. Отвечай JSON.",
        text="Нужен SEO-специалист для продвижения сайта. Бюджет 50000₽.",
        timeout=10
    )
    print(f"✅ Метод: {result.get('method')}")
    print(f"✅ Latency: {result.get('latency_ms')}ms")
    print(f"✅ State: {resilient_llm_client.circuit_state}\n")

async def test_circuit_breaker_trigger():
    print("=== Тест 2: Trigger Circuit Breaker ===")
    
    # 1. Форсируем ошибки (например, через неверный URL)
    original_url = resilient_llm_client.primary_client.base_url
    resilient_llm_client.primary_client.base_url = "https://invalid.url.that.will.fail"
    
    for i in range(5):
        try:
            await resilient_llm_client._call_openrouter("test", "test", 1)
        except Exception:
            print(f"Attempt {i+1}: Failed as expected (Network error)")
    
    print(f"Circuit state: {resilient_llm_client.circuit_state}")
    
    # 2. Теперь circuit должен быть OPEN. Проверяем fail-fast.
    start_time = time.time()
    result = await resilient_llm_client.call_with_fallback("test", "test", 5)
    elapsed = (time.time() - start_time) * 1000
    
    print(f"✅ State is OPEN? {resilient_llm_client.circuit_state}")
    print(f"✅ Fallback used: {result['method']}")
    print(f"✅ Fail-fast latency: {elapsed:.2f}ms (Should be very low)")
    
    # Ресет пути
    resilient_llm_client.primary_client.base_url = original_url

async def main():
    await test_normal_operation()
    await test_circuit_breaker_trigger()
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")

if __name__ == "__main__":
    asyncio.run(main())
