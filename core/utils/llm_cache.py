"""
LLM Cache для экономии API calls.
Кэширует результаты LLM анализа для одинаковых запросов.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class LLMCache:
    """
    Кэш для LLM ответов чтобы не тратить API calls на одинаковые запросы.
    """
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_key(self, prompt: str, text: str) -> str:
        """Генерация cache key из промпта и текста."""
        content = f"{prompt[:200]}||{text[:500]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, text: str) -> Optional[Dict[Any, Any]]:
        """Получить кэшированный результат."""
        key = self._get_cache_key(prompt, text)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        # Проверка TTL
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime > self.ttl:
            cache_file.unlink()
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def set(self, prompt: str, text: str, result: Dict[Any, Any]):
        """Сохранить результат в кэш."""
        key = self._get_cache_key(prompt, text)
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def clear_old(self) -> int:
        """Очистка устаревших записей."""
        cleared = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.now() - mtime > self.ttl:
                    cache_file.unlink()
                    cleared += 1
            except Exception:
                continue
        return cleared

# Глобальный инстанс
from core.config.settings import settings
llm_cache = LLMCache(settings.BASE_DIR / "cache" / "llm", ttl_hours=24)
