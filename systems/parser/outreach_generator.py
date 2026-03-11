"""
Outreach Generator - генерирует персонализированные черновики откликов на вакансии.
Использует личность Алексея для создания качественных офферов.
"""

import asyncio
import sqlite3
from typing import Optional, Dict
from core.ai_engine.llm_client import llm_client
from core.utils.logger import logger
from core.config.settings import settings

class OutreachGenerator:
    """Генератор откликов на основе ИИ."""
    
    SYSTEM_PROMPT = """
Ты — Алексей, опытный эксперт в digital-маркетинге (SEO, Контекстная реклама, Авито). 
Твоя задача: написать идеальный, персонализированный отклик на вакансию.

ТВОЙ СТИЛЬ:
- Профессиональный, но живой и уверенный.
- Без "канцелярщины" и пустых фраз типа "я очень ответственный".
- Акцент на результат и пользу для клиента.
- Краткость — сестра таланта. Сообщение должно быть легко читать в Telegram.

СТРУКТУРА ОТКЛИКА:
1. Приветствие (по имени, если оно есть в вакансии).
2. Если вакансия СТАРАЯ (больше 12 часов назад): Упомяни, что человек ранее искал специалиста (например, "видел, вы ранее искали...", "заметил ваш запрос на днях...").
3. Четкий аргумент, почему ты подходишь (базируясь на тексте вакансии).
4. Предложение обсудить детали или сделать экспресс-аудит (Call to action).
5. Никаких цен в первом сообщении, если не просят.

ОБЯЗАТЕЛЬНО:
- Пиши на русском языке.
- Не используй кавычки.
- Фокусируйся на специализации вакансии.
"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(settings.VACANCY_DB_PATH)

    async def generate_draft(self, vacancy_text: str, direction: str, is_old: bool = False, is_followup: bool = False) -> Optional[str]:
        """Генерирует черновик отклика."""
        logger.info(f"🎨 Генерирую черновик отклика (is_old={is_old}, is_followup={is_followup}) для направления: {direction}")
        
        status_note = ""
        if is_followup:
            status_note = "ПРИМЕЧАНИЕ: Это очень старая вакансия (из архива 2024-2025 гг). Начни сообщение строго с мысли: 'Ранее вы искали специалиста, подскажите, актуально ли в данный момент сотрудничество?'"
        elif is_old:
            status_note = "ПРИМЕЧАНИЕ: Это старая вакансия (больше 12 часов). Упомяни, что человек ранее искал специалиста."
        
        prompt = f"""
{status_note}

Напиши отклик на следующую вакансию.
Направление: {direction}
Текст вакансии:
---
{vacancy_text}
---
Пиши сразу готовое сообщение для отправки в Telegram.
"""
        try:
            draft = await llm_client.generate_response(prompt, self.SYSTEM_PROMPT)
            return draft
        except Exception as e:
            logger.error(f"Failed to generate outreach draft: {e}")
            return None

    def save_draft(self, vacancy_hash: str, draft: str):
        """Сохраняет черновик в базу данных."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE vacancies SET draft_response = ? WHERE hash = ?", (draft, vacancy_hash))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save draft to DB: {e}")
        finally:
            conn.close()

    async def process_new_vacancies(self):
        """Находит вакансии без черновиков и генерирует их. Без повторной LLM-валидации — вакансия уже прошла 7-уровневый фильтр."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hash, text, direction, source, last_seen, message_id, tier, priority
            FROM vacancies
            WHERE status = 'accepted' AND (draft_response IS NULL OR draft_response = '')
            ORDER BY last_seen DESC LIMIT 50
        """)
        pending = cursor.fetchall()
        conn.close()

        if not pending:
            return 0

        from datetime import datetime, timezone
        import dateutil.parser
        now = datetime.now(timezone.utc)
        count = 0

        for v_hash, v_text, v_dir, v_source, last_seen, v_msg_id, v_tier, v_priority in pending:
            # Нет повторной валидации — доверяем первичному фильтру
            is_old, is_followup = False, False
            try:
                dt = dateutil.parser.isoparse(last_seen)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age = (now - dt).total_seconds()
                is_followup = age > 259200   # 3 дня
                is_old = not is_followup and age > 43200  # 12 часов
            except Exception:
                pass

            # Fallback direction если не определено
            direction = v_dir or "маркетинг / digital"

            draft = await self.generate_draft(v_text, direction, is_old=is_old, is_followup=is_followup)

            if draft:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE vacancies SET draft_response = ? WHERE hash = ?",
                    (draft, v_hash)
                )
                conn.commit()
                conn.close()
                logger.info(f"✅ Черновик для {v_hash[:8]}... (dir={direction})")
                count += 1
            else:
                logger.warning(f"⚠️ LLM недоступен для {v_hash[:8]}...")

            await asyncio.sleep(0.1)

        return count


# Singleton
outreach_generator = OutreachGenerator()
