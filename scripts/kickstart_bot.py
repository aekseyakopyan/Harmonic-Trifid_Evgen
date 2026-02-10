import asyncio
from telethon import TelegramClient
from core.config.settings import settings

async def main():
    client = TelegramClient(
        'userbot_session',
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH
    )
    
    target_user = "@klient_yebok_bot"
    
    await client.start()
    
    print(f"Sending start message to {target_user}...")
    # Отправляем /start для инициации общения
    await client.send_message(target_user, "/start")
    print("Message sent! waiting for reply...")
    
    # Можно отправить и второе сообщение, чтобы спровоцировать диалог, если бот молчит
    await asyncio.sleep(2)
    initial_pitch = "Добрый день! Вижу, у вас интересный бот. Занимаетесь продвижением?"
    await client.send_message(target_user, initial_pitch)
    print(f"Sent pitch: {initial_pitch}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
