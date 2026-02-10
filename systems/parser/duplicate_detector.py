
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

class DuplicateDetector:
    """
    Детектор дубликатов на основе fuzzy matching и временных окон.
    """
    
    def __init__(self, db_path: str = "vacancies.db"):
        self.db_path = db_path
    
    def get_text_fingerprint(self, text: str) -> str:
        """
        Создаёт нормализованный отпечаток текста.
        """
        # Убираем шум: эмодзи, хештеги, упоминания, URL
        clean = re.sub(r'http\S+', '', text)
        clean = re.sub(r'@\w+', '', clean)
        clean = re.sub(r'#\w+', '', clean)
        clean = re.sub(r'[^\w\s]', '', clean)
        clean = ' '.join(clean.lower().split())
        
        # Хеш от нормализованного текста
        return hashlib.md5(clean.encode()).hexdigest()
    
    def find_similar_recent(
        self, 
        text: str, 
        time_window_hours: int = 48,
        similarity_threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Находит похожие сообщения за последние N часов.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Временное окно
            cutoff = datetime.now() - timedelta(hours=time_window_hours)
            cutoff_str = cutoff.isoformat()
            
            # Выбираем недавние сообщения
            cursor.execute("""
                SELECT hash, text, last_seen, source 
                FROM vacancies 
                WHERE last_seen > ? 
                ORDER BY last_seen DESC
                LIMIT 500
            """, (cutoff_str,))
            
            recent = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"Error reading DB in DuplicateDetector: {e}")
            return []
        
        # Fuzzy matching
        similarities = []
        text_lower = text.lower()
        
        for row in recent:
            hash_id, existing_text, last_seen, source = row
            if not existing_text: continue
            
            ratio = SequenceMatcher(None, text_lower, existing_text.lower()).ratio()
            
            if ratio >= similarity_threshold:
                similarities.append({
                    "hash": hash_id,
                    "text": existing_text[:100],
                    "similarity": ratio,
                    "last_seen": last_seen,
                    "source": source
                })
        
        return sorted(similarities, key=lambda x: x["similarity"], reverse=True)
    
    def mark_as_duplicate(self, hash_id: str, original_hash: str):
        """
        Помечает сообщение как дубликат в базе данных.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE vacancies 
                SET status = 'rejected',
                    rejection_reason = ?
                WHERE hash = ?
            """, (f"DUPLICATE_OF: {original_hash}", hash_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating DB in DuplicateDetector: {e}")
