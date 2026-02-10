import json
import os
import sqlite3
from typing import Dict, List
from datetime import datetime, timedelta
from core.ai_engine.llm_client import llm_client
from core.utils.logger import logger
from core.config.settings import settings

class GwenLearningEngine:
    """
    Система автономного обучения Гвен.
    Анализирует вакансии и обновляет фильтры через LLM.
    """
    
    def __init__(self):
        self.db_path = "vacancies.db"
        self.filters_path = os.path.join(settings.BASE_DIR, "core/config/dynamic_filters.json")

    async def run_learning_session(self) -> Dict:
        """
        Запускает сессию обучения.
        """
        logger.info("🧠 Гвен начинает сессию самообучения...")
        
        # 1. Собираем данные из БД
        data = self._get_recent_data()
        if not data['accepted'] and not data['rejected']:
            return {"status": "skipped", "reason": "Недостаточно данных для обучения"}
            
        import re
        import json
        
        # 2. Формируем запрос к DeepSeek
        prompt = self._build_learning_prompt(data)
        
        # 3. Запрос к LLM через OpenRouter
        system_prompt = (
            "Ты — аналитик данных и эксперт по фильтрации спама. "
            "Твоя задача — проанализировать список одобренных и отклоненных вакансий "
            "и выделить новые паттерны (ключевые слова или регулярные выражения) для улучшения фильтрации. "
            "ОТВЕЧАЙ СТРОГО В ФОРМАТЕ JSON. Используй только двойные кавычки. "
            "Формат: {\"positive\": [], \"negative\": [], \"explanation\": \"\"}"
        )
        
        response_text = await llm_client.generate_response(prompt, system_prompt)
        if not response_text:
            return {"status": "error", "reason": "LLM не вернула ответ"}
            
        # 4. Парсим результат и обновляем фильтры
        try:
            # Извлекаем JSON из ответа (учитываем возможные ```json блоки)
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start == -1: 
                logger.error(f"Гвен не нашла JSON в ответе: {response_text}")
                raise ValueError("JSON not found")
            
            json_str = response_text[start:end]
            # Базовая очистка (иногда модели ставят запятые перед })
            json_str = re.sub(r',\s*}', '}', json_str)
            
            new_rules = json.loads(json_str)
            
            # Обновляем файл
            updated_count = self._update_filters(new_rules)
            
            logger.info(f"✅ Гвен успешно обновила фильтры. Добавлено: {updated_count} правил.")
            return {
                "status": "success", 
                "added_positive": new_rules.get("positive", []),
                "added_negative": new_rules.get("negative", []),
                "reason": new_rules.get("explanation", "Плановое обновление фильтров")
            }
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге правил от LLM: {e}")
            return {"status": "error", "reason": str(e)}

    def _get_recent_data(self) -> Dict:
        """Извлекает данные за текущие сутки для анализа."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Начало сегодняшнего дня (00:00)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        
        # Берем все одобренные за сегодня
        cursor.execute("SELECT text FROM vacancies WHERE status = 'accepted' AND last_seen >= ?", (today_start,))
        accepted = [row['text'] for row in cursor.fetchall()]
        
        # Берем все отклоненные (мусор) за сегодня
        cursor.execute("SELECT text FROM vacancies WHERE status = 'rejected' AND last_seen >= ?", (today_start,))
        rejected = [row['text'] for row in cursor.fetchall()]
        
        # Если за сегодня данных мало (например, утро), добираем последние 20 штук для контекста
        if len(accepted) < 5:
            cursor.execute("SELECT text FROM vacancies WHERE status = 'accepted' ORDER BY last_seen DESC LIMIT 20")
            accepted = list(set(accepted + [row['text'] for row in cursor.fetchall()]))
            
        if len(rejected) < 10:
            cursor.execute("SELECT text FROM vacancies WHERE status = 'rejected' ORDER BY last_seen DESC LIMIT 30")
            rejected = list(set(rejected + [row['text'] for row in cursor.fetchall()]))
        
        conn.close()
        return {"accepted": accepted, "rejected": rejected}

    def _build_learning_prompt(self, data: Dict) -> str:
        accepted_text = "\n---\n".join([t[:300] for t in data['accepted']])
        rejected_text = "\n---\n".join([t[:300] for t in data['rejected']])
        
        prompt = f"""
Проанализируй следующие вакансии и выдели новые ключевые слова или короткие фразы (регулярные выражения), которые помогут лучше фильтровать мусор и находить полезное.

ЦЕЛЬ: Мы ищем задачи по SEO, Контекстной рекламе (Директ), Авито (только авитолог/продвижение), Разработке сайтов (Тильда) и комплексному маркетингу.
НЕ ИНТЕРЕСНО: SMM, Email, Дизайн, Видеомонтаж, Копирайтинг (кроме SEO), Аналитика, Продажи, Поиск персонала, Инфографика, карточки маркетплейсов (WB/Ozon), чат-боты, Mini App, просто публикация объявлений или отрисовка баннеров для Авито.

