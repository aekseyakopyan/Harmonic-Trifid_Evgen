"""
smart_sender.py — Умная отправка сообщений через Pyrogram.

С Pyrogram всё стало намного проще:
- app.send_message(chat_id: int, text) работает НАПРЯМУЮ по integer ID
- не нужен access_hash, нет get_entity(), нет InputPeerUser хаков
- ImportContacts используется только если нужно найти пользователя по номеру телефона
"""

import asyncio
from typing import Optional, Union
from pyrogram import Client
from pyrogram.types import User
from pyrogram.enums import ChatAction
from pyrogram.errors import (
    UserIsBlocked, InputUserDeactivated, PeerFlood,
    UserPrivacyRestricted, FloodWait, BadRequest
)
from core.utils.logger import logger


async def smart_send_message(
    client: Client,
    recipient: Union[str, int],
    text: str,
    simulate_typing: bool = True,
    typing_duration: float = 2.0,
    phone: Optional[str] = None,
    monitored_chats_ids: Optional[list] = None  # Оставляем для совместимости API
) -> bool:
    """
    Умная отправка сообщения лиду.

    Pyrogram поддерживает отправку по integer user_id напрямую — это главное преимущество
    над Telethon. Метод пробует несколько вариантов и возвращает True при успехе.

    Args:
        client: Pyrogram Client (userbot)
        recipient: username (str, без @) или telegram_id (int)
        text: Текст сообщения
        simulate_typing: Симулировать ли набор текста
        typing_duration: Время имитации набора, секунды
        phone: Опциональный номер телефона (+7XXXXXXXXXX) — для поиска через ImportContacts
        monitored_chats_ids: Не используется в Pyrogram (оставлен для совместимости)

    Returns:
        True если сообщение отправлено, False — если все попытки провалились
    """
    # Проверяем что получатель — реальный пользователь (не канал/группа)
    if not await _is_valid_user(client, recipient):
        return False

    try:
        if simulate_typing:
            try:
                await client.send_chat_action(recipient, ChatAction.TYPING)
                await asyncio.sleep(min(typing_duration, 5.0))
            except Exception:
                pass  # Typing simulation failure is not critical

        await client.send_message(recipient, text)
        logger.info(f"[SmartSender] ✅ Сообщение отправлено: {recipient}")
        return True

    except UserIsBlocked:
        logger.info(f"[SmartSender] ⛔ Пользователь {recipient} заблокировал нас")
        return False

    except InputUserDeactivated:
        logger.info(f"[SmartSender] 👻 Аккаунт {recipient} деактивирован")
        return False

    except UserPrivacyRestricted:
        logger.info(f"[SmartSender] 🔒 {recipient} ограничил входящие сообщения (privacy settings)")
        # Пробуем через ImportContacts если есть номер телефона
        if phone:
            return await _try_send_via_import_contact(client, phone, text, simulate_typing, typing_duration)
        return False

    except PeerFlood:
        logger.warning(f"[SmartSender] 🚨 PeerFlood — слишком много запросов, пауза 60 сек")
        await asyncio.sleep(60)
        return False

    except FloodWait as e:
        logger.warning(f"[SmartSender] ⏳ FloodWait {e.value} секунд для {recipient}")
        await asyncio.sleep(e.value + 5)
        # Повторная попытка после ожидания
        try:
            await client.send_message(recipient, text)
            return True
        except Exception:
            return False

    except BadRequest as e:
        logger.warning(f"[SmartSender] ❌ BadRequest для {recipient}: {e}")
        return False

    except Exception as e:
        logger.error(f"[SmartSender] ❌ Ошибка отправки {recipient}: {e}")
        return False


async def _is_valid_user(client: Client, recipient: Union[str, int]) -> bool:
    """
    Проверяет что получатель — живой пользователь (не бот, не канал/группа).
    Pyrogram позволяет получить информацию по integer ID напрямую.
    """
    try:
        user = await client.get_users(recipient)
        if isinstance(user, User):
            if user.is_bot:
                logger.info(f"[SmartSender] ⏭ Пропуск бота: {recipient}")
                return False
            return True
        return False
    except Exception as e:
        # Если вообще не можем получить инфо — пробуем отправить всё равно
        logger.debug(f"[SmartSender] Не удалось проверить тип {recipient}: {e}, пробуем отправить")
        return True  # Оптимистично пробуем


async def _try_send_via_import_contact(
    client: Client,
    phone: str,
    text: str,
    simulate_typing: bool,
    typing_duration: float
) -> bool:
    """
    Добавляет пользователя по номеру телефона через ImportContacts,
    отправляет сообщение, затем удаляет из контактов.
    """
    try:
        from pyrogram.raw.functions.contacts import ImportContacts, DeleteContacts
        from pyrogram.raw.types import InputPhoneContact

        contacts = [InputPhoneContact(
            client_id=0,
            phone=phone,
            first_name="Lead",
            last_name=""
        )]
        result = await client.invoke(ImportContacts(contacts=contacts))

        if not result.users:
            logger.warning(f"[SmartSender] ImportContacts не нашёл пользователя с номером {phone}")
            return False

        user = result.users[0]
        user_id = user.id

        if simulate_typing:
            try:
                await client.send_chat_action(user_id, ChatAction.TYPING)
                await asyncio.sleep(min(typing_duration, 5.0))
            except Exception:
                pass

        await client.send_message(user_id, text)
        logger.info(f"[SmartSender] ✅ Отправлено через ImportContacts: {phone} (ID: {user_id})")

        # Удаляем из контактов
        try:
            from pyrogram.raw.types import InputUser
            await client.invoke(DeleteContacts(id=[InputUser(user_id=user.id, access_hash=user.access_hash)]))
        except Exception:
            pass

        return True

    except Exception as e:
        logger.error(f"[SmartSender] ImportContacts ошибка для {phone}: {e}")
        return False
