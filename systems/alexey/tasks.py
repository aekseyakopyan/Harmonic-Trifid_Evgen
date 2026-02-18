import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import select, and_, or_
from core.database.connection import async_session
from core.database.models import Lead, MessageLog
from core.ai_engine.llm_client import llm_client
from core.ai_engine.prompt_builder import prompt_builder
from core.utils.logger import logger
from telethon import TelegramClient
from systems.gwen import create_interceptor
from core.config.settings import settings
from core.utils.humanity import humanity_manager

# Модули анализа вакансий
from systems.parser.vacancy_analyzer import VacancyScorer, ContactExtractor, NicheDetector
from core.cases import CaseMatcher

# Настройки для автоматизации
AUTOMATED_OUTREACH_INTERVAL = 3600 # 1 hour
DRY_RUN = False # Реальная отправка включена

async def run_automated_outreach(client: TelegramClient):
    """
    Фоновая задача для автоматического поиска вакансий и отправки откликов.
    """
    # Создаём перехватчик с супервизором
    interceptor = create_interceptor(client)
    
    logger.info(f"Automated outreach task started. Dry-run: {DRY_RUN}")
    
    # Инициализация анализаторов
    scorer = VacancyScorer()
    contact_extractor = ContactExtractor()
    niche_detector = NicheDetector()
    case_matcher = CaseMatcher()
    
    while True:
        try:
            # 1. Получаем список диалогов для мониторинга
            # Проверка главного рубильника
            if not settings.OUTREACH_ENABLED:
                logger.info("Automated outreach is DISABLED in settings. Skipping cycle.")
                await asyncio.sleep(AUTOMATED_OUTREACH_INTERVAL)
                continue

            logger.info("Starting new automated outreach cycle...")
            dialogs = await client.get_dialogs()
            monitored_chats = []
            
            # Проверка тестового режима
            if settings.OUTREACH_TEST_MODE and settings.OUTREACH_TEST_CHAT_ID:
                logger.info(f"Outreach TEST MODE is ON. Only monitoring chat ID: {settings.OUTREACH_TEST_CHAT_ID}")
                for d in dialogs:
                    if d.id == settings.OUTREACH_TEST_CHAT_ID:
                        monitored_chats.append(d)
                        break
            else:
                # Обычный режим
                monitored_ids = settings.monitored_chat_ids
                for d in dialogs:
                    if monitored_ids:
                        if d.id in monitored_ids:
                            monitored_chats.append(d)
                    elif d.is_channel or d.is_group:
                        monitored_chats.append(d)
            
            logger.info(f"Monitoring {len(monitored_chats)} chats for vacancies.")
            
            for chat in monitored_chats:
                try:
                    # Извлекаем последние 10 сообщений
                    messages = await client.get_messages(chat.id, limit=10)
                    
                    for msg in messages:
                        if not msg.text or len(msg.text) < 20:
                            continue
                            
                        # 2. Анализ релевантности
                        analysis = scorer.analyze_message(msg.text, msg.date)
                        
                        if not analysis['is_vacancy'] or analysis['relevance_score'] < 3:
                            continue
                            
                        logger.info(f"Found relevant vacancy in {chat.name} (score: {analysis['relevance_score']}): {analysis['specialization']}")
                        
                        # Проверяем, не писали ли мы уже этому человеку сегодня
                        contact_data = contact_extractor.extract_contact({
                            'text': msg.text,
                            'buttons': msg.buttons,
                            'sender_id': msg.sender_id
                        })
                        
                        if contact_data['contact_type'] == 'not_found':
                            continue
                            
                        recipient = contact_data['contact_value']
                        
                        # Проверка в БД (чтобы не спамить)
                        async with async_session() as session:
                            # Ищем лид по username или telegram_id
                            clean_recipient = recipient.replace('@', '') if isinstance(recipient, str) else recipient
                            
                            lead_stmt = select(Lead).where(
                                or_(
                                    Lead.username == clean_recipient,
                                    Lead.telegram_id.cast(Lead.telegram_id.type.__class__) == clean_recipient
                                )
                            )
                            l_result = await session.execute(lead_stmt)
                            existing_lead = l_result.scalars().first()
                            
                            if existing_lead:
                                # ПРОВЕРКА: Если диалогом уже управляет человек - пропускаем
                                if getattr(existing_lead, 'is_human_managed', False):
                                    logger.info(f"Lead {recipient} is human managed. Skipping.")
                                    continue

                                # Если мы уже общались с ним последние 24 часа — пропускаем
                                if existing_lead.last_interaction > datetime.utcnow() - timedelta(days=1):
                                    continue
                        
                        logger.info(f"Targeting recipient: {recipient}")
                        
                        # 3. Подбор кейса
                        niche_data = niche_detector.detect_niche(msg.text)
                        case_data = case_matcher.find_matching_case(
                            analysis['specialization'],
                            niche_data if niche_data['niche_found'] else None
                        )
                        
                        # 4. Генерация отклика через ИИ
                        o_prompt = prompt_builder.build_outreach_prompt(
                            vacancy_text=msg.text,
                            specialization=analysis['specialization'],
                            case_data=case_data
                        )
                        
                        task_instr = "Ты — Алексей, пишешь первый отклик на вакансию. Будь честным, экспертным и живым."
                        full_system_prompt = prompt_builder.build_system_prompt(task_instr)
                        response_text = await llm_client.generate_response(o_prompt, full_system_prompt)
                        
                        if not response_text:
                            logger.error(f"Failed to generate outreach for {recipient}. All models failed.")
                            continue

                        if DRY_RUN:
                            logger.info(f"[DRY-RUN] Would send to {recipient}:\n{response_text}")
                            continue

                        # 5. Отправка (с имитацией набора)
                        try:
                            # Дополнительная проверка рубильника прямо перед отправкой
                            if not settings.OUTREACH_ENABLED:
                                logger.warning("Outreach disabled during process. Aborting send.")
                                break

                            await humanity_manager.simulate_typing(client, recipient, response_text)
                            await interceptor.send_message(recipient, response_text)
                            logger.info(f"Outreach sent to {recipient}")
                            
                            # Задержка антиспам между разными рассылками
                            import random
                            await asyncio.sleep(60 + random.randint(30, 90) * analysis['relevance_score']) 
                                
                        except Exception as e:
                            logger.error(f"Failed to send outreach to {recipient}: {e}")
                            
                except Exception as e:
                    logger.error(f"Error parsing chat {chat.id}: {e}")
                    await asyncio.sleep(5)
            
            logger.info(f"Outreach cycle finished. Sleeping for {AUTOMATED_OUTREACH_INTERVAL}s")
            await asyncio.sleep(AUTOMATED_OUTREACH_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in automated outreach task: {e}")
            # Уведомить администратора о критической ошибке в фоновой задаче
            try:
                from core.utils.admin_notifier import AdminNotifier
                notifier = AdminNotifier(client)
                await notifier.notify_error(e, "Фоновая задача: автоматическая рассылка откликов")
            except Exception as e:  
                pass
            await asyncio.sleep(300)

async def run_follow_ups(client: TelegramClient):
    """
    Background task to check and send follow-ups.
    """
    # Создаём перехватчик с супервизором
    interceptor = create_interceptor(client)
    
    while True:
        try:
            # ПРОВЕРКА РАБОЧЕГО ВРЕМЕНИ (9:00 - 19:00)
            cur_hour = datetime.now().hour
            if not (9 <= cur_hour < 19):
                logger.info(f"⏸ Вне рабочего времени ({cur_hour}:00). Follow-ups на паузе до 9:00.")
                await asyncio.sleep(1800) # Пауза 30 минут
                continue

            logger.info("Checking for follow-ups...")
            async with async_session() as session:
                now = datetime.utcnow()
                
                intervals = {
                    1: timedelta(days=1),   # Follow-up 1
                    2: timedelta(days=3),   # Follow-up 2
                    3: timedelta(days=5)    # Follow-up 3
                }
                
                for level, interval in intervals.items():
                    stmt = select(Lead).where(
                        and_(
                            Lead.follow_up_level == level - 1,
                            Lead.last_interaction < now - interval
                        )
                    )
                    
                    result = await session.execute(stmt)
                    leads_to_remind = result.scalars().all()
                    
                    for lead in leads_to_remind:
                        # ПРОВЕРКА: Если диалогом уже управляет человек - пропускаем
                        if getattr(lead, 'is_human_managed', False):
                            logger.info(f"Lead {lead.username} is human managed. Skipping follow-up.")
                            continue

                        msg_stmt = select(MessageLog).where(MessageLog.lead_id == lead.id).order_by(MessageLog.created_at.desc()).limit(1)
                        msg_result = await session.execute(msg_stmt)
                        last_msg = msg_result.scalars().first()
                        
                        if last_msg and last_msg.direction == 'outgoing':
                            logger.info(f"Sending follow-up level {level} to {lead.full_name} ({lead.telegram_id})")
                            
                            history_stmt = select(MessageLog).where(MessageLog.lead_id == lead.id).order_by(MessageLog.created_at.desc()).limit(10)
                            h_result = await session.execute(history_stmt)
                            h_msgs = h_result.scalars().all()
                            h_msgs.reverse()
                            history_text = "\n".join([f"{'Клиент' if m.direction == 'incoming' else 'Алексей'}: {m.content}" for m in h_msgs])
                            
                            f_prompt = prompt_builder.build_follow_up_prompt(
                                history_text, 
                                lead.context_memory or "", 
                                lead.style_profile or ""
                            )
                            
                            task_instr = "Ты — Алексей, пишешь вежливое напоминание."
                            full_system_prompt = prompt_builder.build_system_prompt(task_instr)
                            follow_up_text = await llm_client.generate_response(f_prompt, full_system_prompt)
                            
                            if not follow_up_text:
                                logger.error(f"Failed to generate follow-up for {lead.telegram_id}. Skipping.")
                                continue

                            sent_msg = None
                            status = "sent"
                            error_msg = None
                            
                            # Отправляем по username если есть, иначе по telegram_id
                            recipient = f"@{lead.username}" if lead.username else lead.telegram_id
                            await humanity_manager.simulate_typing(client, recipient, follow_up_text)
                            try:
                                sent_msg = await interceptor.send_message(recipient, follow_up_text)
                            except Exception as e:
                                logger.error(f"Failed to send follow-up: {e}")
                                status = "failed"
                                error_msg = str(e)
                            
                            lead.follow_up_level = level
                            lead.follow_up_sent_at = now
                            lead.last_interaction = now 
                            
                            out_msg = MessageLog(
                                lead_id=lead.id,
                                direction="outgoing",
                                content=follow_up_text,
                                intent="follow_up",
                                status=status,
                                telegram_msg_id=sent_msg.id if sent_msg else None,
                                error_message=error_msg
                            )
                            session.add(out_msg)
                            await session.commit()
                        else:
                            pass
        except Exception as e:
            logger.error(f"Error in follow-up task: {e}")
            # Уведомить администратора о критической ошибке в follow-up задаче
            try:
                from core.utils.admin_notifier import AdminNotifier
                notifier = AdminNotifier(client)
                await notifier.notify_error(e, "Фоновая задача: автоматические follow-ups")
            except Exception as e:  
                pass
            
        await asyncio.sleep(3600) 
