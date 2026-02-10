import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.custom import Message
from telethon.events import NewMessage, MessageRead, ChatAction
from systems.gwen import create_interceptor
from core.database.connection import async_session
from core.database.models import Lead, MessageLog
from sqlalchemy import select, update, and_
from core.classifier.intent_classifier import MessageClassifier
from core.ai_engine.llm_client import llm_client
from core.ai_engine.prompt_builder import prompt_builder
from core.knowledge_base.retriever import KnowledgeRetriever
from core.utils.logger import logger
from core.config.settings import settings
from core.utils.handover import handover_manager
from systems.gwen.gwen_supervisor import gwen_supervisor

# Глобальные контейнеры для накопления сообщений
message_buffers = {}
# Глобальные контейнеры для данных пользователя
user_data_cache = {}
debounce_tasks = {}

async def handle_user_action(client: TelegramClient, event: events.ChatAction.Event):
    """
    Handler for user actions like 'typing' or 'recording'.
    Resets the debounce timer to wait for completion.
    """
    sender_id = event.user_id
    if not sender_id:
        return

    # Нам интересны только начало печати или записи
    if event.typing or event.recording:
        # Обновляем время последнего действия в кеше, не затирая другие данные
        if sender_id not in user_data_cache:
            user_data_cache[sender_id] = {}
            
        user_data_cache[sender_id]['last_action_at'] = datetime.utcnow()
        # Сохраняем event только если его там нет (чтобы не затереть основной event сообщения)
        if 'event' not in user_data_cache[sender_id]:
            user_data_cache[sender_id]['event'] = event
            
        logger.debug(f"User {sender_id} is active ({'typing' if event.typing else 'recording'}). Resetting timer.")

