"""
Supervisor Notifier — отправляет уведомления через отдельный Telegram бот.

Получатели: SUPERVISOR_CHAT_ID + все chat_id из NOTIFY_CHAT_IDS (.env)

Нужные уведомления:
  - notify_new_vacancy()   — новая вакансия с кнопками одобрения
  - notify_block()         — Гвен заблокировала исходящее сообщение
  - send_critical()        — PEER_FLOOD / спам-блок / смена статуса сервиса
  - send_filter_report()   — еженедельный отчёт по фильтрам

Убраны (спам):
  - ✅ @login на каждую отправку
  - ⚠️ нет контакта
  - 📬 ручная отправка
  - 🧠 Гвен обновила фильтры (нет действий — только лог)
  - notify_stats()          — нигде не вызывалась
"""
import httpx
import asyncio
from typing import List, Optional
from core.config.settings import settings
from core.utils.logger import logger


class SupervisorNotifier:
    """
    Рассылает уведомления всем получателям из settings.notify_chat_ids.
    """

    def __init__(self):
        self.bot_token = settings.SUPERVISOR_BOT_TOKEN
        self.enabled = bool(self.bot_token)

        if not self.enabled:
            logger.warning("Supervisor bot token not configured. Notifications disabled.")

    # ------------------------------------------------------------------
    # Внутренний метод рассылки всем получателям
    # ------------------------------------------------------------------

    async def _broadcast(self, payload: dict):
        """Отправляет одно сообщение всем chat_id из notify_chat_ids."""
        if not self.enabled:
            return

        recipients: List[int] = settings.notify_chat_ids
        if not recipients:
            logger.warning("No notification recipients configured (SUPERVISOR_CHAT_ID / NOTIFY_CHAT_IDS).")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            for chat_id in recipients:
                try:
                    data = {**payload, "chat_id": chat_id}
                    resp = await client.post(url, json=data)
                    resp.raise_for_status()
                    logger.info(f"Notification sent to {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to {chat_id}: {e}")

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    async def notify_new_vacancy(self, vacancy: dict):
        """
        Уведомляет всех получателей о новой вакансии.
        Включает кнопки: Одобрить / Заблокировать / Дубль / Спам.
        """
        if not self.enabled:
            return

        try:
            status = vacancy.get('status_message', '🔔 НОВАЯ ВАКАНСИЯ')
            v_hash = vacancy.get('hash')
            v_text = vacancy.get('text', '')
            contact_link = vacancy.get('contact_link')

            # Проверка на дубль
            if contact_link and contact_link != "Не найден":
                import sqlite3
                try:
                    conn = sqlite3.connect(str(settings.VACANCY_DB_PATH), timeout=10)
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT COUNT(*) FROM vacancies "
                            "WHERE contact_link = ? AND response IS NOT NULL AND response != '' AND hash != ?",
                            (contact_link, v_hash)
                        )
                        if cursor.fetchone()[0] > 0:
                            status = "👯 ДУБЛИКАТ (Ранее уже писали)"
                    finally:
                        conn.close()
                except Exception as db_err:
                    logger.warning(f"notify_new_vacancy: dup check failed: {db_err}")

            if vacancy.get('rejection_reason') == 'HISTORICAL_LOAD_2024_2026':
                status = "🕰️ ИСТОРИЧЕСКИЙ ЛИД (Гвен видела это в 2024-2025)"

            short_text = self._escape_html(v_text[:700])
            if len(v_text) > 700:
                short_text += "..."

            text = (
                f"{status}\n\n"
                f"📍 <b>Запрос:</b>\n{short_text}\n\n"
                f"🔗 <a href='{vacancy.get('contact_link', '#')}'>Связаться</a>"
            )

            reply_markup = None
            if "ОТПРАВЛЕНО" not in status:
                reply_markup = {
                    "inline_keyboard": [
                        [{"text": "✅ Одобрить и отправить", "callback_data": f"outreach_send_{v_hash}"}],
                        [
                            {"text": "🚫 Заблокировать", "callback_data": f"outreach_block_{v_hash}"},
                            {"text": "👯 Дубль",         "callback_data": f"outreach_duplicate_{v_hash}"}
                        ],
                        [{"text": "🗑 Спам", "callback_data": f"outreach_ignore_{v_hash}"}]
                    ]
                }

            payload = {"text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
            if reply_markup:
                payload["reply_markup"] = reply_markup

            await self._broadcast(payload)

        except Exception as e:
            logger.error(f"notify_new_vacancy error: {e}")

    async def notify_block(self, entity: str, message: str, verdict: dict):
        """
        Уведомляет о заблокированном исходящем сообщении.
        """
        if not self.enabled:
            return

        try:
            text = (
                f"🧠 <b>ГВЕН ЗАБЛОКИРОВАЛА СООБЩЕНИЕ</b>\n\n"
                f"<b>Получатель:</b> {entity}\n"
                f"<b>Причина:</b> {verdict.get('reason', '—')}\n"
                f"<b>Уверенность:</b> {verdict.get('confidence', 0) * 100:.0f}%\n\n"
                f"<b>Текст:</b>\n<code>{self._escape_html(message[:500])}</code>"
            )
            await self._broadcast({"text": text, "parse_mode": "HTML"})
        except Exception as e:
            logger.error(f"notify_block error: {e}")

    async def send_critical(self, message: str):
        """
        Отправляет критическое уведомление всем получателям.
        Использовать только для важных событий:
          - PEER_FLOOD / спам-блок
          - смена статуса сервиса (health check)
          - критические сбои
        """
        if not self.enabled:
            return

        try:
            await self._broadcast({"text": message, "parse_mode": "HTML"})
        except Exception as e:
            logger.error(f"send_critical error: {e}")

    # Алиас для обратной совместимости — оставлен, но вызывается только
    # для КРИТИЧЕСКИХ событий (PEER_FLOOD, спам-блок, health alert).
    # Для логов успешных отправок — НЕ использовать.
    send_error = send_critical

    async def send_filter_report(self, report_text: str, phrases_count: int):
        """
        Еженедельный отчёт фильтра с кнопками одобрения / отклонения рекомендаций.
        """
        if not self.enabled:
            return

        try:
            if phrases_count > 0:
                footer = f"\n\n💡 <b>Найдено {phrases_count} фраз для стоп-листа.</b>\nПрименить их к фильтру?"
                reply_markup = {
                    "inline_keyboard": [[
                        {"text": f"✅ Применить ({phrases_count} фраз)", "callback_data": "filter_apply_confirm"},
                        {"text": "❌ Отклонить",                         "callback_data": "filter_apply_reject"}
                    ]]
                }
            else:
                footer = "\n\n✅ Конкретных фраз для добавления не найдено."
                reply_markup = None

            payload = {
                "text": report_text[:4000] + footer,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            await self._broadcast(payload)
        except Exception as e:
            logger.error(f"send_filter_report error: {e}")

    def _escape_html(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Singleton
supervisor_notifier = SupervisorNotifier()
