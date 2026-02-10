
import asyncio
import os
from pathlib import Path
from telethon import TelegramClient
from core.config.settings import settings
from core.utils.logger import logger

class BacklogMonitor:
    def __init__(self):
        self.interval = 3600  # Напоминать раз в час, если есть задачи
        self.backlog_file = settings.BASE_DIR / "backlog.md"
        self.bot_token = settings.SUPERVISOR_BOT_TOKEN
        self.chat_id = settings.SUPERVISOR_CHAT_ID

    async def start(self):
        """Запуск цикла мониторинга."""
        if not self.bot_token or not self.chat_id:
            logger.warning("BacklogMonitor disabled: Credentials missing.")
            return

        logger.info("📂 Backlog Monitor started.")
        client = TelegramClient('backlog_monitor', settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
        await client.start(bot_token=self.bot_token)

        while True:
            try:
                if self.has_pending_tasks():
                    msg = (
                        "📂 <b>Напоминание от Гвен:</b>\n"
                        "В <code>backlog.md</code> есть невыполненные задачи для Антигравити.\n"
                        "Не забудьте запустить агента в IDE!"
                    )
                    await client.send_message(self.chat_id, msg, parse_mode='html')
                    logger.info("Sent backlog reminder.")
                
            except Exception as e:
                logger.error(f"Backlog monitor error: {e}")

            await asyncio.sleep(self.interval)

    def has_pending_tasks(self) -> bool:
        """Проверяет наличие '[ ]' в файле."""
        if not self.backlog_file.exists():
            return False
            
        try:
            with open(self.backlog_file, 'r', encoding='utf-8') as f:
                content = f.read()
                return "- [ ]" in content
        except Exception:
            return False

async def main():
    monitor = BacklogMonitor()
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
