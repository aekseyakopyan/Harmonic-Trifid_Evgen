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
from core.config.settings import settings

# Загрузка переменных окружения
load_dotenv()

class TelegramHistoryParser:
    """Парсер вакансий из Telegram за исторический период (2 года)"""
    
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        from telethon.sessions import StringSession
        with open("data/sessions/session_string_final.txt", "r") as f:
            session_str = f.read().strip()
        self.session = StringSession(session_str)
        
        self.scorer = VacancyScorer()
        self.contact_extractor = ContactExtractor()
        
        # Границы поиска (2 года назад от сегодня)
        self.start_date = datetime(2026, 2, 8, tzinfo=timezone.utc)
        self.stop_date = datetime(2024, 2, 8, tzinfo=timezone.utc)
        
        # Пути к базам данных
        self.raw_db_path = "data/db/history_raw_messages.db"
        self.leads_db_path = "data/db/history_buyer_leads.db"
        self._init_databases()

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
        print("✅ Машина времени подключена (HISTORY_SESSION)")
    
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
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    async def _process_message(self, message, chat_name):
        text = message.text
        msg_hash = self._get_hash(text)
        
        # 1. В RAW базу (все)
        try:
            with sqlite3.connect(self.raw_db_path) as conn:
                conn.execute('INSERT OR IGNORE INTO raw_messages (chat_name, message_id, date, text, hash) VALUES (?,?,?,?,?)',
                             (chat_name, message.id, message.date.isoformat(), text, msg_hash))
        except Exception:
            pass

        # 2. Анализ на лида
        if msg_hash in self.seen_messages: return
        self.seen_messages.add(msg_hash)
        
        analysis = self.scorer.analyze_message(text, message.date)
        if analysis['is_vacancy']:
            self.stats['total_leads'] += 1
            contact = self.contact_extractor.extract_contact({'text': text})
            
            with sqlite3.connect(self.leads_db_path) as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO history_leads (source, direction, text, contact_link, date, found_at, score, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (chat_name, analysis.get('specialization'), text, contact.get('contact_link'), 
                      message.date.isoformat(), datetime.now().isoformat(), analysis['relevance_score'], msg_hash))

async def main():
    parser = TelegramHistoryParser()
    await parser.parse_history()

if __name__ == "__main__":
    asyncio.run(main())
