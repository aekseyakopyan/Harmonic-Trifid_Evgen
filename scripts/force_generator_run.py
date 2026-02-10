import asyncio
import os
import sys

# Добавляем корень проекта
sys.path.append(os.getcwd())

from systems.parser.outreach_generator import OutreachGenerator
from core.utils.logger import logger

async def main():
    logger.info("🚀 Принудительная генерация черновиков для новых лидов...")
    generator = OutreachGenerator()
    count = await generator.process_new_vacancies()
    logger.info(f"✅ Готово! Сгенерировано черновиков: {count}")

if __name__ == "__main__":
    asyncio.run(main())
