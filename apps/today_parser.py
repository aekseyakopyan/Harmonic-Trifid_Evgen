"""
Парсер сообщений из Telegram за сегодня с фильтрацией вакансий по всем чатам.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl
from dotenv import load_dotenv

import sys
sys.path.append(os.getcwd())

from systems.parser.vacancy_analyzer.scorer import VacancyScorer
from systems.parser.vacancy_analyzer.contact_extractor import ContactExtractor
from systems.parser.vacancy_analyzer.niche_detector import NicheDetector
from systems.parser.vacancy_db import VacancyDatabase
from core.config.settings import settings
from core.database.connection import async_session
from core.database.models import Lead, MessageLog
from sqlalchemy import select, or_

# Загрузка переменных окружения
load_dotenv()

class TelegramVacancyParser:
    """Парсер вакансий из Telegram каналов и групп"""
    
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        from telethon.sessions import StringSession
        with open("data/sessions/session_string_final.txt", "r") as f:
            session_str = f.read().strip()
        self.session = StringSession(session_str)
        
        self.scorer = VacancyScorer()
        self.contact_extractor = ContactExtractor()
        self.niche_detector = NicheDetector()
        
        self.client = None
        self.seen_messages = set() # Для дедупликации по тексту
        self._contacted_today = set()  # Контакты, которым уже написали в этом цикле
        self.db = VacancyDatabase()  # База данных вакансий (берет путь из settings)
        self.results = {
            'parsed_at': datetime.now(timezone.utc).isoformat(),
            'total_messages_scanned': 0,
            'total_chats_scanned': 0,
            'relevant_vacancies': [],
            'irrelevant_messages': [],
            'all_messages': [] # Для полного дампа
        }
    
    async def initialize(self):
        """Инициализация Telegram клиента"""
        self.client = TelegramClient(
            self.session,
            self.api_id,
            self.api_hash
        )
        await self.client.start()
        await self.db.init_db()
        print("✅ Telegram клиент подключен")
    
    async def parse_dialogs(self, hours_ago: int = 24):
        """
        Парсит все группы и каналы пользователя за последние N часов.
        """
        await self.initialize()
        
        print(f"\n📅 Ищем сообщения во всех чатах за последние {hours_ago} часов...")
        
        # Получаем абсолютно все диалоги без лимита
        dialogs = await self.client.get_dialogs(limit=None)
        
        # Фильтруем: Исключаем только переписки с людьми. Оставляем Группы, Каналы и Ботов.
        target_dialogs = []
        for d in dialogs:
            if d.is_group or d.is_channel:
                target_dialogs.append(d)
            elif d.is_user:
                # Проверяем, бот ли это
                if hasattr(d.entity, 'bot') and d.entity.bot:
                    target_dialogs.append(d)
        
        self.results['total_chats_scanned'] = len(target_dialogs)
        print(f"🎯 Найдено подходящих источников (каналы, группы, боты): {len(target_dialogs)}\n")
        
        for i, dialog in enumerate(target_dialogs, 1):
            chat_name = dialog.name or "Без названия"
            print(f"[{i}/{len(target_dialogs)}] 🔍 Анализируем: {chat_name}")
            
            try:
                # Временная граница
                time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
                
                messages_count = 0
                # Лимит 100 сообщений на чат
                async for message in self.client.iter_messages(dialog, limit=100):
                    if not message.message:
                        continue
                    
                    # Проверка времени
                    if message.date < time_threshold:
                        break
                    
                    messages_count += 1
                    self.results['total_messages_scanned'] += 1
                    
                    # Анализ сообщения
                    await self._analyze_message(message, chat_name)
                
                if messages_count > 0:
                    print(f"   ✓ Обработано сообщений: {messages_count}")
                    
            except Exception as e:
                print(f"   ❌ Ошибка при парсинге {chat_name}: {e}")
            
            # Небольшая пауза
            await asyncio.sleep(0.05)
        
        # Сортируем по приоритету
        self.results['relevant_vacancies'].sort(
            key=lambda x: (
                0 if x['priority'] == 'HIGH' else (1 if x['priority'] == 'MEDIUM' else 2),
                -x['analysis']['relevance_score']
            )
        )
        
        await self.client.disconnect()
        print("\n✅ Парсинг завершен!")

    def _get_message_hash(self, text: str) -> str:
        """Генерирует простой хеш для дедупликации (игнорируя пробелы и регистр)"""
        import hashlib
        clean_text = "".join(text.lower().split())
        return hashlib.md5(clean_text.encode()).hexdigest()

    async def _analyze_message(self, message, channel_name: str):
        """Анализирует одно сообщение"""
        text = message.message
        
        # Дедупликация по тексту (в рамках текущего запуска)
        msg_hash = self._get_message_hash(text)
        if msg_hash in self.seen_messages:
            return # Пропускаем дубликат в рамках текущего запуска
        self.seen_messages.add(msg_hash)
        
        # Проверка в базе данных (пропускаем ранее обработанные)
        if self.db.is_processed(text):
            return  # Вакансия уже была обработана ранее
        
        # Извлекаем кнопки если есть
        buttons_text = ""
        if message.buttons:
            buttons_text = "🔘 КНОПКИ:\n"
            for row in message.buttons:
                for button in row:
                    # Проверяем все возможные атрибуты ссылки
                    link = None
                    if hasattr(button, 'url') and button.url:
                        link = button.url
                    elif hasattr(button, 'data') and button.data:
                        # Инлайновые кнопки с данными обычно не содержат прямых ссылок, 
                        # но мы можем пометить их наличие
                        pass
                    
                    if link:
                        buttons_text += f"• {button.text} → {link}\n"
                    else:
                        buttons_text += f"• {button.text} (инлайн/кнопка)\n"
        
        # Поиск Google Forms
        has_google_form = "docs.google.com/forms" in text or "forms.gle" in text or "forms.gle" in buttons_text
        
        # Анализ релевантности
        analysis = self.scorer.analyze_message(text, message.date)
        
        vacancy_data = {
            'channel': channel_name,
            'message_id': message.id,
            'date': message.date.isoformat(),
            'text': text[:500],  # Обрезаем для компактности
            'full_text': text,
            'sender_id': message.sender_id,
            'analysis': analysis,
            'has_form': has_google_form
        }
        
        if analysis['is_vacancy']:
            # Получаем информацию о пересланном сообщении
            fwd_from = None
            if message.fwd_from:
                from_id = None
                if hasattr(message.fwd_from, 'from_id'):
                    f_id = message.fwd_from.from_id
                    if hasattr(f_id, 'user_id'):
                        from_id = f_id.user_id
                    elif hasattr(f_id, 'channel_id'):
                        # Сохраняем как channel_id
                        pass
                
                fwd_from = {
                    'from_id': from_id,
                    'from_username': None, # Для получения username нужно делать дополнительный запрос GetFullUser
                    'channel_id': message.fwd_from.from_id.channel_id if hasattr(message.fwd_from, 'from_id') and hasattr(message.fwd_from.from_id, 'channel_id') else None
                }
            
            # Получаем username отправителя (только если это человек, не канал)
            sender_username = None
            sender_is_user = False
            try:
                from telethon.tl.types import User
                sender = await message.get_sender()
                if sender and isinstance(sender, User) and hasattr(sender, 'username'):
                    sender_username = sender.username
                    sender_is_user = True
            except Exception as e:  
                pass
            
            # Извлекаем контакт
            contact_data = self.contact_extractor.extract_contact({
                'text': text,
                'buttons': buttons_text,
                'sender_id': message.sender_id if sender_is_user else None,
                'fwd_from': fwd_from,
                'sender_username': sender_username
            })
            
            # Определяем нишу
            niche_data = self.niche_detector.detect_niche(text)
            
            vacancy_data['contact'] = contact_data
            vacancy_data['niche'] = niche_data
            # Буст для вакансий с формами
            vacancy_data['priority'] = self._calculate_priority(analysis, contact_data, has_google_form)
            vacancy_data['budget'] = analysis.get('budget')
            
            # Сохраняем в базу данных как принятую с направлением и контактом
            direction = analysis.get('specialization', 'Не определено')
            contact_link = contact_data.get('contact_link')
            await self.db.add_accepted(text, channel_name, direction, contact_link, message.date.isoformat())
            
            # Немедленная отправка первого сообщения лиду
            await self._send_outreach_to_lead(contact_link, text, direction)
            
            self.results['relevant_vacancies'].append(vacancy_data)
            
            status_icon = "📝 ФОРМА!" if has_google_form else "✅ Найдено!"
            print(f"   {status_icon} Score: {analysis['relevance_score']}, Spec: {analysis['specialization']}")
        else:
            # Сохраняем только краткую информацию о нерелевантных
            if analysis.get('rejection_reason'):
                self.results['irrelevant_messages'].append({
                    'channel': channel_name,
                    'message_id': message.id,
                    'rejection_reason': analysis.get('rejection_reason'),
                    'score': analysis['relevance_score']
                })
        
        # Сохраняем в базу данных как отклонённую
        if analysis.get('rejection_reason'):
            await self.db.add_rejected(
                text,
                channel_name,
                analysis.get('rejection_reason'),
                message.date.isoformat()
            )
        
        # Сохраняем ВООБЩЕ ВСЕ для полного дампа
        self.results['all_messages'].append({
            'channel': channel_name,
            'message_id': message.id,
            'date': message.date.isoformat(),
            'full_text': text,
            'is_relevant': analysis['is_vacancy'],
            'relevance_score': analysis['relevance_score'],
            'rejection_reason': analysis.get('rejection_reason')
        })

    async def _send_outreach_to_lead(self, contact_link: str, vacancy_text: str, specialization: str):
        """
        Немедленно отправляет первое сообщение лиду сразу после парсинга.
        Использует тот же Telethon клиент парсера.
        """
        if not contact_link:
            return
        
        # Защита от дублей в рамках одного цикла
        if contact_link in self._contacted_today:
            print(f"   ⏭ Уже написали {contact_link} в этом цикле, пропускаем")
            return
        
        # Проверка по базе данных (чтобы не писать повторно спустя время)
        try:
            async with async_session() as session:
                clean_contact = contact_link.replace('@', '')
                # Ищем по username или ID (если это число)
                stmt = select(Lead).where(
                    or_(
                        Lead.username == clean_contact,
                        Lead.telegram_id.cast(Lead.telegram_id.type.__class__) == clean_contact
                    )
                )
                res = await session.execute(stmt)
                lead = res.scalars().first()
                
                now = datetime.utcnow()
                
                if lead:
                    # Проверяем last_outreach_at (блокировка на 24 часа)
                    if lead.last_outreach_at and (now - lead.last_outreach_at).total_seconds() < 86400:
                        print(f"   ⏭ Лид {contact_link} уже получил сообщение недавно (last_outreach_at), пропускаем")
                        return
                    
                    # Если лид есть и было живое общение (last_interaction)
                    if lead.last_interaction and (now - lead.last_interaction).total_seconds() < 86400:
                        print(f"   ⏭ Лид {contact_link} уже есть в базе и с ним было общение, пропускаем")
                        return
                    
                    # ПРЕДВАРИТЕЛЬНОЕ РЕЗЕРВИРОВАНИЕ (Бронируем лида ПЕРЕД генерацией)
                    lead.last_outreach_at = now
                    await session.commit()
                else:
                    # Создаем нового лида и сразу бронируем его
                    lead = Lead(
                        username=clean_contact if not clean_contact.isdigit() else None,
                        telegram_id=int(clean_contact) if clean_contact.isdigit() else None,
                        full_name=contact_link,
                        last_outreach_at=now
                    )
                    session.add(lead)
                    await session.commit()
                    
        except Exception as e:
            print(f"   ⚠️ Ошибка при проверке/бронировании лида {contact_link}: {e}")
            return # Безопасность: если не смогли забронировать, не пишем
        
        try:
            from core.ai_engine.llm_client import llm_client
            from core.ai_engine.prompt_builder import prompt_builder
            import random
            
            # Генерируем текст через LLM
            prompt = prompt_builder.build_outreach_prompt(
                vacancy_text=vacancy_text,
                specialization=specialization
            )
            system = prompt_builder.build_system_prompt(
                "Ты — Алексей, пишешь первый отклик на вакансию. Будь живым, экспертным, без шаблонов."
            )
            text = await llm_client.generate_response(prompt, system)
            
            if not text:
                print(f"   ❌ LLM не сгенерировал текст для {contact_link}")
                return
            
            # Имитация человеческой задержки перед отправкой (3-10 сек)
            delay = random.uniform(3, 10)
            await asyncio.sleep(delay)
            
            # Отправка через клиент парсера
            await self.client.send_message(contact_link, text)
            self._contacted_today.add(contact_link)
            print(f"   📤 Отправлено сообщение лиду: {contact_link}")
            
            # Пауза после отправки (антиспам)
            await asyncio.sleep(random.uniform(30, 60))
            
        except Exception as e:
            print(f"   ❌ Ошибка отправки лиду {contact_link}: {e}")

    def _calculate_priority(self, analysis: dict, contact: dict, has_form: bool = False) -> str:
        """Вычисляет общий приоритет вакансии"""
        score = analysis['relevance_score']
        contact_priority = contact.get('priority_level', '3')
        
        # HIGH: Score >= 6 или контакт 1A/1B или наличие формы
        if has_form or (score >= 6 and contact_priority in ['1A', '1B']):
            return 'HIGH'
        # MEDIUM: Score >= 4
        elif score >= 4:
            return 'MEDIUM'
        else:
            return 'LOW'

    def save_results(self, filename: str):
        """Сохраняет результаты в JSON файл"""
        filepath = settings.PARSER_REPORTS_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Результаты сохранены: {filepath}")
        print(f"   📊 Всего просканировано источников: {self.results.get('total_chats_scanned', 0)}")
        print(f"   📊 Всего просканировано сообщений: {self.results['total_messages_scanned']}")
        print(f"   ✅ Релевантных вакансий: {len(self.results['relevant_vacancies'])}")

    async def generate_markdown_report(self, filename: str):
        """Генерирует подробный markdown-отчет с учётом статистики из БД."""
        # Получаем статистику из базы данных
        db_stats = await self.db.get_stats()
        filepath = settings.DAILY_REPORTS_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 📊 Отчет по вакансиям (подробный)\n\n")
            f.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Источников просканировано:** {self.results.get('total_chats_scanned', 0)}\n")
            f.write(f"**Сообщений просканировано:** {self.results.get('total_messages_scanned', 0)}\n")
            f.write(f"**Найдено вакансий:** {len(self.results['relevant_vacancies'])}\n\n")
            f.write("---\n\n")
            
            # Статистика из базы данных
            f.write("### 📊 Статистика за всё время\n\n")
            f.write(f"- **Всего обработано:** {db_stats['total']} вакансий\n")
            f.write(f"- **Принято:** {db_stats['accepted']}\n")
            f.write(f"- **Отклонено:** {db_stats['rejected']}\n\n")
            f.write("---\n\n")
            
            # База лидов (таблица)
            f.write("## 📋 База лидов\n\n")
            
            if self.results['relevant_vacancies']:
                f.write("| Время | Направление | Запрос | Контакт | Отклик |\n")
                f.write("|-------|-------------|--------|---------|--------|\n")
                
                for v in self.results['relevant_vacancies']:
                    time_str = datetime.fromisoformat(v['date']).strftime('%H:%M')
                    direction = v['analysis'].get('specialization', 'Не определено')
                    query_preview = v['text'][:50].replace('\n', ' ').replace('|', '\\|') + "..."
                    
                    # Логика отображения контакта
                    contact_data = v['contact']
                    contact_link = contact_data.get('contact_link')
                    contact_value = contact_data.get('contact_value')
                    
                    # Если ссылка не определена (например, admin_mention), пробуем подставить ID отправителя
                    # Но только если это ID ПОЛЬЗОВАТЕЛЯ (обычно положительное большое число, не -100...)
                    if not contact_link and contact_data.get('contact_type') == 'admin_mention' and v.get('sender_id'):
                        sid = v['sender_id']
                        if sid > 0: # ID пользователей обычно положительные
                            contact_link = f"tg://user?id={sid}"
                    
                    if contact_link and (contact_link.startswith('http') or contact_link.startswith('tg://')):
                        contact_display = f"[Контакт]({contact_link})"
                    elif contact_value:
                        contact_display = contact_value
                    else:
                        contact_display = "- Не определен -"
                    
                    response = "-"  # Заглушка для ручного заполнения
                    
                    f.write(f"| {time_str} | {direction} | {query_preview} | {contact_display} | {response} |\n")
                
                f.write("\n---\n\n")
            
            # Детальная информация о вакансиях
            f.write("## 📝 Детальная информация\n\n")
            
            for i, v in enumerate(self.results['relevant_vacancies'], 1):
                spec = v['analysis']['specialization'].capitalize()
                priority = v['priority']
                f.write(f"## {i}. {spec} [{priority}]\n")
                f.write(f"**Источник:** {v['channel']}\n")
                f.write(f"**Оплата:** {v.get('budget') or 'Не указана'}\n")
                f.write(f"**Контакт:** {v['contact'].get('contact_value') or 'Не найден'}\n\n")
                f.write(f"### Полный текст запроса:\n")
                f.write(f"{v['full_text']}\n\n")
                f.write("---\n\n")
            
            if self.results['irrelevant_messages']:
                f.write(f"## ❌ Отфильтрованные сообщения ({len(self.results['irrelevant_messages'])})\n")
                f.write("Эти сообщения были просканированы, но не прошли фильтры:\n\n")
                
                for m in self.results['irrelevant_messages']:
                    reason = m.get('rejection_reason', 'Причина не указана')
                    f.write(f"- **[{m['channel']}]**: {reason} (ID: {m['message_id']})\n")
        
        print(f"📄 Отчет создан: {filename}")

    def generate_full_unfiltered_report(self, filename: str):
        """Генерирует максимально полный отчет без каких-либо фильтров"""
        filepath = settings.PARSER_REPORTS_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# 📜 ПОЛНЫЙ ДАМП СООБЩЕНИЙ (БЕЗ ФИЛЬТРОВ)\n\n")
            f.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Всего сообщений в дампе:** {len(self.results['all_messages'])}\n\n")
            f.write("--- \n\n")
            
            for i, m in enumerate(self.results['all_messages'], 1):
                status = "✅ РЕЛЕВАНТНО" if m['is_relevant'] else "❌ КРАСНЫЙ ФИЛЬТР"
                f.write(f"### {i}. [{m['channel']}] (ID: {m['message_id']})\n")
                f.write(f"**Статус:** {status} | **Score:** {m['relevance_score']}\n")
                if m['rejection_reason']:
                    f.write(f"**Причина фильтра:** {m['rejection_reason']}\n")
                f.write(f"\n**ТЕКСТ:**\n{m['full_text']}\n\n")
                f.write("--- \n\n")
        
        print(f"📄 Полный дамп создан: {filename}")


async def main():
    """Главная функция мониторинга"""
    parser = TelegramVacancyParser()
    await parser.initialize()

    print(f"🚀 Запущен непрерывный мониторинг...")
    
    while True:
        try:
            start_time = datetime.now()
            print(f"\n⏰ Новый цикл сканирования: {start_time.strftime('%H:%M:%S')}")
            
            cycle_parser = TelegramVacancyParser()
            await cycle_parser.parse_dialogs(hours_ago=24)
            
            today = datetime.now().strftime("%Y-%m-%d")
            cycle_parser.save_results(f"vacancies_{today}_monitor.json")
            cycle_parser.generate_markdown_report("report_today.md")
            cycle_parser.generate_full_unfiltered_report("full_dump_today.md")
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            print(f"🏁 Цикл завершен за {duration}. Перезапуск через 10 секунд...")
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"❌ Критическая ошибка в цикле: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
