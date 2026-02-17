
import asyncio
from aiogram import Bot, Dispatcher
from core.config.settings import settings
from systems.gwen.handlers import review_commands, miniapp_commands
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)

async def start_bot():
    """
    Запуск Aiogram бота для Gwen (Review & Active Learning commands).
    Note: Это отдельный процесс от Telethon UserBot (commander.py).
    """
    if not settings.SUPERVISOR_BOT_TOKEN:
        logger.error("SUPERVISOR_BOT_TOKEN is missing. Cannot start Gwen Bot.")
        return

    bot = Bot(token=settings.SUPERVISOR_BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(review_commands.router)
    dp.include_router(miniapp_commands.router)  # Mini App команды
    
    logger.info("🤖 Gwen Aiogram Bot started (Review Mode + Mini App)")
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Gwen Bot Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Gwen Bot stopped")
