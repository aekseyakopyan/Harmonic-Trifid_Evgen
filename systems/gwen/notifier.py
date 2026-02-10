"""
Supervisor Notifier - отправляет уведомления через отдельный Telegram бот.
"""
import httpx
import asyncio
from typing import Optional
from core.config.settings import settings
from core.utils.logger import logger


class SupervisorNotifier:
    """
    Отправляет уведомления об ошибках супервизора через отдельный Telegram бот.
    """
    
    def __init__(self):
        self.bot_token = settings.SUPERVISOR_BOT_TOKEN
        self.chat_id = settings.SUPERVISOR_CHAT_ID
        self.enabled = bool(self.bot_token)
        
        if not self.enabled:
            logger.warning("Supervisor bot token not configured. Notifications disabled.")
    
    async def notify_block(self, entity: str, message: str, verdict: dict):
        """
        Отправляет уведомление о заблокированном сообщении.
        
        Args:
            entity: Получатель, которому НЕ было отправлено сообщение
            message: Текст заблокированного сообщения
            verdict: Вердикт супервизора с причиной блокировки
        """
        if not self.enabled:
            logger.debug("Supervisor notifications disabled")
            return
        
        try:
            # Формируем текст уведомления
            notification = (
                f"🧠 <b>ГВЕН ЗАБЛОКИРОВАЛА СООБЩЕНИЕ</b>\n\n"
                f"<b>Получатель:</b> {entity}\n"
                f"<b>Причина:</b> {verdict['reason']}\n"
                f"<b>Уверенность:</b> {verdict['confidence']*100:.0f}%\n\n"
                f"<b>Заблокированный текст:</b>\n"
                f"<code>{self._escape_html(message[:500])}</code>"
            )
            
            # Отправляем через Telegram Bot API
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": notification,
                        "parse_mode": "HTML"
                    }
                )
                response.raise_for_status()
                logger.info(f"✅ Supervisor notification sent to {self.chat_id}")
                
        except Exception as e:
            logger.error(f"Failed to send supervisor notification: {e}")
    
    async def notify_stats(self, stats: dict):
        """
        Отправляет статистику работы супервизора.
        """
        if not self.enabled:
            return
        
        try:
            notification = (
                f"📊 <b>Статистика Гвен</b>\n\n"
                f"✅ Разрешено: {stats['allowed']}\n"
                f"❌ Заблокировано: {stats['blocked']}\n"
                f"📈 Всего: {stats['total']}"
            )
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": notification,
                        "parse_mode": "HTML"
                    }
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send supervisor stats: {e}")
    
    async def notify_new_vacancy(self, vacancy: dict):
        """
        Уведомляет пользователя о новой найденной вакансии. 
        По запросу пользователя: упрощенный вид (только текст вакансии и кнопка ОК).
        """
        if not self.enabled:
            return
            
        try:
            status = vacancy.get('status_message', '🔔 НОВАЯ ВАКАНСИЯ')
            v_hash = vacancy.get('hash')
            v_text = vacancy.get('text', '')
            direction = vacancy.get('direction', 'Digital Marketing')
            contact_link = vacancy.get('contact_link')
            
            # Проверка на ДУБЛЬ (уже отправляли этому человеку?)
            is_dupe = False
            if contact_link and contact_link != "Не найден":
                import sqlite3
                conn = sqlite3.connect("vacancies.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM vacancies WHERE contact_link = ? AND response IS NOT NULL AND response != '' AND hash != ?", (contact_link, v_hash))
                if cursor.fetchone()[0] > 0:
                    is_dupe = True
                conn.close()

            # Проверка на исторический лид
            is_historical = (vacancy.get('rejection_reason') == 'HISTORICAL_LOAD_2024_2026')
            
            if is_dupe:
                status = f"👯 ДУБЛИКАТ (Ранее уже писали)"
            elif is_historical:
                status = f"🕰️ ИСТОРИЧЕСКИЙ ЛИД (Гвен видела это в 2024-2025)"

            # Сокращаем текст вакансии для уведомления, но оставляем суть
            short_text = self._escape_html(v_text[:700])
            if len(v_text) > 700:
                short_text += "..."

            # Упрощенный вид по просьбе пользователя
            notification = (
                f"{status}\n\n"
                f"📍 <b>Запрос:</b>\n"
                f"{short_text}\n\n"
                f"🔗 <a href='{vacancy.get('contact_link', '#')}'>Связаться</a>"
            )
            
            # Кнопки для управления
            reply_markup = None
            if "ОТПРАВЛЕНО" not in status:
                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Одобрить и отправить", "callback_data": f"outreach_send_{v_hash}"},
                        ],
                        [
                            {"text": "🚫 Заблокировать", "callback_data": f"outreach_block_{v_hash}"},
                            {"text": "👯 Дубль", "callback_data": f"outreach_duplicate_{v_hash}"}
                        ],
                        [{"text": "🗑 Спам", "callback_data": f"outreach_ignore_{v_hash}"}]
                    ]
                }
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                data = {
                    "chat_id": self.chat_id,
                    "text": notification,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                if reply_markup:
                    data["reply_markup"] = reply_markup
                    
                response = await client.post(url, json=data)
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Failed to send vacancy notification: {e}")

    async def send_error(self, message: str):
        """
        Отправляет текстовое уведомление (ошибку или статус) администратору.
        """
        if not self.enabled:
            return
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }
                )
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

    def _escape_html(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Singleton
supervisor_notifier = SupervisorNotifier()
