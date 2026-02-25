from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from core.config.settings import settings
from systems.alexey.handlers.message_handler import handle_incoming_message, handle_message_read
from core.database.connection import init_db, async_session
from core.database.models import Lead, MessageLog
from sqlalchemy import select
from core.utils.logger import logger
from systems.gwen.commander import GwenCommander
from core.utils.handover import handover_manager
import asyncio
import os

# ── Создаём Pyrogram клиент ──────────────────────────────────────────────────
# Пробуем загрузить строку сессии
session_str = None
for session_path in [
    "data/sessions/alexey_pyrogram.txt",
    "data/sessions/session_string_pyrogram.txt",
]:
    try:
        with open(session_path, "r") as f:
            content = f.read().strip()
            if content:
                session_str = content
                break
    except FileNotFoundError:
        continue

if session_str:
    client = Client(
        name="alexey",
        api_id=settings.TELEGRAM_API_ID,
        api_hash=settings.TELEGRAM_API_HASH,
        session_string=session_str,
        in_memory=True,
        no_updates=False
    )
else:
    os.makedirs("data/sessions", exist_ok=True)
    client = Client(
        name="data/sessions/alexey",
        api_id=settings.TELEGRAM_API_ID,
        api_hash=settings.TELEGRAM_API_HASH,
        phone_number=getattr(settings, 'TELEGRAM_PHONE', None),
    )


# ── Фильтры ──────────────────────────────────────────────────────────────────
def _not_blacklisted(_, __, message: Message) -> bool:
    """Фильтр: пропускаем чёрный список."""
    username = message.from_user.username if message.from_user else None
    if username and username.lower() in settings.blacklisted_usernames:
        return False
    return True

not_blacklisted = filters.create(_not_blacklisted)

def _monitored_only(_, __, message: Message) -> bool:
    """Фильтр: только из мониторируемых чатов (если настроено)."""
    if settings.monitored_chat_ids:
        return message.chat.id in settings.monitored_chat_ids
    return True

monitored_only = filters.create(_monitored_only)


# ── Обработчики событий ───────────────────────────────────────────────────────
@client.on_message(
    filters.incoming & filters.private & not_blacklisted & monitored_only
)
async def on_new_message(client: Client, message: Message):
    """Handle all incoming private messages."""
    chat_id = message.chat.id
    logger.info(f"📩 New event from {chat_id}. is_private=True")

    if not message.text and not message.voice:
        return

    text_preview = (message.text or "[voice]")[:50]
    logger.info(f"✅ Processing message in chat {chat_id}: {text_preview}...")

    try:
        await handle_incoming_message(message, client)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        try:
            from core.utils.admin_notifier import AdminNotifier
            notifier = AdminNotifier(client)
            user = message.from_user
            await notifier.notify_error(
                e,
                "Обработка входящего сообщения",
                {
                    "name": user.first_name if user else "Unknown",
                    "username": user.username if user else None,
                    "id": user.id if user else 0
                }
            )
        except Exception:
            pass


@client.on_message(filters.outgoing & filters.private)
async def on_outgoing_message(client: Client, message: Message):
    """Detect when human takes over the chat."""
    chat_id = message.chat.id

    async with async_session() as session:
        stmt = select(Lead).where(Lead.telegram_id == chat_id)
        result = await session.execute(stmt)
        lead = result.scalars().first()

        if handover_manager.is_automated(message.id):
            return

        if lead and not lead.is_human_managed:
            logger.info(f"👨‍💼 Human takeover detected for Lead {chat_id}. Disabling AI.")
            lead.is_human_managed = True
            lead.handover_reason = "Manual takeover (Admin sent a message)"
            await session.commit()


@client.on_message(filters.incoming & ~filters.private)
async def on_channel_message(client: Client, message: Message):
    """Логируем события из каналов/групп (для мониторинга вакансий Gwen)."""
    logger.info(f"📩 New event from {message.chat.id}. is_private=False")


async def main():
    logger.info("Initializing database...")
    await init_db()

    logger.info("Starting userbot...")
    await client.start()

    # Initialize Gwen Commander
    gwen_commander = GwenCommander(client)
    await gwen_commander.start(start_bot=False)

    me = await client.get_me()
    logger.info(f"Logged in as: {me.first_name} (@{me.username})")

    if settings.monitored_chat_ids:
        logger.info(f"Monitoring chats: {settings.monitored_chat_ids}")
    else:
        logger.info("Monitoring ALL incoming private chats")

    logger.info("Userbot is running. Press Ctrl+C to stop.")

    # Start background tasks
    from systems.alexey.tasks import run_follow_ups
    asyncio.create_task(run_follow_ups(client))

    await client.idle()


if __name__ == "__main__":
    asyncio.run(main())
