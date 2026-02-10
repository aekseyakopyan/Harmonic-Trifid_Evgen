import asyncio
from telethon import TelegramClient
from core.config.settings import settings
from core.utils.logger import logger

async def notify_new_admin():
    """
    Sends a welcome message to the new admin.
    """
    print(f"Initializing Telegram client to notify {settings.ADMIN_TELEGRAM_USERNAME}...")
    
    import shutil
    import os
    
    # Try to bypass lock by copying the session file
    if os.path.exists('userbot_session.session'):
        shutil.copy('userbot_session.session', 'temp_notify.session')
    
    client = TelegramClient('temp_notify', settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    
    try:
        await client.start(phone=settings.TELEGRAM_PHONE)
        
        admin_username = settings.ADMIN_TELEGRAM_USERNAME
        print(f"Resolving entity for {admin_username}...")
        
        try:
            entity = await client.get_entity(admin_username)
            message = (
                "👋 **Здравствуйте!**\n\n"
                "Я — Алексей, Ваш AI-стратег. Система обновлена, и теперь Вы назначены основным администратором.\n\n"
                "Я буду обращаться к Вам за помощью (через тег `[ASK_ADMIN:]`), если встречу сложный вопрос от клиента, "
                "на который не смогу ответить самостоятельно.\n\n"
                "Рад нашему сотрудничеству! 🤝"
            )
            
            await client.send_message(entity, message)
            print(f"Successfully sent notification to {admin_username}")
        except Exception as resolve_err:
            print(f"Could not resolve entity: {resolve_err}")
            print("Trying to search for the user first...")
            # Some usernames need searching if not in dialogs
            from telethon.tl.functions.contacts import SearchRequest
            result = await client(SearchRequest(q=admin_username, limit=1))
            if result.users:
                await client.send_message(result.users[0], "Тестовое сообщение от Алексея. Система готова.")
                print(f"Successfully sent search-based notification to {admin_username}")
            else:
                raise resolve_err
        
    except Exception as e:
        print(f"Error sending notification: {e}")
        logger.error(f"Failed to notify admin: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(notify_new_admin())
