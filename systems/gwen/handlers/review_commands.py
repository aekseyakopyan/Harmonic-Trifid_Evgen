"""
Gwen bot commands для ревью и разметки лидов из Active Learning.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from systems.parser.active_learner import active_learner
from systems.parser.vacancy_db import VacancyDatabase
from core.utils.structured_logger import get_logger

router = Router()
logger = get_logger(__name__)

db = VacancyDatabase()

# Хранилище для текущих review sessions
review_sessions = {}


@router.message(Command("review_batch"))
async def cmd_review_batch(message: Message):
    """
    Команда для старта weekly review batch.
    Показывает топ-50 информативных лидов для разметки.
    """
    user_id = message.from_user.id
    
    logger.info(
        "review_batch_started",
        user_id=user_id,
        username=message.from_user.username
    )
    
    await message.answer("🔍 Загружаю самые информативные лиды для разметки...")
    
    # Получить batch от Active Learner
    informative_samples = await active_learner.select_informative_samples()
    
    if not informative_samples:
        await message.answer(
            "✅ Нет новых лидов для разметки.\n"
            "Все спорные случаи уже обработаны!"
        )
        return
    
    # Сохранить session
    review_sessions[user_id] = {
        "samples": informative_samples,
        "current_index": 0,
        "labeled_count": 0,
        "start_time": message.date
    }
    
    await message.answer(
        f"📊 Найдено {len(informative_samples)} лидов для разметки\n"
        f"📈 Средний informativeness: {sum(s['informativeness'] for s in informative_samples) / len(informative_samples):.3f}\n\n"
        f"Начинаем разметку..."
    )
    
    # Показать первый лид
    await show_next_lead(message)


async def show_next_lead(message: Message):
    """Показать следующий лид из review batch"""
    user_id = message.from_user.id
    session = review_sessions.get(user_id)
    
    if not session:
        await message.answer("❌ Нет активной сессии разметки. Используйте /review_batch")
        return
    
    samples = session["samples"]
    idx = session["current_index"]
    
    if idx >= len(samples):
        # Batch завершен
        await complete_review_session(message)
        return
    
    lead = samples[idx]
    
    # Клавиатура для разметки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Реальный лид", callback_data=f"label_true_{lead['lead_id']}"),
            InlineKeyboardButton(text="❌ Не лид", callback_data=f"label_false_{lead['lead_id']}")
        ],
        [
            InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"label_skip_{lead['lead_id']}")
        ]
    ])
    
    # Форматирование текста лида
    text = (
        f"📝 Лид #{idx + 1}/{len(samples)}\n"
        f"🔢 ID: {lead['lead_id']}\n"
        f"📊 Informativeness: {lead['informativeness']:.3f}\n"
        f"📍 Источник: {lead['source']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{lead['text'][:800]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Committee predictions: {lead.get('predictions', 'N/A')}\n"
        f"   Variance: {lead.get('committee_variance', 0.0):.3f}"
    )
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("label_"))
async def handle_label(callback: CallbackQuery):
    """Обработка разметки лида"""
    user_id = callback.from_user.id
    session = review_sessions.get(user_id)
    
    if not session:
        await callback.answer("❌ Сессия истекла", show_alert=True)
        return
    
    # Parse callback data
    parts = callback.data.split("_")
    action = parts[1]
    lead_id = int(parts[2])
    
    if action == "skip":
        logger.info("lead_skipped", lead_id=lead_id, user_id=user_id)
    else:
        # Сохранить разметку
        is_lead = (action == "true")
        
        await db.init_db()
        await db.update_lead_label(
            lead_id=lead_id,
            is_lead=is_lead,
            labeled_by=callback.from_user.username,
            labeled_at=callback.message.date
        )
        
        session["labeled_count"] += 1
        
        logger.info(
            "lead_labeled",
            lead_id=lead_id,
            is_lead=is_lead,
            user_id=user_id,
            labeled_count=session["labeled_count"]
        )
        
        await callback.answer(f"✅ Разметка сохранена: {'Лид' if is_lead else 'Не лид'}")
    
    # Следующий лид
    session["current_index"] += 1
    await show_next_lead(callback.message)


async def complete_review_session(message: Message):
    """Завершение review session"""
    user_id = message.from_user.id
    session = review_sessions.get(user_id)
    
    if not session:
        return
    
    labeled_count = session["labeled_count"]
    total_count = len(session["samples"])
    
    logger.info(
        "review_session_completed",
        user_id=user_id,
        labeled_count=labeled_count,
        total_count=total_count
    )
    
    await message.answer(
        f"🎉 Разметка завершена!\n\n"
        f"✅ Размечено: {labeled_count}/{total_count}\n"
        f"⏭️ Пропущено: {total_count - labeled_count}\n\n"
        f"Проверяю условия для переобучения модели..."
    )
    
    # Проверить условия для retraining
    retrain_result = await active_learner.trigger_retrain()
    
    if retrain_result["retrain_triggered"]:
        await message.answer(
            f"🚀 Запущено переобучение модели!\n"
            f"📊 Новых размеченных примеров: {retrain_result['new_labeled_count']}\n"
            f"⏱️ Ожидаемое время: 5-10 минут\n\n"
            f"Вы получите уведомление по завершении."
        )
    else:
        await message.answer(
            f"⏳ Недостаточно данных для переобучения\n"
            f"📊 Размечено: {retrain_result['new_labeled_count']}/50\n"
            f"❓ {retrain_result['reason']}"
        )
    
    # Очистить session
    del review_sessions[user_id]


@router.message(Command("review_stats"))
async def cmd_review_stats(message: Message):
    """Статистика по Active Learning"""
    metrics = await active_learner.calculate_learning_curve_metrics()
    
    text = (
        f"📊 Active Learning Статистика\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Всего размечено: {metrics['total_labeled']}\n"
        f"📅 За эту неделю: {metrics['weekly_labeled']}\n"
        f"📈 Avg informativeness: {metrics['informativeness_avg']:.3f}\n"
    )
    
    await message.answer(text)
