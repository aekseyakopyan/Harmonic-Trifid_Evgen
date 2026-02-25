"""
smart_sender.py — Умная отправка сообщений через Telethon.

Поддерживает отправку по:
1. username   → клиент сначала резолвит, затем шлёт
2. user_id(int) → берёт из кэша сессии (если бот был в одном чате с лидом)
3. InputPeerUser(id, 0) → попытка отправить по ID с хэшом=0 (работает в некоторых версиях)
4. Поиск через общие чаты → get_participants парсинговых чатов для получения access_hash
5. ImportContacts (если есть номер телефона) → добавляем как контакт, потом шлём

Статья-источник: https://habr.com/ru/companies/amvera/articles/838204/
"""

import asyncio
from typing import Optional, Union
from telethon import TelegramClient
from telethon.tl.types import User, InputPeerUser
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from core.utils.logger import logger


async def smart_send_message(
    client: TelegramClient,
    recipient: Union[str, int],
    text: str,
    simulate_typing: bool = True,
    typing_duration: float = 2.0,
    phone: Optional[str] = None,
    monitored_chats_ids: Optional[list] = None
) -> bool:
    """
    Умная отправка сообщения лиду с множеством стратегий fallback.

    Args:
        client: Telethon клиент (userbot)
        recipient: username (str, без @) или telegram_id (int)
        text: Текст сообщения
        simulate_typing: Симулировать ли набор текста
        typing_duration: Пауза при имитации набора
        phone: Опциональный номер телефона в формате +7XXXXXXXXXX
        monitored_chats_ids: Список ID чатов, в которых бот состоит (для поиска entity через участников)

    Returns:
        True если сообщение отправлено, False — если все попытки провалились
    """
    entity = await _resolve_entity(client, recipient, phone, monitored_chats_ids)
    
    if entity is None:
        logger.warning(f"[SmartSender] ❌ Не удалось разрешить entity для: {recipient}")
        return False
    
    # Проверяем, что это реальный пользователь (не бот/канал/группа)
    if isinstance(entity, User):
        if entity.bot:
            logger.info(f"[SmartSender] ⏭ Пропуск бота: {recipient}")
            return False
    
    try:
        if simulate_typing:
            async with client.action(entity, 'typing'):
                await asyncio.sleep(typing_duration)
                await client.send_message(entity, text)
        else:
            await client.send_message(entity, text)
        
        logger.info(f"[SmartSender] ✅ Сообщение отправлено: {recipient}")
        return True
        
    except Exception as e:
        logger.error(f"[SmartSender] ❌ Ошибка отправки {recipient}: {e}")
        return False


async def _resolve_entity(
    client: TelegramClient,
    recipient: Union[str, int],
    phone: Optional[str] = None,
    monitored_chats_ids: Optional[list] = None
) -> Optional[User]:
    """
    Пытается получить объект User через несколько стратегий.
    """
    
    # ──────────────────────────────────────────────
    # Стратегия 1: Прямое разрешение (username или ID из кэша сессии)
    # ──────────────────────────────────────────────
    try:
        lookup = recipient if isinstance(recipient, int) else recipient.lstrip('@')
        entity = await client.get_entity(lookup)
        logger.info(f"[SmartSender] ✅ Стратегия 1 (get_entity) успешна для: {recipient}")
        return entity
    except Exception as e:
        logger.debug(f"[SmartSender] Стратегия 1 не сработала для {recipient}: {e}")

    # ──────────────────────────────────────────────
    # Стратегия 2: InputPeerUser с access_hash=0
    # Работает если у Telegram API есть запись о пользователе в вашей сессии
    # ──────────────────────────────────────────────
    if isinstance(recipient, int):
        try:
            peer = InputPeerUser(user_id=recipient, access_hash=0)
            entity = await client.get_entity(peer)
            logger.info(f"[SmartSender] ✅ Стратегия 2 (InputPeerUser hash=0) успешна для ID: {recipient}")
            return entity
        except Exception as e:
            logger.debug(f"[SmartSender] Стратегия 2 не сработала для {recipient}: {e}")

    # ──────────────────────────────────────────────
    # Стратегия 3: Поиск через участников мониторируемых чатов
    # Если бот состоит в одном чате с лидом — получаем access_hash через get_participants
    # ──────────────────────────────────────────────
    if isinstance(recipient, int) and monitored_chats_ids:
        for chat_id in monitored_chats_ids[:10]:  # Ограничиваем перебор 10 чатами
            try:
                participants = await client.get_participants(chat_id, limit=200)
                for p in participants:
                    if p.id == recipient:
                        logger.info(f"[SmartSender] ✅ Стратегия 3 (из участников чата {chat_id}) успешна для: {recipient}")
                        return p
            except Exception:
                continue
    
    # ──────────────────────────────────────────────
    # Стратегия 4: ImportContacts по номеру телефона
    # Добавляем временный контакт, получаем entity, затем удаляем контакт
    # ──────────────────────────────────────────────
    if phone:
        try:
            contacts = [InputPhoneContact(
                client_id=0,
                phone=phone,
                first_name="Lead",
                last_name=""
            )]
            result = await client(ImportContactsRequest(contacts))
            
            if result.users:
                user = result.users[0]
                logger.info(f"[SmartSender] ✅ Стратегия 4 (ImportContacts) успешна для: {phone}")
                
                # Удаляем контакт после получения entity (чтобы не засорять список)
                try:
                    await client(DeleteContactsRequest(id=[user]))
                except Exception:
                    pass  # Не критично, если не удалось удалить
                
                return user
        except Exception as e:
            logger.debug(f"[SmartSender] Стратегия 4 не сработала для {phone}: {e}")
    
    return None


async def is_human_user(client: TelegramClient, entity) -> bool:
    """Проверяет, что entity является живым пользователем (не бот, не канал)."""
    if not isinstance(entity, User):
        return False
    if entity.bot:
        return False
    return True
