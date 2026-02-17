import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # System Paths
    @property
    def DATA_DIR(self) -> Path:
        p = self.BASE_DIR / "data"
        p.mkdir(exist_ok=True)
        return p

    @property
    def LOG_DIR(self) -> Path:
        p = self.BASE_DIR / "logs"
        p.mkdir(exist_ok=True)
        return p

    @property
    def SESSIONS_DIR(self) -> Path:
        p = self.DATA_DIR / "sessions"
        p.mkdir(exist_ok=True)
        return p

    @property
    def DB_DIR(self) -> Path:
        p = self.DATA_DIR / "db"
        p.mkdir(exist_ok=True)
        return p

    @property
    def REPORTS_DIR(self) -> Path:
        p = self.BASE_DIR / "reports"
        p.mkdir(exist_ok=True)
        return p

    @property
    def DAILY_REPORTS_DIR(self) -> Path:
        p = self.REPORTS_DIR / "daily_summaries"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def PARSER_REPORTS_DIR(self) -> Path:
        p = self.REPORTS_DIR / "parsing_dumps"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Telegram User API
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_PHONE: str = ""
    
    # Monitored chats (comma-separated list of chat IDs)
    MONITORED_CHATS: str = ""
    
    # Blacklisted usernames (comma-separated, without @)
    BLACKLISTED_USERNAMES: str = "BotFather"
    ADMIN_IDS: str = ""  
    ADMIN_TELEGRAM_USERNAME: str = "_a1exeyy"  # Your username for escalations

    OPENROUTER_API_KEY: str = ""
    # Лучшая модель цена/качество (Уровень GPT-4, но в 20 раз дешевле)
    OPENROUTER_MODEL: str = "deepseek/deepseek-chat"
    
    # Список моделей (платные, используют кредиты OpenRouter)
    FALLBACK_MODELS: List[str] = [
        "google/gemini-2.0-flash-001",       # Очень быстрая и дешевая
        "meta-llama/llama-3.3-70b-instruct", # Надежный Open Source
        "anthropic/claude-3-haiku",          # Экономный вариант от Anthropic
        "openai/gpt-4o-mini",                # Экономный вариант от OpenAI
        
        # Резерв ("Тяжелая артиллерия" на случай сбоев дешевых)
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o"
    ]
    
    # Ollama Configuration
    OLLAMA_URL: str = "http://localhost:11434/api/chat"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    
    OPENAI_API_KEY: str = ""  # For Whisper STT (optional)

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/db/bot_data.db"
    
    @property
    def async_database_url(self) -> str:
        """Returns absolute path for async database."""
        if self.DATABASE_URL.startswith("sqlite"):
            db_path = self.DATABASE_URL.split("///")[-1]
            abs_path = self.BASE_DIR / db_path
            return f"sqlite+aiosqlite:///{abs_path}"
        return self.DATABASE_URL
    
    @property
    def VACANCY_DB_PATH(self) -> Path:
        return self.DB_DIR / "vacancies.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Supervisor Bot (для уведомлений об ошибках)
    SUPERVISOR_BOT_TOKEN: Optional[str] = None
    SUPERVISOR_CHAT_ID: str = "_a1exeyy"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True
    
    # Outreach Settings
    OUTREACH_ENABLED: bool = False
    OUTREACH_TEST_MODE: bool = True
    OUTREACH_TEST_CHAT_ID: Optional[int] = None
    AUTO_OUTREACH: bool = True  # Fully automatic mode
    TARGET_KEYWORDS: str = "seo, сео, авито, avito, директ, контекст, маркетолог, сайт, тильда, tilda"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @property
    def monitored_chat_ids(self) -> List[int]:
        if not self.MONITORED_CHATS:
            return []
        return [int(x.strip()) for x in self.MONITORED_CHATS.split(",") if x.strip()]

    @property
    def blacklisted_usernames(self) -> List[str]:
        if not self.BLACKLISTED_USERNAMES:
            return []
        return [x.strip().lstrip('@').lower() for x in self.BLACKLISTED_USERNAMES.split(",") if x.strip()]
    
    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

# Instantiate settings
settings = Settings(_env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"))
