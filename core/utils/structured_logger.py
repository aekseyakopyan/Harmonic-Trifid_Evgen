import os
import sys
import structlog
import logging
from typing import Any, Dict
from core.config.settings import settings

def setup_structured_logger(name: str):
    """
    Настройка структурированного логирования в формате JSON.
    """
    # Создаем папку для логов если нет
    log_dir = settings.LOG_DIR / "structured"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Конфигурация structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.WriteLoggerFactory(
            file=(log_dir / "leads.json").open("a")
        ),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(name)

# Экспортируем логгер
logger = setup_structured_logger("harmonic_trifid")
