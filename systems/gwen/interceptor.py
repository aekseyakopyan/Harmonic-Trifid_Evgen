"""
interceptor.py — Перехватчик сообщений для проверки через Gwen Supervisor.
Мигрирован на Pyrogram.
"""
from typing import Optional
from pyrogram import Client
from pyrogram.enums import ChatAction
from core.utils.logger import logger
from systems.gwen.gwen_supervisor import gwen_supervisor
from systems.gwen.notifier import supervisor_notifier
from core.utils.handover import handover_manager


class MessageInterceptor:
    """
    Обёртка вокруг Pyrogram Client.send_message для перехвата и проверки Гвен.
    """
    
    def __init__(self, client: Client):
        self.client = client
        self.blocked_count = 0
        self.allowed_count = 0
        
    async def send_message(self, chat_id, message: str, **kwargs):
        """
        Проверяет сообщение через Гвен перед отправкой.
        chat_id: int (user_id) или str (username) — Pyrogram поддерживает оба варианта
        """
        verdict = await gwen_supervisor.check_message(message, {"entity": str(chat_id)})
        
        if verdict["verdict"] == "BLOCK":
            logger.error(f"❌ GWEN BLOCKED message to {chat_id}: {verdict['reason']}")
            logger.error(f"Blocked content: {message[:200]}")
            self.blocked_count += 1
            
            await supervisor_notifier.notify_block(str(chat_id), message, verdict)
            return None
        
        logger.info(f"✅ SUPERVISOR ALLOWED message to {chat_id}")
        self.allowed_count += 1
        
        sent_msg = await self.client.send_message(chat_id, message)
        if sent_msg:
            handover_manager.mark_as_automated(sent_msg.id)
        return sent_msg
    
    async def send_file(self, chat_id, file, caption: str = "", **kwargs):
        """
        Проверяет caption файла через Гвен.
        """
        if caption:
            verdict = await gwen_supervisor.check_message(caption, {"entity": str(chat_id)})
            
            if verdict["verdict"] == "BLOCK":
                logger.error(f"❌ GWEN BLOCKED file caption to {chat_id}: {verdict['reason']}")
                self.blocked_count += 1
                await supervisor_notifier.notify_block(str(chat_id), f"[FILE] {caption}", verdict)
                return None
        
        logger.info(f"✅ GWEN ALLOWED file to {chat_id}")
        self.allowed_count += 1
        
        sent_msg = await self.client.send_document(chat_id, file, caption=caption)
        if sent_msg:
            handover_manager.mark_as_automated(sent_msg.id)
        return sent_msg
    
    def get_stats(self) -> dict:
        """Возвращает статистику блокировок."""
        return {
            "blocked": self.blocked_count,
            "allowed": self.allowed_count,
            "total": self.blocked_count + self.allowed_count
        }


def create_interceptor(client: Client) -> MessageInterceptor:
    """Создаёт и возвращает перехватчик сообщений."""
    return MessageInterceptor(client)
