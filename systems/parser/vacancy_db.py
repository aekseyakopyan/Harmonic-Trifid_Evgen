"""
Vacancy Database - управление постоянной базой данных вакансий.
Хранит принятые и отклонённые вакансии, предотвращает дубликаты.
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List


class VacancyDatabase:
    """Управление базой данных вакансий с поддержкой дедупликации."""
    
    def __init__(self, db_path: str = "vacancies.db"):
        """
        Инициализация базы данных.
        
        Args:
            db_path: путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Создание таблицы, если её ещё нет."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                direction TEXT,
                contact_link TEXT,
                response TEXT,
                draft_response TEXT,
                rejection_reason TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        
        # Индекс для быстрого поиска по hash
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash ON vacancies(hash)
        """)
        
        conn.commit()
        conn.close()
    
    def _generate_hash(self, text: str) -> str:
        """
        Генерирует уникальный hash для текста вакансии.
        """
        clean_text = "".join(text.lower().split())
        return hashlib.md5(clean_text.encode()).hexdigest()

    def _get_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет коэффициент схожести Жаккара для двух текстов на основе шинглов (триграмм).
        """
        def get_shingles(text: str, k: int = 3):
            clean = "".join(char for char in text.lower() if char.isalnum() or char.isspace())
            return set(clean[i:i+k] for i in range(len(clean) - k + 1))
        
        set1 = get_shingles(text1)
        set2 = get_shingles(text2)
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union

    def find_similar(self, text: str, threshold: float = 0.7, days: int = 3) -> Optional[Dict]:
        """
        Ищет похожую вакансию в базе за последние N дней.
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Берем только принятые вакансии за последнее время
        cursor.execute("""
            SELECT id, text, last_seen, source 
            FROM vacancies 
            WHERE status = 'accepted' AND last_seen > ?
        """, (cutoff_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        for row in rows:
            similarity = self._get_similarity(text, row[1])
            if similarity >= threshold:
                return {
                    'id': row[0],
                    'text': row[1],
                    'last_seen': row[2],
                    'source': row[3],
                    'similarity': similarity
                }
        
        return None
    
    def is_processed(self, text: str, fuzzy: bool = True) -> bool:
        """
        Проверяет, была ли вакансия уже обработана ранее (точно или похоже).
        """
        # 1. Точная проверка по хешу
        vacancy_hash = self._generate_hash(text)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vacancies WHERE hash = ?", (vacancy_hash,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return True
            
        # 2. Нечеткая проверка (если включена)
        if fuzzy:
            similar = self.find_similar(text)
            if similar:
                return True
                
        return False
    
    def add_accepted(self, text: str, source: str, direction: str = None, 
                     contact_link: str = None, date: Optional[str] = None) -> bool:
        """
        Добавляет принятую вакансию в базу.
        
        Args:
            text: текст вакансии
            source: источник (название канала)
            direction: направление/специализация (SEO, Контекст, и т.д.)
            contact_link: прямая ссылка на контакт (t.me/username)
            date: дата обнаружения (ISO format), если None - текущая дата
            
        Returns:
            True если успешно добавлено, False если уже существует
        """
        vacancy_hash = self._generate_hash(text)
        if date is None:
            date = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO vacancies (hash, status, text, source, direction, contact_link, response, rejection_reason, first_seen, last_seen)
                VALUES (?, 'accepted', ?, ?, ?, ?, NULL, NULL, ?, ?)
            """, (vacancy_hash, text, source, direction, contact_link, date, date))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Вакансия уже существует, обновляем last_seen
            cursor.execute("""
                UPDATE vacancies SET last_seen = ? WHERE hash = ?
            """, (date, vacancy_hash))
            conn.commit()
            return False
        finally:
            conn.close()
    
    def add_rejected(self, text: str, source: str, reason: str, date: Optional[str] = None) -> bool:
        """
        Добавляет отклонённую вакансию в базу.
        
        Args:
            text: текст вакансии
            source: источник (название канала)
            reason: причина отклонения
            date: дата обнаружения (ISO format), если None - текущая дата
            
        Returns:
            True если успешно добавлено, False если уже существует
        """
        vacancy_hash = self._generate_hash(text)
        if date is None:
            date = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO vacancies (hash, status, text, source, direction, contact_link, response, rejection_reason, first_seen, last_seen)
                VALUES (?, 'rejected', ?, ?, NULL, NULL, NULL, ?, ?, ?)
            """, (vacancy_hash, text, source, reason, date, date))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Вакансия уже существует, обновляем last_seen
            cursor.execute("""
                UPDATE vacancies SET last_seen = ? WHERE hash = ?
            """, (date, vacancy_hash))
            conn.commit()
            return False
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Получает статистику по всей базе данных.
        
        Returns:
            Словарь со статистикой: total, accepted, rejected
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM vacancies")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vacancies WHERE status = 'accepted'")
        accepted = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vacancies WHERE status = 'rejected'")
        rejected = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'accepted': accepted,
            'rejected': rejected
        }
    
    def cleanup_old(self, days: int = 30) -> int:
        """
        Удаляет записи старше указанного количества дней.
        
        Args:
            days: количество дней
            
        Returns:
            Количество удалённых записей
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM vacancies WHERE last_seen < ?", (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def get_recent_accepted(self, limit: int = 100) -> List[Dict]:
        """
        Получает последние принятые вакансии для Базы Лидов.
        
        Args:
            limit: максимальное количество записей
            
        Returns:
            Список словарей с информацией о вакансиях
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT hash, text, source, direction, contact_link, response, first_seen, last_seen
            FROM vacancies
            WHERE status = 'accepted'
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'hash': row[0],
                'text': row[1],
                'source': row[2],
                'direction': row[3],
                'contact_link': row[4],
                'response': row[5],
                'first_seen': row[6],
                'last_seen': row[7]
            })
        
        conn.close()
        return results
