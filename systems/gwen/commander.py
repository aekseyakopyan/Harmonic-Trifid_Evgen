"""
Gwen Commander - Интерфейс команд для Мамы системы (Гвен).
Слушает команды в Telegram боте и управляет системой.
"""
import asyncio
import re
import os
import random
import sqlite3
from typing import Optional
from datetime import datetime, timedelta, timezone
from pyrogram import Client, errors
from sqlalchemy import select, func, distinct, or_
from core.database.session import async_session
from core.database.models import MessageLog, Lead
from core.config.settings import settings
from core.utils.logger import logger
from core.utils.health import health_monitor
from systems.gwen.gwen_supervisor import gwen_supervisor
from systems.parser.duplicate_detector import get_duplicate_detector

class GwenCommander:
    """
    Командный центр Гвен. Работает через SUPERVISOR_BOT_TOKEN.
    """
    
    def __init__(self, main_client: Client, db_path: str = None):
        self.db_path = db_path or str(settings.VACANCY_DB_PATH)
        self.bot_token = settings.SUPERVISOR_BOT_TOKEN
        self.chat_id = settings.SUPERVISOR_CHAT_ID
        self.main_client = main_client # Основной юзербот для рассылок
        self.bot_client = None
        self.enabled = bool(self.bot_token)
        self.waiting_for_reason = {} # user_id -> v_hash
        self.is_running = False
        self._chat_name_to_id = {} # Cache for metadata resolution
        
    async def _resolve_chat_by_name(self, name: str) -> Optional[int]:
        """Пытается найти ID чата по его экранному имени среди диалогов."""
        if not name: return None
        if name in self._chat_name_to_id:
            return self._chat_name_to_id[name]
            
        logger.info(f"🔄 Поиск Chat ID для имени: {name}")
        async for dialog in self.main_client.get_dialogs():
            d_title = getattr(dialog.chat, 'title', None) or getattr(dialog.chat, 'first_name', None)
            if d_title == name:
                self._chat_name_to_id[name] = dialog.chat.id
                return dialog.chat.id
        
        return None

    async def start(self, start_bot=True):
        """Запуск бота-командира."""
        if not self.enabled:
            logger.warning("Gwen Commander token missing. Command interface disabled.")
            return

        try:
            logger.info("🧠 Gwen Commander starting in Orchestrator mode (tasks only).")
            
            # Фоновый мониторинг здоровья (ВСЕГДА ЗАПУСКАЕМ)
            self.service_states = {"database": True, "ollama": True, "openrouter": True}
            asyncio.create_task(self.health_check_loop())
            
            # Фоновый мониторинг бэклога задач
            asyncio.create_task(self._run_backlog_check())
            
            # Фоновый мониторинг новых вакансий для Outreach
            asyncio.create_task(self._run_outreach_monitor())
            
            # Фоновое самообучение фильтрам (раз в сутки в 2:00 МСК)
            asyncio.create_task(self._run_learning_loop())
            
        except Exception as e:
            logger.error(f"Failed to start Gwen Commander: {e}")

    async def check_account_health(self) -> str:
        """
        Проверка статуса аккаунта через @SpamBot.
        """
        logger.info("🔍 Запускаю диагностику аккаунта через @SpamBot...")
        try:
            # Отправляем /start
            await self.main_client.send_message("@SpamBot", "/start")
            await asyncio.sleep(2)
            
            # Получаем последнее сообщение
            messages = []
            async for message in self.main_client.get_chat_history("@SpamBot", limit=1):
                messages.append(message)
            
            if messages:
                return messages[0].text
            return "Нет ответа от @SpamBot"
        except Exception as e:
            logger.error(f"Failed to check SpamBot: {e}")
            return f"Не удалось связаться с @SpamBot: {str(e)}"

    async def _run_outreach_monitor(self):
        """Мониторинг новых вакансий, генерация черновиков и уведомление пользователя."""
        from systems.parser.outreach_generator import outreach_generator
        from systems.gwen.notifier import supervisor_notifier
        import sqlite3
        
        while True:
            try:
                # DEBUG START
                # logger.info(f"DEBUG: Gwen Loop Start. Auto: {settings.AUTO_OUTREACH}")
                
                # 1. Генерируем черновики для новых вакансий (те, что упали из парсера)
                generated_count = await outreach_generator.process_new_vacancies()
                if generated_count > 0:
                    logger.info(f"🎨 Гвен подготовила {generated_count} новых черновиков.")
                
                # 0. Проверка: не ждет ли уже отправленный лид ответа от человека?
                # Если AUTO_OUTREACH выключен, мы работаем в режиме "по одному лиду на подтверждение"
                if not settings.AUTO_OUTREACH:
                    # Используем одно соединение для проверки и возможных действий (избегаем race condition)
                    conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM vacancies WHERE response = 'notified'")
                    pending_count = cursor.fetchone()[0]
                    conn.close()

                    if pending_count > 0:
                        # Лид уже отправлен на подтверждение — ждём реакции пользователя.
                        # Таймаут сброса можно добавить отдельной кнопкой в боте.
                        await asyncio.sleep(1)
                        continue

                # 2. Находим вакансии, о которых еще не уведомляли
                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT hash, text, direction, source, contact_link, draft_response, last_seen, tier, priority, message_id, chat_id
                    FROM vacancies 
                    WHERE status = 'accepted' AND (response IS NULL OR response = "")
                    ORDER BY last_seen DESC LIMIT 1
                """)
                new_vacancies = cursor.fetchall()
                conn.close()
                
                for v in new_vacancies:
                    v_dict = dict(v)
                    v_hash = v_dict['hash']
                    v_draft = v_dict['draft_response']
                    v_contact = v_dict['contact_link']
                    v_tier = v_dict['tier'] or 'COLD'
                    v_priority = v_dict['priority'] or 0
                    
                    # БЛОКиРОВКА: лиды без контакта бесполезны — пробуем восстановить из метадаты
                    if not v_contact or v_contact == "Не найден":
                        v_msg_id = v_dict.get('message_id')
                        v_source = v_dict.get('source') # Имя чата
                        
                        if v_msg_id and v_source:
                            try:
                                logger.info(f"🔍 Попытка восстановить контакт из метадаты: {v_source} / {v_msg_id}")
                                # Пытаемся получить сообщение через Pyrogram
                                # Сначала резолвим имя чата в ID
                                chat_id = await self._resolve_chat_by_name(v_source)
                                if not chat_id:
                                    # Пробуем саму строку если это юзернейм/ID
                                    chat_id = v_source
                                    
                                try:
                                    msg = await self.main_client.get_messages(chat_id, message_ids=[v_msg_id])
                                    if msg and len(msg) > 0 and msg[0].from_user:
                                        user = msg[0].from_user
                                        v_contact = user.username if user.username else str(user.id)
                                        logger.info(f"✨ Контакт восстановлен! {v_contact}")
                                        # Сохраняем для будущего
                                        conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE vacancies SET contact_link = ?, chat_id = ? WHERE hash = ?", (v_contact, chat_id if isinstance(chat_id, int) else None, v_hash))
                                        conn.commit()
                                        conn.close()
                                    else:
                                        raise Exception("Message or user not found")
                                except Exception as e:
                                    logger.warning(f"Failed to resolve metadata contact: {e}")
                                    v_contact = None
                            except Exception as e:
                                logger.error(f"Metadata resolution error: {e}")
                                v_contact = None

                    if not v_contact:
                        logger.info(f"⏭ Пропуск лида без контакта: {v_hash[:8]}...")
                        conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                        cursor = conn.cursor()
                        cursor.execute("UPDATE vacancies SET response = 'no_contact_skip' WHERE hash = ?", (v_hash,))
                        conn.commit()
                        conn.close()
                        continue

                    # АВТОГЕНЕРАЦИЯ ЧЕРНОВИКА если его нет
                    if not v_draft:
                        logger.info(f"📝 Черновик отсутствует для {v_hash[:8]}, генерирую...")
                        try:
                            v_draft = await outreach_generator.generate_draft(
                                v_dict.get('text', ''), v_dict.get('direction', 'Digital Marketing')
                            )
                            if v_draft:
                                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                                cursor = conn.cursor()
                                cursor.execute("UPDATE vacancies SET draft_response = ? WHERE hash = ?", (v_draft, v_hash))
                                conn.commit()
                                conn.close()
                                logger.info(f"✅ Черновик сгенерирован для {v_hash[:8]}")
                            else:
                                logger.info(f"⏭ Не удалось сгенерировать черновик: {v_hash[:8]}")
                                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                                cursor = conn.cursor()
                                cursor.execute("UPDATE vacancies SET response = 'no_draft_skip' WHERE hash = ?", (v_hash,))
                                conn.commit()
                                conn.close()
                                continue
                        except Exception as draft_err:
                            logger.error(f"Draft generation failed for {v_hash[:8]}: {draft_err}")
                            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                            cursor = conn.cursor()
                            cursor.execute("UPDATE vacancies SET response = 'no_draft_skip' WHERE hash = ?", (v_hash,))
                            conn.commit()
                            conn.close()
                            continue

                    # ПРОВЕРКА РАБОЧЕГО ВРЕМЕНИ (8:00 - 23:00)
                    cur_hour = datetime.now().hour
                    if settings.AUTO_OUTREACH and not (8 <= cur_hour < 23):
                        logger.info(f"⏸ Вне рабочего времени ({cur_hour}:00). Авто-отклик отложен до 8:00.")
                        continue

                    if settings.AUTO_OUTREACH:
                        try:
                            target = v_contact.split('/')[-1].replace('@', '').strip()
                            
                            # ПРОВЕРКА НА ДУБЛИКАТЫ В ЧАТЕ (Схожесть с прошлыми откликами)
                            is_duplicate = False
                            try:
                                async with async_session() as session:
                                    entity = await self.main_client.get_users(target)
                                    entity_id = entity.id if entity else None
                                    if not entity_id:
                                        raise Exception(f"User not found: {target}")
                                    
                                    # Ищем лид и его историю сообщений
                                    stmt = select(Lead).where(Lead.telegram_id == entity_id)
                                    res = await session.execute(stmt)
                                    lead = res.scalars().first()
                                    
                                    if lead:
                                        # Берем последние 10 исходящих сообщений с типом outreach
                                        stmt_msgs = select(MessageLog).where(
                                            MessageLog.lead_id == lead.id,
                                            MessageLog.direction == "outgoing",
                                            MessageLog.intent == "outreach"
                                        ).order_by(MessageLog.created_at.desc()).limit(10)
                                        res_msgs = await session.execute(stmt_msgs)
                                        past_messages = res_msgs.scalars().all()
                                        
                                        if past_messages:
                                            detector = get_duplicate_detector()
                                            for past_msg in past_messages:
                                                similarity = detector.calculate_semantic_similarity(v_draft, past_msg.content)
                                                if similarity > 0.85:
                                                    logger.info(f"⏭ Пропуск дубликата: Отклик в {target} слишком похож на предыдущий (sim={similarity:.2f})")
                                                    is_duplicate = True
                                                    break
                            except Exception as check_err:
                                logger.error(f"Error during duplicate outreach check: {check_err}")

                            if is_duplicate:
                                # Помечаем как пропущенный дубликат
                                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                                cursor = conn.cursor()
                                cursor.execute("UPDATE vacancies SET response = 'skipped_duplicate' WHERE hash = ?", (v_hash,))
                                conn.commit()
                                conn.close()
                                continue

                            logger.info(f"🚀 Гвен автоматически отправляет отклик в {v_contact}")
                            sent_msg = await self.main_client.send_message(target, v_draft)
                            
                            # Успешная отправка
                            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                            cursor = conn.cursor()
                            cursor.execute("UPDATE vacancies SET response = ? WHERE hash = ?", (v_draft, v_hash))
                            conn.commit()
                            conn.close()
                            
                            # ЛОГИРОВАНИЕ В ОСНОВНУЮ БД (для Дашборда)
                            try:
                                async with async_session() as session:
                                    # Получаем сущность для ID (Pyrogram)
                                    entity = await self.main_client.get_users(target)
                                    entity_id = entity.id if entity else None
                                    if not entity_id:
                                        raise Exception(f"User not found: {target}")
                                    
                                    # Ищем или создаем лид
                                    stmt = select(Lead).where(Lead.telegram_id == entity_id)
                                    res = await session.execute(stmt)
                                    lead = res.scalars().first()
                                    
                                    now = datetime.now(timezone.utc)
                                    if not lead:
                                        lead = Lead(
                                            telegram_id=entity_id,
                                            username=target if not target.isdigit() else None,
                                            full_name=getattr(entity, 'first_name', target),
                                            tier=v_tier,
                                            priority=v_priority,
                                            last_interaction=now,
                                            last_outreach_at=now
                                        )
                                        session.add(lead)
                                    else:
                                        lead.tier = v_tier
                                        lead.priority = max(lead.priority, v_priority)
                                        lead.last_interaction = now
                                        lead.last_outreach_at = now
                                    
                                    await session.commit()
                                    await session.refresh(lead)
                                    
                                    # Записываем сообщение в лог
                                    msg_log = MessageLog(
                                        lead_id=lead.id,
                                        direction="outgoing",
                                        content=v_draft,
                                        status="sent",
                                        telegram_msg_id=sent_msg.id if sent_msg else None,
                                        intent="outreach"
                                    )
                                    session.add(msg_log)
                                    await session.commit()
                                    logger.info(f"✅ Auto-outreach logged for dashboard: {target}")
                                    
                            except Exception as db_err:
                                logger.error(f"Failed to log auto-outreach to bot_data.db: {db_err}")

                            logger.info(f"✅ Авто-отклик отправлен: {v_contact}")
                            
                        except errors.FloodWait as e:
                            logger.warning(f"⏳ FloodWait: нужно подождать {e.value} сек.")
                            if e.value > 180: # Если ждать больше 3 минут
                                await supervisor_notifier.send_error(f"⏳ Гвен взяла паузу. Telegram просит подождать {e.value} секунд.")
                            await asyncio.sleep(e.value)
                            continue

                        except (errors.UserPrivacyRestricted, errors.PeerIdInvalid, errors.ChatWriteForbidden) as e:
                            logger.error(f"⚠️ Ограничение отправки для {v_contact}: {e}")
                            # Запускаем авто-диагностику через @SpamBot
                            status_report = await self.check_account_health()
                            
                            # Проверяем, есть ли реальный блок
                            is_limited = True
                            resp_check = status_report.lower()
                            if "no limits" in resp_check or "free as a bird" in resp_check or "свободен от каких-либо ограничений" in resp_check:
                                is_limited = False
                            
                            if is_limited:
                                settings.AUTO_OUTREACH = False # Выключаем автомат
                                await supervisor_notifier.send_error(
                                    "🚨 <b>ВНИМАНИЕ: СПАМ-БЛОК ПОДТВЕРЖДЕН!</b>\n\n"
                                    f"Статус от @SpamBot:\n<i>{status_report}</i>\n\n"
                                    "Автоматический режим (AUTO_OUTREACH) <b>ВЫКЛЮЧЕН</b> для спасения аккаунта."
                                )
                                return # Выходим из цикла
                            else:
                                # Ограничений нет, значит это просто приватность пользователя или невалидный ID
                                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                                cursor = conn.cursor()
                                cursor.execute("UPDATE vacancies SET response = 'failed_privacy' WHERE hash = ?", (v_hash,))
                                conn.commit()
                                conn.close()
                                continue

                        except Exception as e:
                            logger.error(f"Auto-outreach failed for {v_contact}: {e}")
                            # Помечаем лид как failed чтобы не зациклиться
                            try:
                                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                                cursor = conn.cursor()
                                cursor.execute("UPDATE vacancies SET response = 'failed' WHERE hash = ?", (v_hash,))
                                conn.commit()
                                conn.close()
                            except Exception as db_err:
                                logger.error(f"Failed to mark lead as failed: {db_err}")
                            await supervisor_notifier.send_error(f"❌ Авто-отклик не отправлен → {v_contact}\n{str(e)}")
                    else:
                        # Ручной режим (AUTO_OUTREACH=False) — отправляем на согласование
                        await supervisor_notifier.notify_new_vacancy(v_dict)

                        # Помечаем как "уведомлен"
                        conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                        cursor = conn.cursor()
                        cursor.execute("UPDATE vacancies SET response = 'notified' WHERE hash = ?", (v_hash,))
                        conn.commit()
                        conn.close()
                    
                    # Потоковый режим (по 1 лиду): пауза около 1 минуты
                    pause_time = random.randint(55, 65)
                    logger.info(f"⏳ Следующий поиск лидов через {pause_time} сек...")
                    await asyncio.sleep(pause_time)
                    
            except Exception as e:
                logger.error(f"Gwen outreach monitor error: {e}")
            
            await asyncio.sleep(30) # Пауза между проверками новых лидов (30 сек)

    async def _run_learning_loop(self):
        """Периодическое обучение Гвен."""
        from systems.gwen.learning_engine import gwen_learning_engine
        from systems.gwen.notifier import supervisor_notifier
        
        while True:
            try:
                # Проверка времени (Запуск в 2 часа ночи по МСК)
                now = datetime.now()
                if now.hour == 2 and now.minute < 30:
                    report = await gwen_learning_engine.run_learning_session()
                    
                    if report.get("status") == "success":
                        msg = (
                            "🧠 <b>Гвен обновила свои фильтры!</b>\n\n"
                            f"✅ Добавлено позитивов: {', '.join(report['added_positive']) if report['added_positive'] else '0'}\n"
                            f"❌ Добавлено негативов: {', '.join(report['added_negative']) if report['added_negative'] else '0'}\n\n"
                            f"📝 <b>Обоснование:</b>\n<i>{report['reason']}</i>"
                        )
                        await supervisor_notifier.send_error(msg)
                    
                    # Генерируем ежедневный отчет за вчерашний день
                    from systems.parser.report_generator import report_generator
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                    daily_report = report_generator.generate_daily_report(yesterday)
                    
                    if daily_report.get("status") == "success":
                        metrics = daily_report['metrics']
                        report_msg = (
                            f"📊 <b>Ежедневный отчет: {metrics['date']}</b>\n\n"
                            f"• Всего сообщений: {metrics['total_messages']}\n"
                            f"• ✅ Одобрено: {metrics['accepted']} ({metrics['acceptance_rate']}%)\n"
                            f"• ❌ Отклонено: {metrics['rejected']}\n"
                            f"• 🚀 Отправлено откликов: {metrics['sent_responses']}\n\n"
                            f"📄 Отчет: <code>{daily_report['path']}</code>"
                        )
                        await supervisor_notifier.send_error(report_msg)
                    
                    # Ждем до следующего часа, чтобы не спамить обучением в течении этого получаса
                    await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Gwen learning loop error: {e}")
            
            await asyncio.sleep(300) # Проверка каждые 5 минут

    async def handle_learn_manual(self, event):
        """Ручной запуск обучения."""
        from systems.gwen.learning_engine import gwen_learning_engine
        await event.respond("🧠 Гвен начинает внеплановый анализ данных. Это займет около минуты...")
        
        report = await gwen_learning_engine.run_learning_session()
        
        if report.get("status") == "success":
            msg = (
                "✅ <b>Обучение завершено!</b>\n\n"
                f"➕ Позитивы: {', '.join(report['added_positive']) if report['added_positive'] else 'нет'}\n"
                f"➖ Негативы: {', '.join(report['added_negative']) if report['added_negative'] else 'нет'}\n\n"
                f"📝 <b>Логика:</b> {report['reason']}"
            )
        elif report.get("status") == "skipped":
            msg = f"⏸ <b>Пропущено:</b> {report['reason']}"
        else:
            msg = f"❌ <b>Ошибка:</b> {report['reason']}"
            
        await event.respond(msg, parse_mode='html')

    async def handle_expand_manual(self, event):
        """Ручной запуск расширения семантики."""
        from systems.gwen.learning_engine import gwen_learning_engine
        await event.respond("📡 Гвен запрашивает у DeepSeek расширенную семантику для всех ниш. Это займет около минуты...")
        
        report = await gwen_learning_engine.expand_semantics()
        
        if report.get("status") == "success":
            phrases_preview = report.get('phrases', [])[:10]  # Первые 10 для превью
            total_count = report.get('added_count', 0)
            
            msg = (
                "✅ <b>Семантика расширена!</b>\n\n"
                f"📊 Добавлено фраз: {total_count}\n\n"
                f"🔍 <b>Примеры:</b>\n"
                f"<i>{', '.join(phrases_preview)}</i>\n\n"
                f"📝 <b>Обоснование:</b> {report.get('reason', 'Нет описания')}"
            )
        else:
            msg = f"❌ <b>Ошибка:</b> {report.get('reason')}"
            
        await event.respond(msg, parse_mode='html')

    async def handle_report(self, event):
        """Генерация и отправка отчета по парсингу."""
        from systems.parser.report_generator import report_generator
        import re
        
        # Проверяем, запрошен ли недельный отчет
        match = event.pattern_match
        arg = match.group(1) if match and match.group(1) else ""
        is_weekly = "week" in arg.lower() or "недел" in arg.lower()
        
        if is_weekly:
            await event.respond("📊 Генерирую недельный отчет...")
            result = report_generator.generate_weekly_report()
        else:
            await event.respond("📊 Генерирую ежедневный отчет...")
            result = report_generator.generate_daily_report()
        
        if result.get("status") == "success":
            metrics = result['metrics']
            
            if is_weekly:
                msg = (
                    f"📊 <b>Недельный отчет: {metrics['period']}</b>\n\n"
                    f"📈 <b>Общая статистика:</b>\n"
                    f"• Всего сообщений: {metrics['total_messages']}\n"
                    f"• Среднее в день: {metrics['avg_per_day']}\n"
                    f"• ✅ Одобрено: {metrics['accepted']} ({metrics['acceptance_rate']}%)\n"
                    f"• ❌ Отклонено: {metrics['rejected']}\n"
                    f"• 🚀 Отправлено откликов: {metrics['sent_responses']} ({metrics['response_rate']}%)\n\n"
                    f"📄 Полный отчет сохранен: <code>{result['path']}</code>"
                )
            else:
                msg = (
                    f"📊 <b>Ежедневный отчет: {metrics['date']}</b>\n\n"
                    f"📈 <b>Статистика:</b>\n"
                    f"• Всего сообщений: {metrics['total_messages']}\n"
                    f"• ✅ Одобрено: {metrics['accepted']} ({metrics['acceptance_rate']}%)\n"
                    f"• ❌ Отклонено: {metrics['rejected']}\n"
                    f"• 🚀 Отправлено откликов: {metrics['sent_responses']} ({metrics['response_rate']}%)\n\n"
                )
                
                if metrics['top_sources']:
                    msg += "🏆 <b>Топ-5 источников:</b>\n"
                    for i, source in enumerate(metrics['top_sources'][:5], 1):
                        msg += f"{i}. {source['source']} — {source['count']} сообщений\n"
                    msg += f"\n📄 Полный отчет: <code>{result['path']}</code>"
            
            await event.respond(msg, parse_mode='html')
            
            # Отправляем файл отчета
            try:
                await event.respond(file=result['path'])
            except Exception as e:
                logger.error(f"Failed to send report file: {e}")
        else:
            await event.respond(f"❌ <b>Ошибка генерации отчета:</b> {result.get('reason', 'Неизвестная ошибка')}", parse_mode='html')

    async def _run_backlog_check(self):
        pass

    async def handle_help(self, event):
        """Список доступных команд."""
        help_text = (
            "🧠 <b>Я — Гвен, Мать и Хранительница этой системы.</b>\n\n"
            "🗣️ <b>Я понимаю голосовые сообщения!</b>\n\n"
            "Доступные команды:\n"
            "🔹 /status — отчет о здоровье систем\n"
            "🔹 /stats — статистика блокировок и активности\n"
            "🔹 /learn — запустить обучение фильтров\n"
            "🔹 /expand — расширить семантику (живые фразы)\n"
            "🔹 /report — ежедневный отчет парсера\n"
            "🔹 /report weekly — недельный отчет парсера\n"
            "🔹 <code>/set_model [имя]</code> — сменить ИИ-модель (можно голосом)\n"
            "🔹 <code>/task [текст]</code> — задача для Антигравити (можно голосом)\n"
            "🔹 <code>/spam [контакт]</code> — забанить спамера и удалить его заказы\n"
            "🔹 <code>/outreach [N]ч [сообщение]</code> — рассылка по активным клиентам"
        )
        await event.respond(help_text, parse_mode='html')

    async def handle_chat_or_voice(self, event):
        """Обработка текстовых и голосовых сообщений."""
        text = event.message.message or ""
        
        # 0. Проверка: ждем ли мы комментарий к лиду?
        if event.sender_id in self.waiting_for_reason:
            v_hash = self.waiting_for_reason.pop(event.sender_id)
            import sqlite3
            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
            cursor = conn.cursor()
            
            # Получаем текст вакансии для анализа
            cursor.execute("SELECT text FROM vacancies WHERE hash = ?", (v_hash,))
            v_row = cursor.fetchone()
            v_text = v_row[0] if v_row else ""
            
            # Обучение Гвен на основе фидбека
            from systems.gwen.learning_engine import gwen_learning_engine
            learning_report = await gwen_learning_engine.analyze_spam_with_feedback(v_text, text)
            
            # Обновляем причину и помечаем как обработанное, чтобы разблокировать очередь
            cursor.execute("UPDATE vacancies SET status = 'rejected', rejection_reason = ?, response = 'rejected' WHERE hash = ?", (f"USER_REJECT: {text}", v_hash))
            conn.commit()
            conn.close()

            # --- ЭТАП 2: РЕВАЛИДАЦИЯ ОЧЕРЕДИ ---
            # После того как Гвен выучила новые стоп-слова, нужно пройтись по ожидающим лидам
            # и удалить те, что теперь считаются мусором.
            deleted_count = await gwen_learning_engine.revalidate_pending_leads()
            
            report_msg = f"✅ <b>Учла:</b> <i>{text}</i>\n🔍 {learning_report}"
            if deleted_count > 0:
                report_msg += f"\n\n🧹 <b>Чистка очереди:</b> Гвен автоматически отклонила еще <b>{deleted_count}</b> похожих лидов."
            
            await event.reply(report_msg, parse_mode='html')
            return

        # Пропускаем, если команда уже обработана другими хендлерами
        if event.message.message and event.message.message.startswith('/'):
            return
        
        # Если голосовое - транскрибируем
        if event.message.voice:
            await event.reply("🎧 Слушаю...")
            try:
                os.makedirs("downloads", exist_ok=True)
                file_path = await event.message.download_media(file="downloads/")
                
                from core.audio.transcriber import transcriber
                text = await transcriber.transcribe(file_path)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                if not text:
                    await event.reply("❌ Не удалось разобрать речь.")
                    return
                    
                await event.reply(f"🗣️ <b>Вы сказали:</b> <i>{text}</i>", parse_mode='html')
                
            except Exception as e:
                logger.error(f"Voice processing error: {e}")
                await event.reply("❌ Ошибка обработки голосового сообщения.")
                return

        if not text:
            return

        # Проверка на голосовые команды
        text_lower = text.lower()
        
        # 1. Смена модели
        if "поменяй модель" in text_lower or "установи модель" in text_lower:
            # Пытаемся найти название модели в тексте
            model_map = {
                "gemma": "google/gemma-2-9b-it:free",
                "llama": "meta-llama/llama-3.3-70b-instruct:free",
                "qwen": "qwen/qwen3-next-80b-a3b-instruct:free",
                "mistral": "mistralai/mistral-small-3.1-24b-instruct:free",
                "stepfun": "stepfun/step-3.5-flash:free",
            }
            
            new_model = None
            for key, val in model_map.items():
                if key in text_lower:
                    new_model = val
                    break
            
            if new_model:
                await self._change_model(event, new_model)
                return
            else:
                 await event.reply("❓ Какую модель установить? (Gemma, Llama, Qwen, Mistral)")
                 return

        # 2. Задача для Антигравити
        if "задача для антигравити" in text_lower or "задача антигравити" in text_lower:
            # Вырезаем саму задачу
            task_text = re.sub(r'задача (для )?антигравити:?', '', text_lower, flags=re.IGNORECASE).strip()
            if task_text:
                await self._save_antigravity_task(event, task_text)
                return
            else:
                await event.reply("❓ Какую задачу записать?")
                return

        # Если это не команда - отправляем в обычный ИИ-чат (существующая логика)
        await self.handle_chat(event, override_text=text)

    async def handle_set_model(self, event):
        """Команда /set_model"""
        model_name = event.pattern_match.group(1).strip()
        await self._change_model(event, model_name)

    async def handle_task(self, event):
        """Команда /task"""
        task_text = event.pattern_match.group(1).strip()
        await self._save_antigravity_task(event, task_text)

    async def _change_model(self, event, model_name):
        """Смена модели в настройках."""
        try:
            old_model = settings.OPENROUTER_MODEL
            settings.OPENROUTER_MODEL = model_name
            await event.reply(f"✅ <b>Модель изменена!</b>\n\nБыло: <code>{old_model}</code>\nСтало: <code>{model_name}</code>", parse_mode='html')
            logger.info(f"Model changed by Gwen to {model_name}")
        except Exception as e:
            await event.reply(f"❌ Ошибка смены модели: {e}")

    async def _save_antigravity_task(self, event, task_text):
        """
        Сохранение задачи в единый бэклог (backlog.md), который читает Агент.
        Это "бесшовная" интеграция: Гвен пишет, Агент видит.
        """
        try:
            # Путь к файлу в корне проекта
            backlog_path = settings.BASE_DIR / "backlog.md"
            
            # Формируем строку задачи
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_line = f"- [ ] {task_text} 🗣️ (Voice/Gwen {timestamp})\n"
            
            # Создаем или дописываем
            mode = 'a' if backlog_path.exists() else 'w'
            with open(backlog_path, mode, encoding='utf-8') as f:
                if mode == 'w':
                    f.write("# 📥 Бэклог задач (от Гвен)\n\n")
                f.write(new_line)
                
            await event.reply(f"✅ <b>Записано в Бэклог!</b>\n\n📝: <i>{task_text}</i>", parse_mode='html')
            logger.info(f"Task added to backlog.md: {task_text}")
            
        except Exception as e:
            logger.error(f"Failed to save task to backlog: {e}")
            await event.reply(f"❌ Не удалось сохранить задачу: {e}")

    async def handle_status(self, event):
        """Отчет о состоянии систем."""
        status = await health_monitor.get_full_status()
        
        status_text = (
            f"🩺 <b>Отчет о состоянии систем:</b>\n\n"
            f"{'✅' if status['database'] == 'OK' else '❌'} <b>База данных:</b> {status['database']}\n"
            f"{'☁️' if status['openrouter'] == 'OK' else '❌'} <b>OpenRouter (Cloud):</b> {status['openrouter']}\n"
            f"{'💤' if status['ollama'] == 'OK' else '🔘'} <b>Ollama (Local):</b> {status['ollama']} <i>(optional)</i>\n\n"
            f"🏁 <b>Общий статус:</b> {status['overall']}"
        )
        await event.respond(status_text, parse_mode='html')

    async def handle_stats(self, event):
        """Расширенная статистика по всем базам."""
        try:
            # 1. Статистика по активным диалогам (SQLAlchemy)
            async with async_session() as session:
                leads_count = await session.scalar(select(func.count(Lead.id)))
                today = datetime.now() - timedelta(days=1)
                msg_today = await session.scalar(select(func.count(MessageLog.id)).where(MessageLog.created_at > today))
            
            # 2. Статистика по парсеру (SQLite)
            import sqlite3
            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM vacancies GROUP BY status")
            v_stats = dict(cursor.fetchall())
            
            # Проверяем кол-во черновиков
            cursor.execute("SELECT COUNT(*) FROM vacancies WHERE draft_response IS NOT NULL AND response IS NULL")
            new_drafts = cursor.fetchone()[0]
            conn.close()
            
            stats_text = (
                f"📊 <b>Статистика системы:</b>\n\n"
                f"<b>Активные диалоги:</b>\n"
                f"👥 Лидов в базе: {leads_count}\n"
                f"✉️ Сообщений (24ч): {msg_today}\n\n"
                f"<b>Парсер вакансий:</b>\n"
                f"🔍 Всего в базе: {v_stats.get('accepted', 0) + v_stats.get('rejected', 0)}\n"
                f"✅ Принято: {v_stats.get('accepted', 0)}\n"
                f"🎨 Готовых черновиков: {new_drafts}\n"
                f"🚫 Отклонено: {v_stats.get('rejected', 0)}\n\n"
                f"🛡️ <b>Версия Гвен:</b> 2.2 (Secure Outreach)"
            )
            await event.respond(stats_text, parse_mode='html')
        except Exception as e:
            await event.respond(f"❌ Ошибка получения статистики: {e}")

    async def handle_outreach(self, event):
        """Рассылка по активным за последние N часов."""
        try:
            match = re.search(r'/outreach\s+(\d+)ч\s+(.+)', event.message.text)
            if not match:
                await event.respond("❌ Неверный формат. Используйте: <code>/outreach [N]ч [сообщение]</code>", parse_mode='html')
                return

            hours = int(match.group(1))
            message = match.group(2)
            
            await event.respond(f"🚀 <b>Гвен начинает рассылку...</b>\nЦель: клиенты активные за последние {hours}ч.\nСообщение: <i>{message}</i>", parse_mode='html')
            
            since = datetime.now() - timedelta(hours=hours)
            
            async with async_session() as session:
                # Находим лидов, с которыми общались (только входящие от них)
                stmt = select(distinct(Lead.telegram_id)).join(MessageLog).where(
                    MessageLog.created_at >= since,
                    MessageLog.direction == 'incoming'
                )
                result = await session.execute(stmt)
                leads_ids = [row[0] for row in result.all() if row[0]]
            
            if not leads_ids:
                await event.respond("🙈 Гвен не нашла лидов, писавших за этот период.")
                return

            success_count = 0
            for tg_id in leads_ids:
                try:
                    # Используем основной клиент для отправки
                    await self.main_client.send_message(tg_id, message)
                    success_count += 1
                    await asyncio.sleep(1.5) # Защита от спам-фильтра
                except Exception as e:
                    logger.error(f"Outreach failed for {tg_id}: {e}")

            await event.respond(f"✅ <b>Рассылка завершена!</b>\nДоставлено: {success_count} из {len(leads_ids)}.")
            
        except Exception as e:
            logger.error(f"Gwen outreach error: {e}")
            await event.respond(f"❌ Критический сбой рассылки: {e}")

    async def handle_spam(self, event):
        """Команда /spam [контакт] - заблокировать и пометить как спам."""
        arg = event.pattern_match.group(1)
        if not arg:
            await event.respond("❓ Укажите ник или ID для блокировки: <code>/spam @username</code>", parse_mode='html')
            return
            
        target = arg.strip().replace('@', '')
        try:
            await self.main_client.block_user(target)
            
            # Анализ причины спама (ЛОКАЛЬНО)
            from systems.gwen.learning_engine import gwen_learning_engine
            # Пытаемся найти текст сообщения в базе для анализа
            import sqlite3
            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT text FROM vacancies WHERE contact_link LIKE ? ORDER BY last_seen DESC LIMIT 1", (f'%{target}%',))
            row = cursor.fetchone()
            
            reason = "Ручная блокировка"
            if row:
                reason = await gwen_learning_engine.analyze_spam_reason(row[0])

            # Также помечаем в базе если есть такие вакансии
            cursor.execute("UPDATE vacancies SET status = 'rejected', rejection_reason = ? WHERE contact_link LIKE ?", (f"MANUAL_SPAM: {reason}", f'%{target}%'))
            conn.commit()
            conn.close()
            
            await event.respond(f"🚫 <b>{target}</b> отправлен в бан.\n🧐 <b>Анализ Гвен:</b> <i>{reason}</i>", parse_mode='html')
        except Exception as e:
            await event.respond(f"❌ Ошибка блокировки: {e}")

    async def handle_callback(self, event):
        """Обработка кнопок под откликами."""
        try:
            data = event.data.decode('utf-8')
            logger.info(f"🔘 Получен callback: {data} от {event.sender_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка декодирования callback: {e}")
            return
        
        if not data.startswith('outreach_'):
            return
            
        # Парсим действие и хеш вакансии
        # Формат: outreach_(send|edit|ignore)_(hash)
        parts = data.split('_')
        if len(parts) < 3:
            return
            
        action = parts[1]
        v_hash = parts[2]
        
        if action in ["ignore", "block", "duplicate"]:
            import sqlite3
            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
            cursor = conn.cursor()
            
            # Получаем данные вакансии
            cursor.execute("SELECT text, contact_link FROM vacancies WHERE hash = ?", (v_hash,))
            row = cursor.fetchone()
            
            if not row:
                await event.answer("❌ Вакансия не найдена", alert=True)
                conn.close()
                return

            v_text, v_contact_link = row
            status_text = ""
            rejection_reason = "MANUAL_REJECT"

            if action == "block":
                await event.answer("🚫 Пользователь заблокирован")
                rejection_reason = "MANUAL_BLOCK"
                status_text = "🚫 <b>Пользователь заблокирован.</b> Больше лидов от него не будет."
                
                # Блокируем в Телеграм (основной аккаунт)
                if v_contact_link and v_contact_link != "Не найден":
                    try:
                        contact_part = v_contact_link.split('/')[-1].replace('@', '').strip()
                        if contact_part:
                            await self.main_client.block_user(contact_part)
                            logger.info(f"🚫 Пользователь {contact_part} заблокирован")
                        else:
                            logger.warning(f"Could not extract username from {v_contact_link}")
                    except Exception as e:
                        logger.warning(f"Failed to block user: {e}")

            elif action == "duplicate":
                await event.answer("👯 Отмечено как дубль")
                rejection_reason = "DUPLICATE"
                status_text = "👯 <b>Отмечено как дубль.</b> Мы уже общались с этим заказчиком."

            elif action == "ignore":
                # Больше не анализируем автоматически ИИ
                self.waiting_for_reason[event.sender_id] = v_hash
                await event.answer("🗑 Напиши причину!")
                await event.edit("📩 <b>Помечено как СПАМ.</b>\n\n💬 Напиши кратко, <b>почему</b> этот лид не подходит? (Просто отправь текст следующим сообщением)", parse_mode='html')
                conn.close()
                return

            # Обновляем БД (для block/duplicate) - помечаем response как 'processed', чтобы очередь шла дальше
            cursor.execute("UPDATE vacancies SET status = 'rejected', rejection_reason = ?, response = 'processed' WHERE hash = ?", (rejection_reason, v_hash))
            conn.commit()
            conn.close()

            await event.edit(status_text, parse_mode='html')
            return

        # Для Send и Edit нужна информация из БД
        import sqlite3
        try:
            conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT text, draft_response, contact_link FROM vacancies WHERE hash = ?", (v_hash,))
            vacancy = cursor.fetchone()
        except Exception as e:
            logger.error(f"DB Error in callback: {e}")
            await event.answer("❌ Ошибка базы данных", alert=True)
            return
        finally:
             if 'conn' in locals(): conn.close()
        
        if not vacancy:
            await event.answer("❌ Вакансия не найдена в базе", alert=True)
            return
            
        v_text, v_draft, v_contact = vacancy
        
        if action == "send":
            # Попытка найти ЧЕЛОВЕЧЕСКИЙ контакт (@username) в тексте
            import re
            # Ищем t.me ссылки и @username
            tg_match = re.search(r'(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,32})|(?<!\w)@([a-zA-Z0-9_]{5,32})', v_text)
            
            # Если нашли юзернейм в тексте - это ВСЕГДА лучше, чем ID или "Не найден"
            if tg_match:
                username = tg_match.group(1) or tg_match.group(2)
                # Игнорируем false-positive (например, названия каналов или ботов, если они очевидны, но пока берем всё)
                # ПРИОРИТЕТ: Если в базе пусто ИЛИ там ID-ссылка (tg://user), то берем найденный юзернейм
                if not v_contact or v_contact == "Не найден" or "tg://user" in v_contact:
                     v_contact = f"https://t.me/{username}"
                     logger.info(f"🔎 Нашел (или заменил ID на) контакт из текста: {v_contact}")

            # Если контактов нет совсем - выходим СРАЗУ, не тратим время на AI
            if not v_contact or v_contact == "Не найден":
                await event.answer("⚠️ Контакт не найден.", alert=True)
                # Помечаем как accepted, но без отправки
                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                cursor = conn.cursor()
                cursor.execute("UPDATE vacancies SET status = 'accepted', response = 'no_contact_skip' WHERE hash = ?", (v_hash,))
                conn.commit()
                conn.close()
                await event.edit(f"✅ <b>Одобрено (без отправки)</b>\n\nЯ запомнила твой выбор, но отправить отклик некуда (нет контакта).", parse_mode='html')
                return

            # Возвращаем обучение Гвен на одобрении (ТОЛЬКО ЕСЛИ ЕСТЬ КОНТАКТ)
            from systems.gwen.learning_engine import gwen_learning_engine
            analysis_reason = await gwen_learning_engine.analyze_approval_reason(v_text)
            logger.info(f"✨ Гвен поняла логику одобрения: {analysis_reason}")
            
            try:
                # Если черновика нет или он помечен как SKIPPED, генерируем его ПРЯМО СЕЙЧАС
                if not v_draft or v_draft == 'SKIPPED':
                    from systems.parser.outreach_generator import outreach_generator
                    from datetime import datetime, timezone
                    import dateutil.parser
                    
                    # Проверка на старость
                    is_old = False
                    try:
                        cursor.execute("SELECT last_seen, direction FROM vacancies WHERE hash = ?", (v_hash,))
                        ls_row = cursor.fetchone()
                        if ls_row:
                            last_seen, v_dir = ls_row
                            dt = dateutil.parser.isoparse(last_seen)
                            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                            if (datetime.now(timezone.utc) - dt).total_seconds() > 43200:
                                is_old = True
                            direction = v_dir or "Digital Marketing"
                        else:
                            direction = "Digital Marketing"
                    except Exception as e:  
                        direction = "Digital Marketing"

                    await event.edit("⏳ <i>Гвен пишет черновик...</i>", parse_mode='html')
                    v_draft = await outreach_generator.generate_draft(v_text, direction, is_old=is_old)
                    
                    if not v_draft:
                        await event.answer("❌ Не удалось сгенерировать текст", alert=True)
                        return
                    
                    # Сохраняем черновик
                    conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                    cursor = conn.cursor()
                    cursor.execute("UPDATE vacancies SET draft_response = ? WHERE hash = ?", (v_draft, v_hash))
                    conn.commit()
                    conn.close()

                # Определяем получателя (username или ID)
                destination = None
                if "tg://user?id=" in v_contact:
                    try:
                        destination = int(v_contact.split('=')[-1])
                    except Exception as e:  
                        pass
                
                if not destination:
                    destination = v_contact.split('/')[-1].replace('@', '').strip()
                
                try:
                    await self.main_client.send_message(destination, v_draft)
                except ValueError as ve:
                    error_msg = str(ve)
                    if "Cannot find any entity" in error_msg or "Could not find the input entity" in error_msg or "No user has" in error_msg:
                        await event.answer("❌ Не могу найти этот контакт (нет общих чатов). Проверь вручную.", alert=True)
                        return
                    raise ve
                
                await event.answer("🚀 Отправлено!", alert=False)
                await event.edit(f"✅ <b>Отправлено в {v_contact}</b>\n🧐 <b>Анализ Гвен:</b> {analysis_reason}\n\n{v_draft}", parse_mode='html')
                
                # Помечаем в базе как отправленное
                conn = sqlite3.connect(str(settings.VACANCY_DB_PATH))
                cursor = conn.cursor()
                cursor.execute("UPDATE vacancies SET response = ? WHERE hash = ?", (v_draft, v_hash))
                conn.commit()
                conn.close()
                
            except Exception as e:
                logger.error(f"Failed to send outreach via userbot: {e}")
                await event.answer(f"❌ Ошибка: {str(e)}", alert=True)
        
        elif action == "edit":
            await event.answer("📝 Режим редактирования (функция в разработке)")
            await event.respond(f"Скопируйте и отредактируйте текст:\n\n<code>{v_draft}</code>", parse_mode='html')

    async def handle_chat(self, event, override_text=None):
        """Обработка свободного общения с Гвен."""
        # USER REQUEST: Отключен модуль общения. Гвен теперь молчит на обычные сообщения.
        return

    async def health_check_loop(self):
        """Цикл проверки здоровья систем Гвен."""
        from systems.gwen.notifier import supervisor_notifier
        logger.info("Gwen starting background health monitoring...")
        while True:
            try:
                status = await health_monitor.get_full_status()
                
                for service, state in status.items():
                    if service in ["overall", "ollama"]: continue
                    
                    is_ok = (state == "OK")
                    if is_ok != self.service_states.get(service, True):
                        self.service_states[service] = is_ok
                        icon = "✅" if is_ok else "❌"
                        msg = f"{icon} <b>Гвен сообщает:</b> Состояние сервиса <b>{service}</b> изменилось на <b>{state}</b>."
                        try:
                            await supervisor_notifier.send_error(msg)
                        except Exception as e:
                            logger.error(f"Gwen failed to send health alert: {e}")
                
            except Exception as e:
                logger.error(f"Gwen health loop error: {e}")
            
            await asyncio.sleep(60)
