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
from systems.parser.lead_filter_advanced import filter_lead_advanced

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

    def __init__(self, db_path: str = "vacancies.db"):
        self.db_path = db_path

    async def generate_draft(self, vacancy_text: str, direction: str, is_old: bool = False) -> Optional[str]:
        """Генерирует черновик отклика."""
        logger.info(f"🎨 Генерирую черновик отклика (is_old={is_old}) для направления: {direction}")
        
        status_note = "ПРИМЕЧАНИЕ: Это старая вакансия. Обязательно начни с того, что человек искал специалиста ранее." if is_old else ""
        
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
        """Находит вакансии без черновиков и генерирует их с предварительной проверкой."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Берем принятые вакансии за последние 24 часа без черновика
        cursor.execute("""
            SELECT hash, text, direction, source, last_seen, message_id 
            FROM vacancies 
            WHERE status = 'accepted' AND draft_response IS NULL
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
        
        for v_hash, v_text, v_dir, v_source, last_seen, v_msg_id in pending:
            # AI Check: Действительно ли это качественная вакансия?
            filter_result = await filter_lead_advanced(v_text, v_source, v_dir, message_id=v_msg_id or 0, use_llm_for_uncertain=True)
            is_valid = filter_result["is_lead"]
            
            if is_valid:
                # Проверка на "старость"
                is_old = False
                try:
                    dt = dateutil.parser.isoparse(last_seen)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    if (now - dt).total_seconds() > 43200: # 12 hours
                        is_old = True
                except: pass

                # Мы больше не генерируем черновики заранее для экономии ресурсов и упрощения процесса.
                # Черновик будет сгенерирован только в момент клика на кнопку "Одобрить".
                count += 1
                # Помечаем как обработанную генератором, чтобы не попадать в этот цикл снова
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE vacancies SET draft_response = 'SKIPPED' WHERE hash = ?", (v_hash,))
                conn.commit()
                conn.close()
            else:
                logger.warning(f"🚫 Гвен пометила вакансию как мусор/спам: {v_hash}")
                # Помечаем как rejected, чтобы больше не обрабатывать
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE vacancies SET status = 'rejected', rejection_reason = ? WHERE hash = ?", (filter_result.get("reason", "Advanced AI Filter Reject"), v_hash))
                conn.commit()
                conn.close()
                
            await asyncio.sleep(0.1)
        
        return count


# Singleton
outreach_generator = OutreachGenerator()
