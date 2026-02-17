"""
Обработчик команды /app для открытия Telegram Mini App.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

router = Router()

@router.message(Command("app"))
async def cmd_open_miniapp(message: Message):
    """Открыть Telegram Mini App."""
    
    # ВАЖНО: Замените на ваш реальный URL после настройки ngrok
    # Для локального тестирования используйте ngrok: ngrok http 8080
    webapp_url = "http://localhost:8080"  # Замените на https://your-ngrok-url.ngrok.io
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Открыть Dashboard",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    
    await message.answer(
        "📱 <b>Harmonic Trifid Mini App</b>\n\n"
        "✨ Управление лидами с телефона\n"
        "📊 Realtime статистика\n"
        "🤖 RL-оптимизация откликов\n\n"
        "Нажмите кнопку ниже:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
