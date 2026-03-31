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
    # Use logging.FileHandler so the file is properly managed and closed on shutdown
    log_file = log_dir / "leads.json"
    file_handler = logging.FileHandler(str(log_file), mode="a", encoding="utf-8")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(file=file_handler.stream),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    
def get_logger(name: str):
    """Возвращает структурированный логгер для модуля."""
    return structlog.get_logger(name)

# Экспортируем дефолтный логгер
logger = get_logger("harmonic_trifid")