async def handle_incoming_message(event, client: TelegramClient):
    """
    Handler for incoming messages with debouncing.
    Wait for more messages or actions from the same user.
    """
    message = event.message if hasattr(event, 'message') else event
    sender = await event.get_sender()
    sender_id = sender.id if sender else 0
    
    # Игнорируем свои собственные сообщения
    me = await client.get_me()
    if sender_id == me.id:
        return

    # 0. Извлекаем текст
    text = ""
    if message.voice:
        logger.info(f"Voice message from {sender_id}. Downloading...")
        os.makedirs("downloads", exist_ok=True)
        file_path = await message.download_media(file="downloads/")
        from core.audio.transcriber import transcriber
        text = await transcriber.transcribe(file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        text = message.text

    if not text:
        return

    # 1. Добавляем в буфер пользователя
    if sender_id not in message_buffers:
        message_buffers[sender_id] = []
    message_buffers[sender_id].append(text)

    # 2. Обновляем время последней активности
    if sender_id not in user_data_cache:
        user_data_cache[sender_id] = {}
        
    user_data_cache[sender_id].update({
        'last_action_at': datetime.utcnow(),
        'sender': sender,
        'event': event
    })

    # 3. Управляем таймером (debounce)
    if sender_id in debounce_tasks:
        debounce_tasks[sender_id].cancel()

    # Запускаем новую задачу ожидания на 10 секунд
    task = asyncio.create_task(wait_and_process(client, sender_id))
    debounce_tasks[sender_id] = task

async def wait_and_process(client, sender_id):
    """Ожидает тишины перед обработкой. Таймер динамический."""
    try:
        # 1. Определяем время ожидания (быстрее в активном диалоге)
        wait_time = 5.0 # По умолчанию
        
        async with async_session() as session:
            stmt = select(Lead).where(Lead.telegram_id == sender_id)
            res = await session.execute(stmt)
            lead = res.scalars().first()
            if lead and lead.last_interaction:
                # Если диалог активен (последнее сообщение < 5 минут назад)
                diff = (datetime.utcnow() - lead.last_interaction).total_seconds()
                if diff < 300:
                    wait_time = 2.0 # В активном чате ждать 2 сек вполне ок
                else:
                    wait_time = 5.0
            else:
                wait_time = 7.0 # При первом контакте ждем подольше (вдруг пишет простыню)
        
        while True:
            await asyncio.sleep(1) # Проверяем каждую секунду
            
            last_activity = user_data_cache.get(sender_id, {}).get('last_action_at')
            if not last_activity:
                break
                
            elapsed = (datetime.utcnow() - last_activity).total_seconds()
            if elapsed >= wait_time:
                # Тишина длилась достаточно долго — выходим из цикла и обрабатываем
                break
            else:
                # Еще нет 10 секунд тишины — продолжаем ждать
                continue
        
        # Если дождались — извлекаем всё накопленное
        texts = message_buffers.pop(sender_id, [])
        data = user_data_cache.pop(sender_id, {})
        
        if not texts:
            return
            
        full_text = "\n".join(texts)
        sender = data.get('sender')
        event = data.get('event')
        
        logger.info(f"Processing thought from {sender.first_name if sender else 'Unknown'} after 10s silence.")
        await process_full_thought(client, event, sender, full_text)
        
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in wait_and_process: {e}")
        # Уведомить администратора о критической ошибке
        try:
            from core.utils.admin_notifier import AdminNotifier
            notifier = AdminNotifier(client)
            await notifier.notify_error(
                e,
                "Обработка накопленных сообщений пользователя",
                {
                    "name": "Unknown",
                    "id": sender_id
                }
            )
        except:
            pass  # Не падаем, если уведомление не отправилось
    finally:
        if debounce_tasks.get(sender_id) == asyncio.current_task():
            debounce_tasks.pop(sender_id, None)

async def process_full_thought(client: TelegramClient, event: NewMessage.Event, sender, full_text: str):
    """Core logic to process the combined message."""
    sender_id = sender.id if sender else 0
    sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', 'Unknown')
    sender_username = getattr(sender, 'username', None)

    async with async_session() as session:
        # 1. Get or create lead
        stmt = select(Lead).where(Lead.telegram_id == sender_id)
        result = await session.execute(stmt)
        lead = result.scalars().first()
        
        if not lead:
            lead = Lead(
                telegram_id=sender_id,
                username=sender_username,
                full_name=sender_name
            )
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
        
        # Guard: Если диалог передан человеку — игнорируем входящие для ИИ
        if lead.is_human_managed:
            logger.info(f"⏸ Skipping AI processing for Lead {sender_id} (Human Managed)")
            return
            
        lead.follow_up_level = 0
        lead.follow_up_sent_at = None

        # 1.1 History
        from sqlalchemy import desc
        history_stmt = select(MessageLog).where(MessageLog.lead_id == lead.id).order_by(desc(MessageLog.created_at)).limit(10)
        history_result = await session.execute(history_stmt)
        history_msgs = history_result.scalars().all()
        history_msgs.reverse()
        
        history_items = []
        for m in history_msgs:
            role = "ТЫ (Алексей)" if m.direction == "outgoing" else "КЛИЕНТ"
            history_items.append(f"{role}: {m.content}")
        history_text = "\n".join(history_items)

        # 2. Classify
        classifier = MessageClassifier()
        classification = await classifier.classify(full_text)
        
        # 3. Context
        retriever = KnowledgeRetriever(session)
        cases = await retriever.find_relevant_cases(full_text)
        service = await retriever.find_service_by_category(classification.get("category", ""))
        
        # 3.1 KB Search (B2B Sales Materials)
        sales_materials = await retriever.search_markdown_kb(full_text)

        # 3.2 Web Search if needed
        external_cases = []
        if len(cases) < 2 and classification.get("category") not in ["general", None]:
            from core.knowledge_base.web_searcher import web_searcher
            niche = full_text # Simplification: use full_text as niche context
            service_name = service.name if service else classification.get("category")
            external_cases = await web_searcher.search_cases(niche, service_name)

        # 4. Prompt
        # 4.1 Dynamic Emotion Selection based on tone and history
        tone = classification.get("tone", "neutral")
        if "hurry" in tone:
            current_emotion = "interested" # Если клиент торопится, мы максимально вовлечены
        elif tone == "negative":
            current_emotion = "skeptical" # На негатив отвечаем скепсисом
        elif tone == "positive":
            current_emotion = "interested" # На позитив — интересом
        elif len(history_msgs) > 5:
            current_emotion = "interested" # После 5 сообщений мы уже партнеры
        else:
            current_emotion = "skeptical" # По умолчанию — легкий скепсис эксперта
            
        task_instr = "Ты — Алексей, отвечаешь клиенту в личной переписке. Дай живой, экспертный ответ в зависимости от истории и контекста."
        system_prompt = prompt_builder.build_system_prompt(task_instr)
        user_prompt = prompt_builder.build_user_prompt(
            query=full_text,
            user_name=sender_name,
            cases=cases,
            external_cases=external_cases,
            service=service,
            category=classification.get("category"),
            style_profile=lead.style_profile,
            context_memory=lead.context_memory,
            history_text=history_text,
            current_emotion=current_emotion,
            sales_materials=sales_materials
        )
        
        # 5. LLM Generation Loop with Supervisor
        MAX_RETRIES = 3
        current_system_prompt = system_prompt
        ai_response_text = ""
         
        for attempt in range(MAX_RETRIES):
            logger.info(f"🔄 Generation attempt {attempt+1}/{MAX_RETRIES}...")
            ai_response_text = await llm_client.generate_response(user_prompt, current_system_prompt)
            
            if not ai_response_text:
                break # Handle as failure below
                
            # Check with Gwen
            check = await gwen_supervisor.check_message(ai_response_text)
            verdict = check.get("verdict", "ALLOW")
            
            if verdict == "ALLOW":
                logger.info("✅ Gwen approved response.")
                break
                
            elif verdict == "BLOCK":
                logger.warning(f"⛔️ Gwen HARD BLOCKED response: {check.get('reason')}")
                # Log failure and stop
                msg_log = MessageLog(
                    lead_id=lead.id, direction="outgoing", content=ai_response_text,
                    status="blocked", error_message=check.get("reason"),
                    intent=classification.get("intent") 
                )
                session.add(msg_log)
                await session.commit()
                
                # Notify Admin about Block
                try:
                   from systems.gwen.notifier import supervisor_notifier
                   await supervisor_notifier.notify_block(
                       f"{sender_name} (@{sender_username})", 
                       ai_response_text, 
                       check
                   )
                except: pass
                return # EXIT, DO NOT SEND
                
            elif verdict == "RETRY":
                logger.info(f"🔧 Gwen requested RETRY: {check.get('reason')}")
                # Add correction instruction to prompt context for next attempt
                correction = check.get('correction', 'Improve quality.')
                current_system_prompt += f"\n\n[SUPERVISOR FEEDBACK]: The previous draft was rejected. Reason: {check.get('reason')}. instruction: {correction}. Fix this in the new response."
        else:
            # If loop finished without break (all retries failed)
            logger.warning("⚠️ Max retries reached. Sending best effort (or failing safely).")
            # Decision: Send the last attempt if it wasn't a hard block? 
            # Or fail? Let's fail safely for now to avoid bad reps.
            if verdict == "RETRY": 
                # If we are here, it means even the last attempt was a RETRY, 
                # but not a BLOCK. We might choose to send it anyway or silence.
                # Let's silence to be safe.
                 msg_log = MessageLog(
                    lead_id=lead.id, direction="outgoing", content=ai_response_text,
                    status="failed_quality", error_message="Max retries reached on Gwen check"
                )
                 session.add(msg_log)
                 await session.commit()
                 return

        
        if not ai_response_text:
            logger.error(f"Critical: LLM failed to generate response for user {sender_id}. Reporting to admin.")
            # Логируем в БД как провал, но НЕ отправляем клиенту
            msg_log = MessageLog(
                lead_id=lead.id, direction="incoming", content=full_text,
                intent=classification.get("intent"), category=classification.get("category"),
                lead_score=classification.get("lead_score"), ai_response=None,
                status="failed", error_message="All LLM models failed"
            )
            session.add(msg_log)
            await session.commit()
            return

        # 5.1 Detect if any case was mentioned OR if user asked for "screenshots/proofs"
        mentioned_cases = []
        is_requesting_proof = any(word in full_text.lower() for word in ["скрин", "пруф", "фото", "покажи", "доказательства", "кабинет"])
        
        if cases:
            for case in cases:
                if case.title.lower() in ai_response_text.lower() or (is_requesting_proof and case.category.lower() in full_text.lower()):
                    mentioned_cases.append(case)
        
        # 6. Log Incoming
        msg_log = MessageLog(
            lead_id=lead.id, direction="incoming", content=full_text,
            intent=classification.get("intent"), category=classification.get("category"),
            lead_score=classification.get("lead_score"), ai_response=ai_response_text,
            metadata_json=classification
        )
        session.add(msg_log)
        
        from core.utils.humanity import humanity_manager
        
        # 7. Humanity
        # 7.1 Reading Delay
        reading_delay = humanity_manager.get_reading_delay(full_text)
        logger.debug(f"Simulating reading delay: {reading_delay:.2f}s")
        await asyncio.sleep(reading_delay)
        
        # Помечаем сообщение как прочитанное после "прочтения"
        try:
            await client.send_read_acknowledge(event.chat_id, event.message)
        except Exception as e:
            logger.warning(f"Failed to mark message as read: {e}")
            
        # 7.2 Prepare chunks
        chunks = humanity_manager.split_into_human_chunks(ai_response_text)
        
        sent_msg = None
        status = "sent"
        
        # Создаем перехватчик сообщений с супервизором для отправки (опционально)
        interceptor = client # Bypassing Gwen for now as requested or assumed for Alexey
        
        try:
            # 7.4 Handle Admin Escalation or Graceful Exit tag cleaning
            import re
            clean_response = ai_response_text
            
            # Case 1: Manual Help needed
            if "[ASK_ADMIN:" in ai_response_text:
                match = re.search(r"\[ASK_ADMIN:\s*(.*?)\]", ai_response_text)
                question = match.group(1) if match else "Вопрос не распознан"
                
                # Notify Admin
                admin_username = settings.ADMIN_TELEGRAM_USERNAME.lstrip('@')
                admin_msg = (
                    f"🆘 **Алексей зовет на помощь!**\n\n"
                    f"Клиент: {sender.first_name} (@{sender.username})\n"
                    f"Вопрос: {question}\n\n"
                    f"Больше я в этот диалог не пишу. Теперь твоя очередь!"
                )
                try:
                    await client.send_message(admin_username, admin_msg)
                except: pass
                
                # Set handover flags
                lead.is_human_managed = True
                lead.handover_reason = f"AI requested help: {question}"
                
                # Clean the tag
                clean_response = re.sub(r"\[ASK_ADMIN:.*?\]", "", clean_response).strip()

            # Case 2: Graceful Exit (Colleague/Recruiter detected)
            if "[HANDOVER_TO_HUMAN:" in ai_response_text:
                match = re.search(r"\[HANDOVER_TO_HUMAN:\s*(.*?)\]", ai_response_text)
                reason = match.group(1) if match else "Тактичный отход"
                
                # Notify Admin
                admin_username = settings.ADMIN_TELEGRAM_USERNAME.lstrip('@')
                admin_msg = (
                    f"🤝 **Тактичный отход Алексея**\n\n"
                    f"Лид: {sender.first_name} (@{sender.username})\n"
                    f"Причина: {reason}\n\n"
                    f"Алексей распознал коллегу или рекрутера и выдал финальную фразу. Диалог передан тебе (ИИ отключен)."
                )
                try:
                    await client.send_message(admin_username, admin_msg)
                except: pass
                
                # Set handover flags
                lead.is_human_managed = True
                lead.handover_reason = f"Graceful exit: {reason}"
                
                # Clean the tag
                clean_response = re.sub(r"\[HANDOVER_TO_HUMAN:.*?\]", "", clean_response).strip()

            # Re-split chunks based on cleaned response
            chunks = humanity_manager.split_into_human_chunks(clean_response)

            # 7.4 Send chunks with typing simulation
            for i, chunk in enumerate(chunks):
                # Start typing simulation
                duration = humanity_manager.get_typing_duration(chunk)
                async with client.action(event.chat_id, 'typing'):
                    await asyncio.sleep(duration)
                    
                    # If it's the LAST chunk, we might want to attach cases
                    if i == len(chunks) - 1:
                        if mentioned_cases:
                            # Sort to get the most relevant first
                            best_case = mentioned_cases[0]
                            
                            if best_case.image_url and os.path.exists(best_case.image_url):
                                caption = (
                                    f"{chunk}\n\n"
                                    f"📊 Кейс: {best_case.title}\n"
                                    f"✅ Результат: {best_case.results}\n\n"
                                    f"🔗 Читать подробный разбор: {best_case.project_url}"
                                )
                                if len(caption) > 1000:
                                    caption = caption[:997] + "..."
                                # Use client directly
                                sent_msg = await client.send_file(event.chat_id, best_case.image_url, caption=caption)
                            else:
                                text_with_link = f"{chunk}\n\n🔗 Подробнее об этом кейсе: {best_case.project_url}"
                                sent_msg = await client.send_message(event.chat_id, text_with_link)
                        else:
                            sent_msg = await client.send_message(event.chat_id, chunk)
                    else:
                        # Just send a regular message chunk
                        sent_msg = await client.send_message(event.chat_id, chunk)
                    
                    if sent_msg:
                        handover_manager.mark_as_automated(sent_msg.id)
                
                # Pause between chunks
                if i < len(chunks) - 1:
                    import random
                    pause = random.uniform(0.7, 1.8)
                    await asyncio.sleep(pause)
                    
        except Exception as e:
            logger.error(f"Error sending message with humanity: {e}")
            status = "failed"
        
        # 8. Log Outgoing
        out_msg_log = MessageLog(
            lead_id=lead.id, direction="outgoing", content=ai_response_text,
            status=status, telegram_msg_id=sent_msg.id if sent_msg else None
        )
        session.add(out_msg_log)
        lead.last_interaction = datetime.utcnow()
        await session.commit()

        
        # 9. Adaptive Learning
        try:
            new_history = history_text + f"\nКлиент: {full_text}\nАлексей: {ai_response_text}"
            analysis_prompt = prompt_builder.build_analysis_prompt(new_history, lead.style_profile or "", lead.context_memory or "")
            analysis_json = await llm_client.generate_response(analysis_prompt, "Ты — аналитик стиля общения.")
            start, end = analysis_json.find('{'), analysis_json.rfind('}') + 1
            if start != -1 and end != -1:
                data = json.loads(analysis_json[start:end])
                lead.style_profile = data.get("style_profile", lead.style_profile)
                lead.context_memory = data.get("context_memory", lead.context_memory)
                await session.commit()
        except Exception: pass

async def handle_message_read(event: MessageRead):
    if event.inbox: return
    async with async_session() as session:
        stmt = update(MessageLog).where(and_(MessageLog.telegram_msg_id <= event.max_id, MessageLog.direction == 'outgoing', MessageLog.status == 'sent')).values(status='read')
        await session.execute(stmt)
        await session.commit()
