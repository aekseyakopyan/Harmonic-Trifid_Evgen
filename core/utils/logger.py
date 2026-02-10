import logging
import sys
from core.config.settings import settings

def setup_logger(name: str):
    # Маппинг системных имен для логов
    display_names = {
        "bot_system": "АЛЕКСЕЙ",
        "gwen": "ГВЕН",
        "parser": "ПАРСЕР",
        "dashboard": "ДАШБОРД"
    }
    display_name = display_names.get(name, name.upper())
    
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    
    formatter = logging.Formatter(
        f'%(asctime)s - [{display_name}] - %(levelname)s - %(message)s'
    )
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler("logs/bot.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(file_handler)
        
    return logger

# Global default logger
logger = setup_logger("bot_system")
