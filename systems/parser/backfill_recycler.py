"""
Backfill Recycler - перерабатывает старые сообщения из базы данных.
Находит качественные лиды, которые были пропущены старыми фильтрами или у которых не было контактов.
"""

import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import List, Tuple

# Добавляем корень проекта в путь
sys.path.append(os.getcwd())

from core.config.settings import settings
from core.utils.logger import logger
from core.ai_engine.llm_client import llm_client
from systems.parser.lead_filter_advanced import LeadFilterAdvanced
from systems.parser.entity_extractor import extract_entities_hybrid
from systems.parser.vacancy_db import VacancyDatabase
from systems.parser.outreach_generator import OutreachGenerator

class BackfillRecycler:
    def __init__(self):
        self.db_path = str(settings.VACANCY_DB_PATH)
        self.history_db_path = "data/db/history_raw_messages.db"
        self.filter = LeadFilterAdvanced()
        self.vac_db = VacancyDatabase()
        self.generator = OutreachGenerator()
        
    async def recycle_leads(self, limit: int = 1000):
        """
        Перерабатывает лиды: 
        1. Rejected лиды (второй шанс).
        2. Accepted лиды без контактов (новые попытки извлечения).
        """
        logger.info(f"♻️ Запуск рециклинга лидов (limit={limit})")
        
        # 1. Сначала лиды, которые были приняты, но не имели контактов
        await self._recover_missing_contacts(limit // 2)
        
        # 2. Затем лиды, которые были отклонены (попробуем найти алмазы в мусоре)
        await self._reprocess_rejected_leads(limit // 2)
        
    async def _recover_missing_contacts(self, limit: int):
        """Пытается найти контакты в сообщениях, которые уже приняты, но помечены как no_contact_skip."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT hash, text, source, direction 
            FROM vacancies 
            WHERE status = 'accepted' AND response = 'no_contact_skip'
            ORDER BY last_seen DESC LIMIT ?
        """, (limit,))
        
        candidates = cur.fetchall()
        conn.close()
        
        if not candidates:
            logger.info("✅ Нет принятых лидов без контактов для обработки.")
            return

        recovered = 0
        for v_hash, v_text, v_source, v_dir in candidates:
            entities = extract_entities_hybrid(v_text)
            contact = entities.get("contact", {}).get("telegram")
            
            contact_link = None
            if contact:
                contact_link = contact[0] if isinstance(contact, list) else contact
            
            # Fallback к LLM если контакт важен (accepted lead)
            if not contact_link:
                try:
                    prompt = f"Извлеки контакт для связи (Telegram username или ссылка) из текста вакансии. Если контакта нет, ответь 'NONE'.\nТекст:\n{v_text}"
                    res = await llm_client.generate_response(prompt, "Ты — экстрактор контактов.")
                    if res and "NONE" not in res.upper():
                        # Чистим результат от лишнего текста
                        match = re.search(r'(@[\w\d_]+|t\.me/[\w\d_]+)', res)
                        if match:
                            contact_link = match.group(0)
                        elif len(res.strip()) < 32:
                            contact_link = res.strip()
                except Exception as e:
                    logger.error(f"LLM contact extraction failed: {e}")
            
            if not contact_link:
                # Попытка 2: Поиск в истории (Match by hash/text)
                metadata = self._match_with_history(v_hash, v_text)
                if metadata:
                    logger.info(f"🔍 Нашел метадату в истории для {v_hash[:8]}: {metadata}")
                    # Здесь мы позже добавим вызов Pyrogram для получения отправителя по msg_id
                    # Пока просто сохраним ИДишники если они нашлись
                    conn = sqlite3.connect(self.db_path)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE vacancies 
                        SET message_id = ?, source = ? 
                        WHERE hash = ?
                    """, (metadata['message_id'], metadata['chat_name'], v_hash))
                    conn.commit()
                    conn.close()

            if contact_link:
                
                # Генерируем новый черновик (с учетом возраста)
                draft = await self.generator.generate_draft(v_text, v_dir, is_old=True, is_followup=True)
                
                if draft:
                    # Если контакт найден и черновик готов — сбрасываем response
                    conn = sqlite3.connect(self.db_path)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE vacancies 
                        SET contact_link = ?, response = NULL, draft_response = ? 
                        WHERE hash = ?
                    """, (contact_link, draft, v_hash))
                    conn.commit()
                    conn.close()
                    recovered += 1
                    logger.info(f"✨ Восстановлен контакт и черновик для {v_hash[:8]}: {contact_link}")
        
        logger.info(f"📊 Итог восстановления контактов: {recovered}/{len(candidates)}")

    def _match_with_history(self, v_hash: str, v_text: str) -> dict:
        """Ищет совпадение в歴史_raw_messages.db по хешу или тексту."""
        if not os.path.exists(self.history_db_path):
            return None
            
        try:
            conn = sqlite3.connect(self.history_db_path)
            cur = conn.cursor()
            
            # 1. По хешу
            cur.execute("SELECT chat_name, message_id FROM raw_messages WHERE hash = ?", (v_hash,))
            row = cur.fetchone()
            if row:
                return {"chat_name": row[0], "message_id": row[1]}
            
            # 2. По тексту (начало)
            snippet = v_text[:100]
            cur.execute("SELECT chat_name, message_id FROM raw_messages WHERE text LIKE ?", (snippet + '%',))
            row = cur.fetchone()
            if row:
                return {"chat_name": row[0], "message_id": row[1]}
                
            return None
        except Exception as e:
            logger.error(f"History match error: {e}")
            return None
        finally:
            if 'conn' in locals(): conn.close()

    async def _reprocess_rejected_leads(self, limit: int):
        """Перепроверяет отклоненные лиды на соответствие новым фильтрам Волны 2."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Берем отклоненные лиды, которые содержат ключевые слова целевых ниш
        # Это сужает поиск до потенциально полезных.
        cur.execute("""
            SELECT hash, text, source, last_seen 
            FROM vacancies 
            WHERE status = 'rejected' 
              AND (text LIKE '%seo%' OR text LIKE '%сео%' OR text LIKE '%директ%' OR text LIKE '%авито%' OR text LIKE '%тильда%')
            ORDER BY last_seen DESC LIMIT ?
        """, (limit,))
        
        candidates = cur.fetchall()
        conn.close()
        
        if not candidates:
            logger.info("✅ Нет отклоненных лидов для повторной проверки.")
            return

        accepted = 0
        for v_hash, v_text, v_source, v_last_seen in candidates:
            # Анализируем через продвинутый фильтр
            result = await self.filter.analyze(v_text, source=v_source)
            
            if result.get("is_lead"):
                entities = result.get("entities", {})
                contact = entities.get("contact", {}).get("telegram")
                
                if contact:
                    contact_link = contact[0] if isinstance(contact, list) else contact
                    
                    # Генерируем черновик сразу
                    draft = await self.generator.generate_draft(v_text, result.get("direction"), is_old=True, is_followup=True)
                    
                    if draft:
                        conn = sqlite3.connect(self.db_path)
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE vacancies 
                            SET status = 'accepted', 
                                response = NULL, 
                                draft_response = ?,
                                contact_link = ?,
                                direction = ?,
                                tier = ?,
                                priority = ?
                            WHERE hash = ?
                        """, (
                            draft,
                            contact_link, 
                            result.get("direction", "Unknown"),
                            result.get("tier", "COLD"),
                            result.get("priority", 50),
                            v_hash
                        ))
                        conn.commit()
                        conn.close()
                        accepted += 1
                        logger.info(f"💎 Нашел пропущенный лид и создал черновик! {v_hash[:8]} -> {result.get('direction')}")

        logger.info(f"📊 Итог репроцессинга отклоненных: {accepted}/{len(candidates)} лидов возвращено в работу")

async def main():
    recycler = BackfillRecycler()
    await recycler.recycle_leads(500)

if __name__ == "__main__":
    asyncio.run(main())