✅ ПРИМЕРЫ ОДОБРЕННЫХ (Хорошие):
{accepted_text}

❌ ПРИМЕРЫ ОТКЛОНЕННЫХ (Мусор):
{rejected_text}

Выдай результат в формате JSON:
{{
  "positive": ["новое_слово1", "фраза2"],
  "negative": ["мусорное_слово1", "регулярка2"],
  "explanation": "краткое пояснение, почему добавлены эти слова"
}}

Важно: Не дублируй уже общеизвестные слова (SEO, Директ и т.д.). Ищи специфические паттерны спама или новых ниш.
"""
        return prompt

    async def expand_semantics(self) -> Dict:
        """
        Запрашивает у ИИ расширение семантического ядра (живые фразы для всех ниш).
        """
        logger.info("📡 Гвен запрашивает расширение семантики у DeepSeek...")
        
        prompt = """
Составь максимально широкий список "живых" поисковых фраз и ключевых слов для Telegram-чатов по следующим направлениям:
1. SEO (продвижение сайтов)
2. Контекстная реклама (Яндекс Директ)
3. Авито (продвижение, услуги авитолога)
4. Разработка сайтов (Тильда, лендинги, сайты под ключ)
5. Комплексный маркетинг (трафик, лиды, развитие бизнеса)

ФОРМАТ: Ищи фразы, которые пишут реальные люди («нужен сайт», «хочу в топ», «кто настроит директ», «помогите с лидами»).
ИСКЛЮЧИ: SMM, дизайн, карточки WB, чат-ботов, вакансии в штат, поиск сотрудников.

