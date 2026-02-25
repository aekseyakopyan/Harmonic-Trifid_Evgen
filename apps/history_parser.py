"""
Парсер сообщений из Telegram за период 2024-2026 (Машина времени).
"""

import asyncio
import json
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl
from dotenv import load_dotenv

import sys
sys.path.append(os.getcwd())

from systems.parser.vacancy_analyzer.scorer import VacancyScorer
from systems.parser.vacancy_analyzer.contact_extractor import ContactExtractor
from systems.parser.vacancy_db import VacancyDatabase
from core.config.settings import settings

# Загрузка переменных окружения
load_dotenv()

class TelegramHistoryParser:
    """Парсер вакансий из Telegram за исторический период (2024+)"""
    
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        from telethon.sessions import StringSession
        with open("data/sessions/session_string_final.txt", "r") as f:
            session_str = f.read().strip()
        self.session = StringSession(session_str)
        
        # Новый фильтр Гвен
        from systems.parser.lead_filter_advanced import LeadFilterAdvanced
        self.lead_filter = LeadFilterAdvanced()
        
        # Границы поиска (с 2024 года)
        self.start_date = datetime.now(timezone.utc)
        self.stop_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        # Основная база данных
        self.db = VacancyDatabase()

        self.client = None
        self.seen_messages = set() # Дедупликация в рамках сессии
        
        self.stats = {
            'total_messages': 0,
            'total_leads': 0
        }

    def _init_databases(self):
        """Создание таблиц для сырых данных и лидов"""
        os.makedirs("data/db", exist_ok=True)
        
        # 1. RAW Database
        with sqlite3.connect(self.raw_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS raw_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_name TEXT,
                    message_id INTEGER,
                    date TEXT,
                    text TEXT,
                    hash TEXT UNIQUE
                )
            ''')
        
        # 2. LEADS Database
        with sqlite3.connect(self.leads_db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS history_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    direction TEXT,
                    text TEXT,
                    contact_link TEXT,
                    date TEXT,
                    found_at TEXT,
                    score INTEGER,
                    hash TEXT UNIQUE
                )
            ''')

    async def initialize(self):
        self.client = TelegramClient(self.session, self.api_id, self.api_hash)
        await self.client.start()
        await self.db.init_db()
        print("✅ Машина времени подключена (UNIFIED_DB)")
    
    async def parse_history(self):
        await self.initialize()
        
        print(f"\n🚀 Запуск сканирования за 2 года: {self.start_date.date()} -> {self.stop_date.date()}")
        
        dialogs = await self.client.get_dialogs(limit=None)
        target_dialogs = [d for d in dialogs if d.is_group or d.is_channel or (d.is_user and hasattr(d.entity, 'bot') and d.entity.bot)]
        
        print(f"🎯 Найдено диалогов: {len(target_dialogs)}\n")
        
        # Параллельность (5 чатов одновременно)
        semaphore = asyncio.Semaphore(5)
        
        async def process_chat(dialog, index):
            async with semaphore:
                chat_name = dialog.name or "Unknown"
                msg_count = 0
                
                try:
                    async for message in self.client.iter_messages(dialog, limit=None, offset_date=self.start_date):
                        if not message.text: continue
                        if message.date < self.stop_date: break
                        
                        msg_count += 1
                        self.stats['total_messages'] += 1
                        
                        # Сохраняем и анализируем
                        await self._process_message(message, chat_name)
                        
                        if msg_count % 1000 == 0:
                            print(f"[{index}] ⏳ {chat_name}: {msg_count} сообщений... (Дата: {message.date.date()})")

                    if msg_count > 0:
                        print(f"[{index}] ✅ Успешно: {chat_name} ({msg_count} сообщений)")
                    else:
                        print(f"[{index}] ⚪ Пусто: {chat_name}")
                        
                except Exception as e:
                    print(f"[{index}] ❌ Ошибка в {chat_name}: {e}")
                
                await asyncio.sleep(0.5)

        tasks = [process_chat(d, i+1) for i, d in enumerate(target_dialogs)]
        await asyncio.gather(*tasks)
        
        await self.client.disconnect()
        print(f"\n🏁 Финиш! Просканировано: {self.stats['total_messages']}, Найдено лидов: {self.stats['total_leads']}")

    def _get_hash(self, text):
        import hashlib
        clean_text = "".join(text.lower().split())
        return hashlib.md5(clean_text.encode()).hexdigest()

    async def _process_message(self, message, chat_name):
        text = message.text
        if not text: return
        
        # 1. Проверяем, был ли пост уже обработан
        if await self.db.is_processed(text):
            return

        # 2. Анализ через LeadFilterAdvanced (LLM + BERT)
        result = await self.lead_filter.analyze(text, message_id=message.id, chat_id=message.chat_id, source=chat_name)
        
        if result['is_lead']:
            self.stats['total_leads'] += 1
            direction = result.get('specialization', 'Unknown')
            contact_link = result.get('entities', {}).get('contact', {}).get('contact_link')
            
            # Сохраняем в основную базу
            # Статус 'accepted', но response=None, чтобы outreach_generator увидел и подготовил черновик
            await self.db.add_accepted(
                text=text,
                source=chat_name,
                direction=direction,
                contact_link=contact_link,
                date=message.date.isoformat()
            )
            print(f"   ✨ Нашелся исторический лид! ({chat_name}, {message.date.date()}) -> {direction}")
        else:
            # Опционально сохраняем в rejected, чтобы не анализировать повторно
            await self.db.add_rejected(
                text=text,
                source=chat_name,
                reason=result.get('reason', 'Historical Reject'),
                date=message.date.isoformat()
            )

async def main():
    parser = TelegramHistoryParser()
    await parser.parse_history()

if __name__ == "__main__":
    asyncio.run(main())
