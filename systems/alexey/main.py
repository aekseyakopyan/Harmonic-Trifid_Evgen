from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
from core.config.settings import settings
from systems.alexey.handlers.message_handler import handle_incoming_message, handle_message_read
from core.database.connection import init_db, async_session
from core.database.models import Lead, MessageLog
from sqlalchemy import select
from core.utils.logger import logger
from systems.gwen.commander import GwenCommander
from core.utils.handover import handover_manager

from telethon.sessions import StringSession
import os

# Try to load session string
try:
    with open("data/sessions/session_string_final.txt", "r") as f:
        session_str = f.read().strip()
except Exception as e:
    logger.error(f"Failed to read session string: {e}")
    session_str = ""

# Create Telethon client
client = TelegramClient(
    StringSession(session_str),  # Use StringSession
    settings.TELEGRAM_API_ID,
    settings.TELEGRAM_API_HASH
)

@client.on(events.NewMessage(incoming=True))
async def on_new_message(event):
    """Handle all incoming messages."""
    chat_id = event.chat_id
    
    logger.info(f"📩 New event from {chat_id}. is_private={event.is_private}")

    # ONLY respond to private messages (DMs)
    if not event.is_private:
        return
    
    # Only process messages from monitored chats (if any specified)
    if settings.monitored_chat_ids and chat_id not in settings.monitored_chat_ids:
        logger.debug(f"Ignored message from unmonitored chat {chat_id}")
        return
    
    # Skip messages from self
    if event.out:
        return

    # Check blacklist
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    if username and username.lower() in settings.blacklisted_usernames:
        logger.info(f"🛑 Ignored message from blacklisted user: @{username}")
        return
        
    # Skip non-text/non-voice messages
    if not event.message.text and not event.message.voice:
        return
    
    text_preview = (event.message.text or "[voice]")[:50]
    logger.info(f"✅ Processing message in chat {chat_id}: {text_preview}...")
    
    try:
        await handle_incoming_message(event, client)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        try:
            from core.utils.admin_notifier import AdminNotifier
            notifier = AdminNotifier(client)
            sender = await event.get_sender()
            await notifier.notify_error(
                e,
                "Обработка входящего сообщения",
                {
                    "name": getattr(sender, 'first_name', 'Unknown'),
                    "username": getattr(sender, 'username', None),
                    "id": sender.id if sender else 0
                }
            )
        except:
            pass

@client.on(events.NewMessage(outgoing=True))
async def on_outgoing_message(event):
    """Detect when human takes over the chat."""
    chat_id = event.chat_id
    if not event.is_private:
        return
        
    # Мы ищем лид по ID чата
    async with async_session() as session:
        stmt = select(Lead).where(Lead.telegram_id == chat_id)
        result = await session.execute(stmt)
        lead = result.scalars().first()
        
        # Если это автоматическое сообщение от самого бота — игнорируем
        if handover_manager.is_automated(event.id):
            return

        if lead and not lead.is_human_managed:
            # Если бот видит, что «Алексей» написал сам (а не через скрипт отклика)
            # Примечание: тут можно добавить проверку на метаданные, 
            # чтобы не отключать бота при его же собственных ответах.
            # Но в данной архитектуре исходящие от скрипта идут через client.send_message,
            # что тоже триггерит outgoing=True.
            
            # Для простоты: если в логе последнего исходящего сообщения нет признака 'ai', 
            # или если мы хотим просто ручной перехват.
            
            logger.info(f"👨‍💼 Human takeover detected for Lead {chat_id}. Disabling AI.")
            lead.is_human_managed = True
            lead.handover_reason = "Manual takeover (Admin sent a message)"
            await session.commit()

@client.on(events.MessageRead())
async def on_message_read(event):
    """Handle read receipts."""
    try:
        await handle_message_read(event)
    except Exception as e:
        logger.error(f"Error handling read event: {e}")

@client.on(events.ChatAction)
async def on_user_action(event):
    """Handle user actions like typing and recording."""
    try:
        from systems.alexey.handlers.message_handler import handle_user_action
        await handle_user_action(client, event)
    except Exception as e:
        logger.error(f"Error handling user action: {e}")

async def main():
    logger.info("Initializing database...")
    await init_db()
    
    logger.info("Starting userbot...")
    
    await client.start()
    
    # Initialize and start Gwen Commander
    gwen_commander = GwenCommander(client)
    await gwen_commander.start()
    
    me = await client.get_me()
    logger.info(f"Logged in as: {me.first_name} (@{me.username})")
    
    if settings.monitored_chat_ids:
        logger.info(f"Monitoring chats: {settings.monitored_chat_ids}")
    else:
        logger.info("Monitoring ALL incoming private chats")
    
    logger.info("Userbot is running. Press Ctrl+C to stop.")
    
    # Start background tasks
    from systems.alexey.tasks import run_follow_ups
    client.loop.create_task(run_follow_ups(client))
    # Note: run_automated_outreach is now superseded by GwenCommander's outreach monitor
    # client.loop.create_task(run_automated_outreach(client))
    
    # Temporary: Initiate conversation with test bot and LOG it
    try: 
        logger.info("🚀 Initiating dialogue with @klient_yebok_bot...")
        target_username = "klient_yebok_bot"
        start_text = "Добрый день! Вижу, вы тут главный. Занимаетесь бизнесом?"
        
        # 1. Send
        sent_msg = await client.send_message(f"@{target_username}", start_text)
        
        # 2. Log to DB
        async with async_session() as session:
            # Get entity ID
            entity = await client.get_entity(f"@{target_username}")
            if entity:
                # Find/Create Lead
                stmt = select(Lead).where(Lead.telegram_id == entity.id)
                res = await session.execute(stmt)
                lead = res.scalars().first()
                if not lead:
                    lead = Lead(telegram_id=entity.id, username=target_username, full_name=getattr(entity, 'first_name', target_username))
                    session.add(lead)
                    await session.commit()
                    await session.refresh(lead)
                
                # Log Message
                msg_log = MessageLog(
                    lead_id=lead.id, 
                    direction="outgoing", 
                    content=start_text,
                    status="sent", 
                    telegram_msg_id=sent_msg.id
                )
                session.add(msg_log)
                await session.commit()
                logger.info(f"✅ Initial message logged for {target_username}")

    except Exception as e:
        logger.error(f"Failed to initiate dialogue: {e}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio
    try:
        with client:
            client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Userbot stopped by user")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Unexpected error: {e}")