Выдай результат в формате JSON:
{
  "positive": ["фраза1", "фраза2", ...],
  "count": 0,
  "explanation": "почему выбраны эти направления"
}
Пиши только на русском. Используй только двойные кавычки. Минимум 30 фраз.
"""
        system_prompt = "Ты — эксперт по семантическому проектированию и поисковым запросам в мессенджерах."
        
        response_text = await llm_client.generate_response(prompt, system_prompt)
        if not response_text:
            return {"status": "error", "reason": "LLM не вернула ответ"}

        logger.info(f"Raw LLM response (full): {response_text}")  # Debug log

        try:
            import re
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start == -1:
                logger.error(f"JSON не найден в ответе: {response_text}")
                return {"status": "error", "reason": "JSON не найден в ответе LLM"}
            
            json_str = response_text[start:end]
            # Базовая очистка
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            new_rules = json.loads(json_str)
            
            added = self._update_filters({"positive": new_rules.get("positive", []), "negative": []})
            
            return {
                "status": "success",
                "added_count": added,
                "phrases": new_rules.get("positive", []),
                "reason": "Масштабное расширение семантического ядра"
            }
        except Exception as e:
            logger.error(f"Ошибка расширения семантики: {e}")
            return {"status": "error", "reason": str(e)}

    async def analyze_approval_reason(self, text: str) -> str:
        """
        Анализирует сообщение, которое пользователь ОДОБРИЛ.
        Помогает Гвен понять, какие именно запросы нам интересны.
        """
        prompt = f"""
        Проанализируй это сообщение, которое пользователь ОДОБРИЛ.
        Выдели главную причину (ключевое слово или нишу), почему это ХОРОШИЙ лид.
        Наши ниши: SEO, Директ, Авито (продвижение), Сайты.

        Текст сообщения:
        ---
        {text[:500]}
        ---

        Ответь кратко (до 10 слов).
        """
        try:
            # Сначала пробуем Ollama
            reason = await llm_client._generate_ollama(settings.OLLAMA_MODEL, prompt, "Ты — аналитик лидов.")
            if not reason or "error" in reason.lower() or "connection" in reason.lower():
                raise ConnectionError("Ollama is unavailable")
            
            # Если Ollama сработала, извлекаем ключевые слова
            extraction_prompt = f"Извлеки из текста выше 1–2 ключевых слова/фразы, которые делают его релевантным. Ответь только словами через запятую.\nТекст: {text[:200]}"
            keywords = await llm_client._generate_ollama(settings.OLLAMA_MODEL, extraction_prompt, "Ты — экстрактор ключевых слов.")
            
            if keywords and len(keywords) < 50:
                new_kw = [k.strip().lower() for k in keywords.split(',') if len(k.strip()) > 3]
                if new_kw:
                    self._update_filters({"positive": new_kw, "negative": []})
                    logger.info(f"✨ Гвен выучила новые ПРИОРИТЕТНЫЕ слова: {new_kw}")
            
            return reason or "Одобрено пользователем"

        except Exception as e:
            logger.warning(f"⚠️ Ollama fail in approval analysis: {e}. Switching to Cloud...")
            # Fallback на OpenRouter
            try:
                reason = await llm_client.generate_response(prompt, system_prompt="Ты — аналитик лидов. Отвечай кратко.")
                return reason or "Одобрено (Cloud)"
            except:
                return "Одобрено пользователем"

    async def analyze_spam_with_feedback(self, text: str, user_reason: str) -> str:
        """
        Анализирует спам, используя комментарий пользователя.
        Ищет подтверждение причины в тексте и обновляет фильтры.
        """
        prompt = f"""
        Пользователь отклонил этот лид с причиной: "{user_reason}".
        Проанализируй текст вакансии и найди в нем конкретные слова или фразы, которые подтверждают эту причину.
        Извлеки 1-2 самых характерных стоп-слова из текста.

        Текст вакансии:
        ---
        {text[:700]}
        ---

        Ответишь только списком слов через запятую. Если подтверждения нет, ответь "None".
        """
        try:
            # Пробуем Ollama с коротким таймаутом
            keywords = None
            try:
                keywords = await asyncio.wait_for(
                    llm_client._generate_ollama(settings.OLLAMA_MODEL, prompt, "Ты — эксперт по фильтрации спама."),
                    timeout=5.0
                )
            except:
                logger.warning("Ollama timeout/fail in feedback analysis, switching to Cloud.")
            
            # Fallback на Cloud если Ollama тупит
            if not keywords or "error" in keywords.lower() or "connection" in keywords.lower():
                keywords = await llm_client.generate_response(prompt, system_prompt="Ты — эксперт по спаму. Отвечай только списком ключевых слов.")

            if keywords and "none" not in keywords.lower() and len(keywords) < 100:
                new_kw = [k.strip().lower() for k in keywords.split(',') if len(k.strip()) > 3]
                if new_kw:
                    self._update_filters({"positive": [], "negative": new_kw})
                    logger.info(f"💾 Гвен запомнила новые стоп-слова на основе твоего фидбека: {new_kw}")
                    return f"Поняла. Выделила стоп-слова: {', '.join(new_kw)}"
            
            return "Принято. Я запомнила эту причину."
        except Exception as e:
            logger.error(f"Feedback analysis error: {e}")
            return "Запомнила."

    async def analyze_spam_reason(self, text: str) -> str:
        """Анализирует причину спама (автоматически)."""
        prompt = f"Почему этот текст - спам для digital-агентства? Ответь 1 фразой.\nТекст: {text[:300]}"
        try:
             return await llm_client.generate_response(prompt, system_prompt="Ты аналитик спама.")
        except:
             return "Помечено как спам"

    def _update_filters(self, new_rules: Dict) -> int:
        """Обновляет файл динамических фильтров."""
        if not os.path.exists(self.filters_path):
            current = {"positive": [], "negative": [], "version": 1}
        else:
            with open(self.filters_path, 'r', encoding='utf-8') as f:
                current = json.load(f)
        
        added = 0
        for key in ["positive", "negative"]:
            current_vals = set(current.get(key, []))
            for val in new_rules.get(key, []):
                if val.lower() not in current_vals:
                    current[key].append(val.lower())
                    added += 1
        
        current["last_updated"] = datetime.now().isoformat()
        
        with open(self.filters_path, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=4)
            
        return added

    async def revalidate_pending_leads(self) -> int:
        """
        Проходит по всем 'accepted' лидам, которые еще не обработаны (нет response),
        и проверяет их заново с учетом НОВЫХ фильтров (стоп-слов).
        Если находит совпадение с негативом -> меняет статус на rejected.
        
        Returns:
            int: количество отсеянных лидов.
        """
        logger.info("🧹 Гвен проводит ревалидацию очереди лидов...")
        try:
            # 1. Загружаем текущие фильтры
            if not os.path.exists(self.filters_path):
                return 0
            
            with open(self.filters_path, 'r', encoding='utf-8') as f:
                filters = json.load(f)
                negative_keywords = filters.get("negative", [])

            if not negative_keywords:
                return 0

            # 2. Берем все 'accepted' лиды без ответа
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT hash, text FROM vacancies WHERE status = 'accepted' AND (response IS NULL OR response = '')")
            pending_leads = cursor.fetchall()
            
            count_rejected = 0
            
            for lead in pending_leads:
                text_lower = lead['text'].lower()
                
                # Проверка на негатив
                found_negative = None
                for neg in negative_keywords:
                    if neg in text_lower:
                        found_negative = neg
                        break
                
                if found_negative:
                    # Нашли стоп-слово! Отклоняем.
                    logger.info(f"🧹 Ревалидация: отклонена вакансия {lead['hash']} (стоп-слово: {found_negative})")
                    cursor.execute(
                        "UPDATE vacancies SET status = 'rejected', rejection_reason = ? WHERE hash = ?", 
                        (f"AUTO_REVALIDATION: {found_negative}", lead['hash'])
                    )
                    count_rejected += 1
            
            conn.commit()
            conn.close()
            
            if count_rejected > 0:
                logger.info(f"✅ Ревалидация завершена. Очищено лидов: {count_rejected}")
            
            return count_rejected
            
        except Exception as e:
            logger.error(f"Error during revalidation: {e}")
            return 0

# Singleton
gwen_learning_engine = GwenLearningEngine()
