from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.config.settings import settings
import os
from pathlib import Path

router = APIRouter()

class OutreachSettings(BaseModel):
    enabled: bool
    test_mode: bool
    test_chat_id: Optional[int]

@router.get("/outreach")
async def get_outreach_settings():
    """Get current outreach settings"""
    return {
        "enabled": settings.OUTREACH_ENABLED,
        "test_mode": settings.OUTREACH_TEST_MODE,
        "test_chat_id": settings.OUTREACH_TEST_CHAT_ID
    }

@router.post("/outreach")
async def update_outreach_settings(data: OutreachSettings):
    """Update outreach settings and save to .env"""
    try:
        env_path = Path(settings.BASE_DIR) / ".env"
        
        # Читаем текущий .env
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        new_lines = []
        keys_to_update = {
            "OUTREACH_ENABLED": str(data.enabled).lower(),
            "OUTREACH_TEST_MODE": str(data.test_mode).lower(),
            "OUTREACH_TEST_CHAT_ID": str(data.test_chat_id) if data.test_chat_id else ""
        }
        
        updated_keys = set()
        for line in lines:
            key_found = False
            for key in keys_to_update:
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={keys_to_update[key]}\n")
                    updated_keys.add(key)
                    key_found = True
                    break
            if not key_found:
                new_lines.append(line)
        
        # Добавляем новые ключи, если их не было
        for key, val in keys_to_update.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={val}\n")
        
        # Сохраняем в .env
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        # Обновляем в текущем объекте settings (хотя для полной работы бота лучше перезапуск)
        settings.OUTREACH_ENABLED = data.enabled
        settings.OUTREACH_TEST_MODE = data.test_mode
        settings.OUTREACH_TEST_CHAT_ID = data.test_chat_id
        
        return {"message": "Settings updated and saved to .env"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
