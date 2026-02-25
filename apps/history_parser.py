"""
Парсер сообщений из Telegram за период 2024-2026 (Машина времени).
"""

import asyncio
import json
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta, timezone
from pyrogram import Client
from pyrogram.types import MessageEntityTextUrl
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
        
        # Загружаем Pyrogram сессию
        session_str = None
        for path in ["data/sessions/alexey_pyrogram.txt", "data/sessions/session_string_pyrogram.txt"]:
            try:
                with open(path, "r") as f:
                    content = f.read().strip()
                    if content:
                        session_str = content
                        break
            except FileNotFoundError:
                continue
        
        if session_str:
            self.client = Client(
                name="history_parser",
                api_id=self.api_id,
                api_hash=self.api_hash,
                session_string=session_str,
                in_memory=True,
                no_updates=True
            )
        else:
            import os
            os.makedirs("data/sessions", exist_ok=True)
            self.client = Client(
                name="data/sessions/history_parser",
                api_id=self.api_id,
                api_hash=self.api_hash,
                phone_number=getattr(settings, 'TELEGRAM_PHONE', None),
                no_updates=True
            )
        
        # Новый фильтр Гвен
        from systems.parser.lead_filter_advanced import LeadFilterAdvanced
        self.lead_filter = LeadFilterAdvanced()
        
        # Границы поиска (с 2024 года)
        self.start_date = datetime.now(timezone.utc)
        self.stop_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        # Основная база данных
        self.db = VacancyDatabase()

        self.seen_messages = set()
        
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
        await self.client.start()
        await self.db.init_db()
        print("✅ Машина времени подключена (Pyrogram, UNIFIED_DB)")
    
    async def parse_history(self):
        await self.initialize()
        
        print(f"\n🚀 Запуск сканирования за 2 года: {self.start_date.date()} -> {self.stop_date.date()}")
        
        target_dialogs = []
        async for d in self.client.get_dialogs():
            from pyrogram.enums import ChatType
            if d.chat.type in (ChatType.SUPERGROUP, ChatType.GROUP, ChatType.CHANNEL, ChatType.BOT):
                target_dialogs.append(d)
        
        print(f"🎯 Найдено диалогов: {len(target_dialogs)}\n")
        
        # Параллельность (5 чатов одновременно)
        semaphore = asyncio.Semaphore(5)
        
        async def process_chat(dialog, index):
            async with semaphore:
                chat_name = dialog.name or "Unknown"
                msg_count = 0
                
                try:
                    async for message in self.client.get_chat_history(d.chat.id, limit=None):
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
