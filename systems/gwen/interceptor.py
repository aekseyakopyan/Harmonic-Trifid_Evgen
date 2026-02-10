"""
Message Interceptor - Перехватывает все вызовы send_message и проверяет через супервизор.
"""
from typing import Optional
from telethon import TelegramClient
from core.utils.logger import logger
from systems.gwen.gwen_supervisor import gwen_supervisor
from systems.gwen.notifier import supervisor_notifier
from core.utils.handover import handover_manager


class MessageInterceptor:
    """
    Обёртка вокруг TelegramClient.send_message для перехвата и проверки Гвен.
    """
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.blocked_count = 0
        self.allowed_count = 0
        
    async def send_message(self, entity, message: str, **kwargs):
        """
        Проверяет сообщение через Гвен перед отправкой.
        """
        # Проверка через Гвен
        verdict = await gwen_supervisor.check_message(message, {"entity": str(entity)})
        
        if verdict["verdict"] == "BLOCK":
            logger.error(f"❌ GWEN BLOCKED message to {entity}: {verdict['reason']}")
            logger.error(f"Blocked content: {message[:200]}")
            self.blocked_count += 1
            
            # Уведомляем админа через отдельный бот супервизора
            await supervisor_notifier.notify_block(str(entity), message, verdict)
            
            # НЕ отправляем сообщение клиенту
            return None
        
        logger.info(f"✅ SUPERVISOR ALLOWED message to {entity}")
        self.allowed_count += 1
        
        # Отправляем сообщение через оригинальный метод
        sent_msg = await self.client.send_message(entity, message, **kwargs)
        if sent_msg:
            handover_manager.mark_as_automated(sent_msg.id)
        return sent_msg
    
    async def send_file(self, entity, file, **kwargs):
        """
        Проверяет caption файла через Гвен.
        """
        caption = kwargs.get('caption', '')
        
        if caption:
            verdict = await gwen_supervisor.check_message(caption, {"entity": str(entity)})
            
            if verdict["verdict"] == "BLOCK":
                logger.error(f"❌ GWEN BLOCKED file caption to {entity}: {verdict['reason']}")
                self.blocked_count += 1
                
                await supervisor_notifier.notify_block(str(entity), f"[FILE] {caption}", verdict)
                return None
        
        logger.info(f"✅ GWEN ALLOWED file to {entity}")
        self.allowed_count += 1
        
        sent_msg = await self.client.send_file(entity, file, **kwargs)
        if sent_msg:
            handover_manager.mark_as_automated(sent_msg.id)
        return sent_msg
    
    async def _notify_admin_about_block(self, entity, message: str, verdict: dict):
        """Уведомляет администратора о заблокированном сообщении."""
        try:
            from core.config.settings import settings
            admin_username = settings.ADMIN_TELEGRAM_USERNAME.lstrip('@')
            
            notification = (
                f"🚨 **СУПЕРВИЗОР ЗАБЛОКИРОВАЛ СООБЩЕНИЕ**\\n\\n"
                f"Получатель: {entity}\\n"
                f"Причина: {verdict['reason']}\\n"
                f"Уверенность: {verdict['confidence']*100:.0f}%\\n\\n"
                f"Текст:\\n{message[:300]}"
            )
            
            # Отправляем напрямую через оригинальный метод (без проверки)
            await self.client.send_message(admin_username, notification)
            
        except Exception as e:
            logger.error(f"Failed to notify admin about block: {e}")
    
    def get_stats(self) -> dict:
        """Возвращает статистику блокировок."""
        return {
            "blocked": self.blocked_count,
            "allowed": self.allowed_count,
            "total": self.blocked_count + self.allowed_count
        }


# Функция для создания перехватчика
def create_interceptor(client: TelegramClient) -> MessageInterceptor:
    """Создаёт и возвращает перехватчик сообщений."""
    return MessageInterceptor(client)
