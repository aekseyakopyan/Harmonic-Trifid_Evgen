"""
Health Monitor - Проверяет состояние критических компонентов системы.
"""
import httpx
import asyncio
from sqlalchemy import text
from core.database.connection import async_session
from core.config.settings import settings
from core.utils.logger import logger

class HealthMonitor:
    """
    Класс для проверки жизнедеятельности системы.
    Проверяет: БД, OpenRouter и опционально Ollama.
    """
    
    @staticmethod
    async def check_db() -> bool:
        """Проверка соединения с базой данных."""
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Health Check: Database is DOWN: {e}")
            return False

    @staticmethod
    async def check_openrouter() -> bool:
        """Проверка доступности API OpenRouter."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://openrouter.ai/api/v1/models")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health Check: OpenRouter is DOWN/UNREACHABLE: {e}")
            return False

    @classmethod
    async def get_full_status(cls) -> dict:
        """Возвращает полный отчет о состоянии системы."""
        # Асинхронно запускаем все проверки
        db_ok, openrouter_ok = await asyncio.gather(
            cls.check_db(),
            cls.check_openrouter()
        )
        
        status = {
            "database": "OK" if db_ok else "DOWN",
            "openrouter": "OK" if openrouter_ok else "DOWN"
        }
        
        critical_services = [db_ok, openrouter_ok]
        status["overall"] = "HEALTHY" if all(critical_services) else "DEGRADED"
        return status

health_monitor = HealthMonitor()
