import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]  # playground/Evgeniy/
DB_PATH = os.environ.get("DASHBOARD_DB", str(BASE_DIR / "data/db/bot_data.db"))
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
