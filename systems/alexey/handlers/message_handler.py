import os
import re
import asyncio
import json
import random
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.errors import UserIsBlocked, FloodWait
from systems.gwen import create_interceptor
from core.database.connection import async_session
from core.database.models import Lead, MessageLog
from sqlalchemy import select, update, and_, desc
from core.classifier.intent_classifier import MessageClassifier
from core.ai_engine.llm_client import llm_client
from core.ai_engine.prompt_builder import prompt_builder
from core.knowledge_base.retriever import KnowledgeRetriever
from core.utils.logger import logger
from core.utils.smart_sender import smart_send_message
from core.utils.humanity import humanity_manager
from core.config.settings import settings
from core.utils.handover import handover_manager


# Глобальные контейнеры для накопления сообщений
message_buffers: dict = {}
user_data_cache: dict = {}
debounce_tasks: dict = {}

# По одному asyncio.Lock на sender_id — предотвращает race condition буфера
_buffer_locks: dict = {}
# Очередь сообщений у которых LLM не ответил — для повторной попытки через 5 мин
_llm_retry_queue: dict = {}  # sender_id -> {text, sender, message, attempt, retry_at}


def _get_buffer_lock(sender_id: int) -> asyncio.Lock:
    """Возвращает (или создаёт) Lock для данного sender_id."""
    if sender_id not in _buffer_locks:
        _buffer_locks[sender_id] = asyncio.Lock()
    return _buffer_locks[sender_id]

# Сильные паттерны — 1 совпадение = блок (однозначные признаки бота/системы)
_STRONG_BOT_PATTERNS = [
    "вакансия здесь размещена",
    "вакансии здесь размещены",
    "неизвестная команда",
    "доступные команды:",
    "login code:",
    "this code can be used to log in",
    # Агрегаторы вакансий / фриланс-чаты
    "здесь публикуются заказы",
    "здесь публикуются вакансии",
    "здесь публикуются резюме",
    "под каждым постом есть кнопка",
    "разместить резюме/вакансию",
    "разместить резюме или вакансию",
    "это бесплатный фриланс чат",
    "бесплатный фриланс чат",
    # Канал-промо ответы (только уникальные — не дублировать с _FREELANCER_REPLY_STRONG)
    "подробнее в нашем канале",
    "кейсы в нашем канале",
    "смотрите наши работы в",
    "больше работ в нашем",
    "все проекты в канале",
]

# Слабые паттерны — нужно 2 совпадения
_WEAK_BOT_PATTERNS = [
    "vakansii",
    "freelance_rabota",
    "советуем",
    "если вам нужен фриланс чат",
    "freelance_rabota_chat",
    "фриланс чат",
    "публикуются заказы",
]

# Паттерны ответа исполнителя/фрилансера на outreach
_FREELANCER_REPLY_STRONG = [
    "подробнее в канале",
    "все подробности в канале",
    "больше работ в канале",
    "кейсы в канале",
    "смотрите в канале",
    "записывайтесь через бот",
    "все в телеграм боте",
]

_FREELANCER_REPLY_WEAK = [
    "мои кейсы",
    "моё портфолио",
    "мое портфолио",
    "готов взяться",
    "готов помочь",
    "могу настроить",
    "могу создать",
    "могу помочь",
    "напишите мне в лс",
    "пишите мне в лс",
    "стоимость моих услуг",
    "мой прайс",
    "расценки в лс",
    "беру проекты",
    "принимаю заказы",
    "занимаюсь настройкой",
    "занимаюсь продвижением",
    "занимаюсь созданием",
    # "портфолио" убрано: клиент может спросить "покажи своё портфолио" — ложный блок
    "мои работы",
]


def _is_freelancer_response(text: str) -> bool:
    """Определяет, является ли ответ реакцией исполнителя (не клиента)."""
    t = text.lower()
    for p in _FREELANCER_REPLY_STRONG:
        if p in t:
            return True
    weak_hits = sum(1 for p in _FREELANCER_REPLY_WEAK if p in t)
    return weak_hits >= 2

# Telegram system sender IDs (777000 = Telegram официальный, 42777 = Telegram уведомления)
_SYSTEM_SENDER_IDS = {777000, 42777}

def _is_vacancy_bot_autoreply(text: str) -> bool:
    """Определяет авто-ответ от бота-агрегатора вакансий или системное сообщение."""
    t = text.lower()
    # 1 сильный паттерн = блок
    for p in _STRONG_BOT_PATTERNS:
        if p in t:
            return True
    # 2 слабых паттерна = блок
    weak_hits = sum(1 for p in _WEAK_BOT_PATTERNS if p in t)
    if weak_hits >= 2:
        return True
    # Специфичный ID-паттерн агрегаторов вакансий
    if re.search(r'id\s*:\s*[a-z0-9/ ]{10,}', t):
        return True
    return False


