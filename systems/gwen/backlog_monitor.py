"""
BacklogMonitor — напоминает о невыполненных задачах в backlog.md.
Интервал: раз в сутки (в 10:00 МСК), только если есть незакрытые задачи.
Рассылает всем получателям из settings.notify_chat_ids.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx

from core.config.settings import settings
from core.utils.logger import logger

MSK = timezone(timedelta(hours=3))


class BacklogMonitor:
    def __init__(self):
        self.backlog_file: Path = settings.BASE_DIR / "backlog.md"
        self.bot_token = settings.SUPERVISOR_BOT_TOKEN
        # Час отправки напоминания по МСК (10:00)
        self.notify_hour = 10

    async def start(self):
        """Запуск цикла мониторинга."""
        if not self.bot_token:
            logger.warning("BacklogMonitor disabled: SUPERVISOR_BOT_TOKEN not set.")
            return

        recipients = settings.notify_chat_ids
        if not recipients:
            logger.warning("BacklogMonitor disabled: no recipients configured.")
            return

        logger.info("📂 Backlog Monitor started (daily reminder at %02d:00 MSK).", self.notify_hour)

        sent_today: str | None = None  # дата последней отправки "YYYY-MM-DD"

        while True:
            try:
                now = datetime.now(MSK)
                today = now.strftime("%Y-%m-%d")

                if now.hour == self.notify_hour and sent_today != today:
                    if self.has_pending_tasks():
                        msg = (
                            "📂 <b>Напоминание от Гвен:</b>\n"
                            "В <code>backlog.md</code> есть невыполненные задачи.\n"
                            "Не забудьте запустить агента в IDE!"
                        )
                        await self._broadcast(msg, recipients)
                        sent_today = today
                        logger.info("Sent backlog reminder.")

            except Exception as e:
                logger.error(f"Backlog monitor error: {e}")

            # Проверяем раз в 30 минут
            await asyncio.sleep(1800)

    def has_pending_tasks(self) -> bool:
        """Проверяет наличие '[ ]' в файле."""
        if not self.backlog_file.exists():
            return False
        try:
            content = self.backlog_file.read_text(encoding="utf-8")
            return "- [ ]" in content
        except Exception:
            return False

    async def _broadcast(self, text: str, recipients: list):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            for chat_id in recipients:
                try:
                    await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
                except Exception as e:
                    logger.error(f"BacklogMonitor: failed to send to {chat_id}: {e}")


async def main():
    monitor = BacklogMonitor()
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())
