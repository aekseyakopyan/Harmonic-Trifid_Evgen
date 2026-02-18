import asyncio
import os
import random
import aiosqlite
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession

# Настройка путей (предполагаем запуск из корня проекта)
import sys
sys.path.append(os.getcwd())

from core.config.settings import settings
from core.database.connection import async_session
from core.database.models import Lead, MessageLog
from core.ai_engine.llm_client import llm_client
from core.ai_engine.prompt_builder import prompt_builder
from core.utils.logger import logger
from core.utils.humanity import humanity_manager
from sqlalchemy import select, or_

# Настройки рассылки
LIMIT_PER_RUN = 200  # Отправляем всех за один раз
MIN_DELAY = 120    # 2 минуты
MAX_DELAY = 180    # 3 минуты

async def get_targets():
    """Получает список уникальных контактов, которым мы еще не писали."""
    targets = []
    
    # 1. Извлекаем из vacancies.db
    all_accepted = []
    async with aiosqlite.connect('data/db/vacancies.db') as db:
        cursor = await db.execute(
            "SELECT contact_link, direction, text FROM vacancies "
            "WHERE status='accepted' AND contact_link IS NOT NULL AND contact_link != ''"
        )
        all_accepted = await cursor.fetchall()

    # 2. Фильтруем через bot_data.db
    async with async_session() as session:
        for link, direction, text in all_accepted:
            clean_contact = link.replace('@', '').strip()
            if not clean_contact:
                continue
                
            # Проверка существования лида
            stmt = select(Lead).where(
                or_(
                    Lead.username == clean_contact,
                    Lead.telegram_id.cast(Lead.telegram_id.type.__class__) == clean_contact
                )
            )
            res = await session.execute(stmt)
            lead = res.scalars().first()
            
            # Если лида нет или с ним не было общения
            if not lead or not lead.last_interaction:
                targets.append({
                    'link': link,
                    'direction': direction,
                    'text': text
                })
                
    # Дедупликация в списке таргетов
    seen = set()
    unique_targets = []
    for t in targets:
        if t['link'] not in seen:
            unique_targets.append(t)
            seen.add(t['link'])
            
    return unique_targets

async def run_outreach():
    # Загрузка сессии
    try:
        with open("data/sessions/session_string_final.txt", "r") as f:
            session_str = f.read().strip()
    except Exception as e:
        print(f"Ошибка загрузки сессии: {e}")
        return

    client = TelegramClient(StringSession(session_str), settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Клиент не авторизован!")
        return

    targets = await get_targets()
    print(f"Найдено целей для рассылки: {len(targets)}")
    
    to_process = targets[:LIMIT_PER_RUN]
    print(f"Начинаю обработку первых {len(to_process)} целей...")

    for i, target in enumerate(to_process, 1):
        link = target['link']
        direction = target['direction']
        vacancy_text = target['text']
        
        print(f"[{i}/{len(to_process)}] 👉 Цель: {link} ({direction})")
        
        try:
            # 1. Генерация отклика
            prompt = prompt_builder.build_outreach_prompt(vacancy_text, direction)
            system = prompt_builder.build_system_prompt("Ты — Алексей, пишешь первый отклик на вакансию.")
            response_text = await llm_client.generate_response(prompt, system)
            
            if not response_text:
                print(f"   ❌ Ошибка генерации для {link}")
                continue
                
            # 2. Имитация набора текста
            await humanity_manager.simulate_typing(client, link, response_text)
            
            # 3. Отправка
            sent_msg = await client.send_message(link, response_text)
            print(f"   ✅ Отправлено!")

            # 4. Сохранение в БД
            async with async_session() as session:
                clean_contact = link.replace('@', '')
                # Найти или создать лид
                stmt = select(Lead).where(
                    or_(
                        Lead.username == clean_contact,
                        Lead.telegram_id.cast(Lead.telegram_id.type.__class__) == clean_contact
                    )
                )
                res = await session.execute(stmt)
                lead = res.scalars().first()
                
                if not lead:
                    lead = Lead(
                        username=clean_contact if '@' in link or not link.startswith('tg://') else None,
                        telegram_id=int(clean_contact) if clean_contact.isdigit() else None,
                        full_name=link
                    )
                    session.add(lead)
                    await session.commit()
                    await session.refresh(lead)
                
                # Лог сообщения
                msg_log = MessageLog(
                    lead_id=lead.id,
                    direction="outgoing",
                    content=response_text,
                    status="sent",
                    telegram_msg_id=sent_msg.id
                )
                lead.last_interaction = datetime.utcnow()
                session.add(msg_log)
                await session.commit()

            # 5. Задержка между лидами
            if i < len(to_process):
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                print(f"   ⏸ Пауза {delay} сек...")
                await asyncio.sleep(delay)

        except Exception as e:
            print(f"   ❌ Критическая ошибка для {link}: {e}")
            await asyncio.sleep(10)

    await client.disconnect()
    print("✨ Рассылка завершена!")

if __name__ == "__main__":
    asyncio.run(run_outreach())