async def handle_user_action(client: Client, message: Message):
    """
    Обработчик 'печатает' — в Pyrogram нет отдельного ChatAction event,
    но этот хук можно вызвать если есть такая необходимость.
    """
    sender_id = message.from_user.id if message.from_user else None
    if not sender_id:
        return

    if sender_id not in user_data_cache:
        user_data_cache[sender_id] = {}
    user_data_cache[sender_id]['last_action_at'] = datetime.utcnow()


async def handle_incoming_message(message: Message, client: Client):
    """
    Handler for incoming messages with debouncing.
    Pyrogram Message объект используется напрямую.
    """
    sender = message.from_user
    sender_id = sender.id if sender else 0

    # Игнорируем свои сообщения (Pyrogram помечает их message.outgoing)
    if message.outgoing:
        return

    # Игнорируем системные сообщения Telegram (коды входа, уведомления)
    if sender_id in _SYSTEM_SENDER_IDS:
        return

    # Извлекаем текст
    text = ""
    if message.voice:
        logger.info(f"Voice message from {sender_id}. Downloading...")
        os.makedirs("downloads", exist_ok=True)
        file_path = await client.download_media(message.voice, file_name="downloads/")
        from core.audio.transcriber import transcriber
        text = await transcriber.transcribe(file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        text = message.text or message.caption or ""

    if not text:
        return

    # Детектируем авто-ответы спам-ботов агрегаторов вакансий
    if _is_vacancy_bot_autoreply(text):
        logger.info(f"🤖 Спам-бот авто-ответ от {sender_id} — блокируем и не отвечаем")
        async with async_session() as session:
            stmt = select(Lead).where(Lead.telegram_id == sender_id)
            result = await session.execute(stmt)
            lead = result.scalars().first()
            if not lead:
                lead = Lead(telegram_id=sender_id, username=getattr(sender, 'username', None),
                            full_name=getattr(sender, 'first_name', 'Bot'))
                session.add(lead)
            lead.is_human_managed = True
            lead.handover_reason = "spam_bot_autoreply"
            await session.commit()
        return

    # Детектируем ответы исполнителей/фрилансеров (не клиентов)
    if _is_freelancer_response(text):
        logger.info(f"👔 Ответ исполнителя от {sender_id} — останавливаем диалог")
        async with async_session() as session:
            stmt = select(Lead).where(Lead.telegram_id == sender_id)
            result = await session.execute(stmt)
            lead = result.scalars().first()
            if not lead:
                lead = Lead(telegram_id=sender_id, username=getattr(sender, 'username', None),
                            full_name=getattr(sender, 'first_name', 'Unknown'))
                session.add(lead)
            lead.is_human_managed = True
            lead.handover_reason = "freelancer_executor_response"
            await session.commit()
        return

    # Потокобезопасное добавление в буфер
    async with _get_buffer_lock(sender_id):
        if sender_id not in message_buffers:
            message_buffers[sender_id] = []
        message_buffers[sender_id].append(text)

        if sender_id not in user_data_cache:
            user_data_cache[sender_id] = {}
        user_data_cache[sender_id].update({
            'last_action_at': datetime.utcnow(),
            'sender': sender,
            'message': message
        })

        # Управляем debounce таймером
        if sender_id in debounce_tasks:
            debounce_tasks[sender_id].cancel()

        task = asyncio.create_task(wait_and_process(client, sender_id))
        debounce_tasks[sender_id] = task


async def wait_and_process(client: Client, sender_id: int):
    """Ожидает тишины перед обработкой. Таймер динамический."""
    try:
        wait_time = 5.0

        async with async_session() as session:
            stmt = select(Lead).where(Lead.telegram_id == sender_id)
            res = await session.execute(stmt)
            lead = res.scalars().first()
            if lead and lead.last_interaction:
                diff = (datetime.utcnow() - lead.last_interaction).total_seconds()
                wait_time = 2.0 if diff < 300 else 5.0
            else:
                wait_time = 7.0

        while True:
            await asyncio.sleep(1)
            last_activity = user_data_cache.get(sender_id, {}).get('last_action_at')
            if not last_activity:
                break
            if (datetime.utcnow() - last_activity).total_seconds() >= wait_time:
                break

        texts = message_buffers.pop(sender_id, [])
        data = user_data_cache.pop(sender_id, {})

        if not texts:
            return

        full_text = "\n".join(texts)
        sender = data.get('sender')
        message = data.get('message')

        logger.info(f"Processing thought from {sender.first_name if sender else 'Unknown'} after silence.")
        await process_full_thought(client, message, sender, full_text)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in wait_and_process: {e}")
    finally:
        if debounce_tasks.get(sender_id) == asyncio.current_task():
            debounce_tasks.pop(sender_id, None)


async def process_full_thought(client: Client, message: Message, sender, full_text: str):
    """Core logic to process the combined message."""
    sender_id = sender.id if sender else 0
    sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'username', 'Unknown') or 'Unknown'
    sender_username = getattr(sender, 'username', None)
    chat_id = message.chat.id

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

        if lead.is_human_managed:
            logger.info(f"⏸ Skipping AI processing for Lead {sender_id} (Human Managed)")
            return

        lead.follow_up_level = 0
        lead.follow_up_sent_at = None

        # 1.1 History
        history_stmt = select(MessageLog).where(MessageLog.lead_id == lead.id).order_by(desc(MessageLog.created_at)).limit(10)
        history_result = await session.execute(history_stmt)
        history_msgs = history_result.scalars().all()
        history_msgs.reverse()

        history_items = []
        for m in history_msgs:
            role = "ТЫ (Ксения)" if m.direction == "outgoing" else "КЛИЕНТ"
            history_items.append(f"{role}: {m.content}")
        history_text = "\n".join(history_items)

        # Определяем: это ответ на холодный outreach?
        is_outreach_dialog = any(m.intent == "outreach" for m in history_msgs)
        first_outreach_msg = next((m for m in history_msgs if m.intent == "outreach"), None)

        # 2. Classify
        classifier = MessageClassifier()
        classification = await classifier.classify(full_text)

        # 3. Context
        # Для outreach-диалогов: если клиент ответил коротко ("интересно", "расскажи"),
        # дополняем поисковый запрос содержимым нашего оффера
        retriever = KnowledgeRetriever(session)
        search_query = full_text
        if is_outreach_dialog and first_outreach_msg and len(full_text.split()) < 6:
            search_query = f"{full_text} {first_outreach_msg.content}"

        cases = await retriever.find_relevant_cases(search_query)
        service = await retriever.find_service_by_category(classification.get("category", ""))

        # Если сервис не определился по короткому ответу — пробуем по тексту оффера
        if not service and is_outreach_dialog and first_outreach_msg:
            outreach_cls = await classifier.classify(first_outreach_msg.content)
            service = await retriever.find_service_by_category(outreach_cls.get("category", ""))

        sales_materials = await retriever.search_markdown_kb(search_query)

        external_cases = []
        if len(cases) < 2 and classification.get("category") not in ["general", None]:
            from core.knowledge_base.web_searcher import web_searcher
            service_name = service.name if service else classification.get("category")
            external_cases = await web_searcher.search_cases(search_query, service_name)

        # 4. Prompt
        tone = classification.get("tone", "neutral")
        msg_count = len(history_msgs)
        text_lower = full_text.lower()

        if "hurry" in tone or "срочно" in text_lower or "быстро" in text_lower:
            current_emotion = "interested"
        elif is_outreach_dialog and msg_count <= 3:
            current_emotion = "intrigued"  # Лид ответил на наш оффер — потенциально горячий
        elif any(w in text_lower for w in ["сколько стоит", "цена", "прайс", "бюджет", "стоимость"]) and msg_count >= 3:
            current_emotion = "intrigued"
        elif tone == "negative" and msg_count > 0:
            current_emotion = "skeptical"
        elif tone == "positive" or (msg_count > 5 and tone != "negative"):
            current_emotion = "interested"
        elif msg_count > 8:
            current_emotion = "tired"
        elif classification.get("category") not in ["seo", "ppc", "avito", "smm", "marketing", "general", None]:
            current_emotion = "uncertain"
        elif full_text.strip().endswith("?") and msg_count >= 2:
            current_emotion = "intrigued"
        else:
            current_emotion = "skeptical"

        if is_outreach_dialog:
            if msg_count <= 2:
                task_instr = (
                    "Человек ответил на твой холодный отклик — значит, он уже ищет исполнителя. "
                    "Квалификация не нужна: потребность подтверждена. "
                    "Покажи себя как лучший выбор: коротко упомяни релевантный кейс из нашей практики, "
                    "задай один точечный вопрос про детали их задачи."
                )
            elif msg_count <= 5:
                task_instr = (
                    f"Диалог с outreach-лидом (сообщение {msg_count + 1}). "
                    "Переходи к конкретике: предложение, цифры, следующий шаг. "
                    "Цель — закрыть на созвон или получить бриф."
                )
            else:
                task_instr = (
                    f"Длинный диалог с outreach-лидом (сообщение {msg_count + 1}). "
                    "Предложи созвон или конкретный следующий шаг. Не затягивай."
                )
        else:
            if msg_count == 0:
                task_instr = "Это первое сообщение от клиента. Коротко и живо: покажи интерес к задаче, задай один уточняющий вопрос."
            elif msg_count <= 3:
                task_instr = f"Диалог только начался (сообщение {msg_count + 1}). Продолжай квалификацию, уточняй потребности, не спеши с предложением."
            elif msg_count <= 7:
                task_instr = f"Диалог развивается (сообщение {msg_count + 1}). Давай конкретику, можно предложить что-то осязаемое. Следи за сигналами готовности к сделке."
            else:
                task_instr = f"Длинный диалог (сообщение {msg_count + 1}). Отвечай кратко и по делу. Если клиент готов — предложи созвон."

        if lead.context_memory:
            task_instr += " Ты уже знаком с этим клиентом — используй знания о нём из КОНТЕКСТ."

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
            sales_materials=sales_materials,
            message_count=msg_count + 1
        )

        # 5. LLM Generation
        logger.info("🔄 Generating response...")
        ai_response_text = await llm_client.generate_response(user_prompt, system_prompt)

        if not ai_response_text:
            logger.error(f"Critical: LLM failed to generate response for user {sender_id}.")
            msg_log = MessageLog(
                lead_id=lead.id, direction="incoming", content=full_text,
                intent=classification.get("intent"), category=classification.get("category"),
                lead_score=classification.get("lead_score"), ai_response=None,
                status="failed", error_message="All LLM models failed"
            )
            session.add(msg_log)
            await session.commit()
            # Планируем повторную попытку через 5 минут (максимум 2 попытки)
            attempt = _llm_retry_queue.get(sender_id, {}).get("attempt", 0)
            if attempt < 2:
                _llm_retry_queue[sender_id] = {
                    "text": full_text, "sender": sender,
                    "message": message, "attempt": attempt + 1,
                }
                asyncio.create_task(_llm_retry_after(client, sender_id, delay=300))
                logger.info(f"📅 LLM retry #{attempt + 1} запланирован для {sender_id} через 5 мин")
            # Отправляем fallback чтобы клиент не завис в тишине
            fallback = "Получил ваше сообщение, отвечу чуть позже 🙏"
            try:
                await smart_send_message(client, sender_id, fallback)
                logger.info(f"📤 Fallback sent to {sender_id} (LLM unavailable)")
            except Exception as fb_err:
                logger.warning(f"Fallback send failed: {fb_err}")
            return

        # 5.1 Detect mentioned cases
        mentioned_cases = []
        is_requesting_proof = any(w in full_text.lower() for w in ["скрин", "пруф", "фото", "покажи", "доказательства", "кабинет"])
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

        # 7. Humanity — Reading delay
        reading_delay = humanity_manager.get_reading_delay(full_text)
        await asyncio.sleep(reading_delay)

        # Помечаем как прочитанное (Pyrogram)
        try:
            await client.read_chat_history(chat_id)
        except Exception as e:
            logger.warning(f"Failed to mark message as read: {e}")

        sent_msg = None
        status = "sent"

        # 7.4 Handle tags
        clean_response = ai_response_text

        if "[ASK_ADMIN:" in ai_response_text:
            match = re.search(r"\[ASK_ADMIN:\s*(.*?)\]", ai_response_text)
            question = match.group(1) if match else "Вопрос не распознан"
            admin_username = settings.ADMIN_TELEGRAM_USERNAME.lstrip('@')
            admin_msg = (
                f"🆘 **Ксения зовет на помощь!**\n\n"
                f"Клиент: {sender_name} (@{sender_username})\n"
                f"Вопрос: {question}\n\nТеперь твоя очередь!"
            )
            try:
                await client.send_message(admin_username, admin_msg)
            except Exception:
                pass
            lead.is_human_managed = True
            lead.handover_reason = f"AI requested help: {question}"
            clean_response = re.sub(r"\[ASK_ADMIN:.*?\]", "", clean_response).strip()

        if "[HANDOVER_TO_HUMAN:" in ai_response_text:
            match = re.search(r"\[HANDOVER_TO_HUMAN:\s*(.*?)\]", ai_response_text)
            reason = match.group(1) if match else "Тактичный отход"
            admin_username = settings.ADMIN_TELEGRAM_USERNAME.lstrip('@')
            admin_msg = (
                f"🤝 **Тактичный отход Алексея**\n\n"
                f"Лид: {sender_name} (@{sender_username})\n"
                f"Причина: {reason}\n\nИИ отключен."
            )
            try:
                await client.send_message(admin_username, admin_msg)
            except Exception:
                pass
            lead.is_human_managed = True
            lead.handover_reason = f"Graceful exit: {reason}"
            clean_response = re.sub(r"\[HANDOVER_TO_HUMAN:.*?\]", "", clean_response).strip()

        chunks = humanity_manager.split_into_human_chunks(clean_response)

        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            try:
                duration = humanity_manager.get_typing_duration(chunk)
                await client.send_chat_action(chat_id, ChatAction.TYPING)
                await asyncio.sleep(duration)

                if i == len(chunks) - 1 and mentioned_cases:
                    best_case = mentioned_cases[0]
                    if best_case.image_url and os.path.exists(best_case.image_url):
                        caption = f"{chunk}\n\n📊 Кейс: {best_case.title}\n✅ {best_case.results}\n🔗 {best_case.project_url}"
                        sent_msg = await client.send_photo(chat_id, best_case.image_url, caption=caption[:1000])
                    else:
                        sent_msg = await client.send_message(chat_id, f"{chunk}\n\n🔗 {best_case.project_url}")
                else:
                    sent_msg = await client.send_message(chat_id, chunk)

                if sent_msg:
                    handover_manager.mark_as_automated(sent_msg.id)

                if i < len(chunks) - 1:
                    await asyncio.sleep(random.uniform(0.7, 1.8))

                i += 1

            except FloodWait as e:
                wait_sec = e.value + 2
                logger.warning(f"⏳ FloodWait {e.value}s на chunk {i}/{len(chunks)} — ожидаем {wait_sec}s...")
                await asyncio.sleep(wait_sec)
                # Не инкрементируем i — повторяем тот же chunk

            except UserIsBlocked:
                logger.error(f"❌ UserIsBlocked при отправке chunk {i}")
                status = "failed"
                break

            except Exception as e:
                logger.error(f"Error sending chunk {i}: {e}")
                status = "failed"
                break

        # 8. Log Outgoing
        out_msg_log = MessageLog(
            lead_id=lead.id, direction="outgoing", content=clean_response,
            status=status, telegram_msg_id=sent_msg.id if sent_msg else None
        )
        session.add(out_msg_log)
        lead.last_interaction = datetime.utcnow()
        await session.commit()

        # 9. Adaptive Learning
        try:
            new_history = history_text + f"\nКлиент: {full_text}\nКсения: {ai_response_text}"
            analysis_prompt = prompt_builder.build_analysis_prompt(new_history, lead.style_profile or "", lead.context_memory or "")
            analysis_json = await llm_client.generate_response(analysis_prompt, "Ты — аналитик стиля общения.")
            if not analysis_json:
                logger.warning(f"Adaptive Learning: LLM вернул пустой ответ для lead {sender_id}")
            else:
                start, end = analysis_json.find('{'), analysis_json.rfind('}') + 1
                if start != -1 and end > start:
                    data = json.loads(analysis_json[start:end])
                    lead.style_profile = data.get("style_profile", lead.style_profile)
                    lead.context_memory = data.get("context_memory", lead.context_memory)
                    await session.commit()
                else:
                    logger.warning(f"Adaptive Learning: не удалось извлечь JSON для lead {sender_id}: {analysis_json[:100]}")
        except json.JSONDecodeError as e:
            logger.warning(f"Adaptive Learning: невалидный JSON для lead {sender_id}: {e}")
        except Exception as e:
            logger.error(f"Adaptive Learning error for lead {sender_id}: {e}")


async def handle_message_read(message):
    """Обработка прочтения сообщений (Pyrogram callback)."""
    pass  # В Pyrogram read receipts обрабатываются иначе, через raw updates


async def _llm_retry_after(client: Client, sender_id: int, delay: int = 300):
    """
    Повторная попытка LLM-ответа через `delay` секунд.
    Вызывается как asyncio.Task когда LLM не смог ответить с первого раза.
    """
    await asyncio.sleep(delay)
    retry_data = _llm_retry_queue.pop(sender_id, None)
    if not retry_data:
        return  # Пользователь написал снова — буфер уже обработан

    logger.info(f"🔁 LLM retry #{retry_data.get('attempt', '?')} для {sender_id}")
    try:
        await process_full_thought(
            client=client,
            message=retry_data["message"],
            sender=retry_data["sender"],
            full_text=retry_data["text"],
        )
    except Exception as e:
        logger.error(f"LLM retry failed for {sender_id}: {e}")
