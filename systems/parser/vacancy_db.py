"""
Vacancy Database - управление постоянной базой данных вакансий.
Хранит принятые и отклонённые вакансии, предотвращает дубликаты.
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import pandas as pd
from dataclasses import dataclass
from core.config.settings import settings


@dataclass
class Lead:
    """Простая обертка для данных лида из БД."""
    id: int
    hash: str
    text: str
    source_channel: str
    timestamp: float
    message_id: int = None
    chat_id: int = None
    tier: str = None
    informativeness_score: float = 0.0
    needs_review: bool = False
    manual_label: bool = None
    embedding: bytes = None


class VacancyDatabase:
    """Управление базой данных вакансий с поддержкой дедупликации."""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация базы данных.
        
        Args:
            db_path: путь к файлу базы данных SQLite
        """
        self.db_path = db_path or str(settings.VACANCY_DB_PATH)
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
                last_seen TEXT NOT NULL,
                informativeness_score REAL DEFAULT 0.0,
                needs_review INTEGER DEFAULT 0,
                manual_label INTEGER,
                labeled_by TEXT,
                labeled_at TEXT,
                embedding BLOB,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
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

    # ==========================================
    # ACTIVE LEARNING METHODS
    # ==========================================

    def update_lead_informativeness(self, lead_id: int, informativeness: float, needs_review: bool = True):
        """Обновление score информативности."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vacancies 
            SET informativeness_score = ?, needs_review = ?
            WHERE id = ?
        """, (informativeness, 1 if needs_review else 0, lead_id))
        conn.commit()
        conn.close()

    def update_lead_label(self, lead_id: int, is_lead: bool, labeled_by: str, labeled_at: datetime):
        """Сохранение ручной разметки."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vacancies 
            SET manual_label = ?, labeled_by = ?, labeled_at = ?, needs_review = 0
            WHERE id = ?
        """, (1 if is_lead else 0, labeled_by, labeled_at.isoformat(), lead_id))
        conn.commit()
        conn.close()

    def get_labeled_data(self) -> pd.DataFrame:
        """Получение всех размеченных данных для обучения."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("""
            SELECT text, manual_label as is_lead
            FROM vacancies
            WHERE manual_label IS NOT NULL
        """, conn)
        conn.close()
        return df

    def get_recent_leads(self, hours: int = 24) -> List[Lead]:
        """Получение последних лидов за временное окно."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, hash, text, source, timestamp, message_id, chat_id, tier, 
                   informativeness_score, needs_review, manual_label
            FROM vacancies
            WHERE last_seen > ?
        """, (cutoff,))
        
        leads = []
        for row in cursor.fetchall():
            leads.append(Lead(
                id=row[0], hash=row[1], text=row[2], source_channel=row[3],
                timestamp=row[4] or 0.0, message_id=row[5], chat_id=row[6],
                tier=row[7], informativeness_score=row[8] or 0.0,
                needs_review=bool(row[9]), manual_label=row[10]
            ))
        conn.close()
        return leads

    def get_unlabeled_leads_since(self, cutoff_time: datetime) -> List[Lead]:
        """Получение неразмеченных лидов, которые еще не были проанализированы на информативность."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем лиды, у которых еще нет informativeness_score (или она 0)
        cursor.execute("""
            SELECT id, hash, text, source, last_seen, 0, 0, NULL, 
                   informativeness_score, needs_review, manual_label, embedding
            FROM vacancies 
            WHERE last_seen > ? 
              AND manual_label IS NULL
              AND (informativeness_score IS NULL OR informativeness_score = 0)
        """, (cutoff_time.isoformat(),))
        
        leads = []
        for row in cursor.fetchall():
            # Парсим timestamp из string (last_seen)
            try:
                ts = datetime.fromisoformat(row[4]).timestamp()
            except Exception as e:  
                ts = 0.0
                
            leads.append(Lead(
                id=row[0], hash=row[1], text=row[2], source_channel=row[3],
                timestamp=ts, message_id=row[5], chat_id=row[6],
                tier=row[7], informativeness_score=row[8] or 0.0,
                needs_review=bool(row[9]), manual_label=row[10], embedding=row[11]
            ))
        conn.close()
        return leads

    def get_new_labeled_count_since_last_train(self) -> int:
        """Подсчет новых размеченных примеров (заглушка: берет все размеченные)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vacancies WHERE manual_label IS NOT NULL")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def update_lead_embedding(self, lead_id: int, embedding: bytes):
        """Сохранить embedding для лида."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE vacancies SET embedding = ? WHERE id = ?", (embedding, lead_id))
        conn.commit()
        conn.close()

    def get_leads_without_embeddings(self, limit: int = 1000) -> List[Lead]:
        """Получить leads без embeddings для миграции."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, hash, text, source, timestamp, message_id, chat_id, tier, 
                   informativeness_score, needs_review, manual_label, embedding
            FROM vacancies 
            WHERE embedding IS NULL 
            LIMIT ?
        """, (limit,))
        
        leads = []
        for row in cursor.fetchall():
            leads.append(Lead(
                id=row[0], hash=row[1], text=row[2], source_channel=row[3],
                timestamp=row[4] or 0.0, message_id=row[5], chat_id=row[6],
                tier=row[7], informativeness_score=row[8] or 0.0,
                needs_review=bool(row[9]), manual_label=row[10], embedding=row[11]
            ))
        conn.close()
        return leads

    def get_leads_since(self, cutoff_time: datetime, limit: int = 500) -> List[Lead]:
        """Получение лидов с определенной даты."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, hash, text, source, timestamp, message_id, chat_id, tier, 
                   informativeness_score, needs_review, manual_label, embedding
            FROM vacancies
            WHERE last_seen > ?
            ORDER BY last_seen DESC
            LIMIT ?
        """, (cutoff_time.isoformat(), limit))
        
        leads = []
        for row in cursor.fetchall():
            leads.append(Lead(
                id=row[0], hash=row[1], text=row[2], source_channel=row[3],
                timestamp=row[4] or 0.0, message_id=row[5], chat_id=row[6],
                tier=row[7], informativeness_score=row[8] or 0.0,
                needs_review=bool(row[9]), manual_label=row[10], embedding=row[11]
            ))
        conn.close()
        return leads

    # ==========================================
    # DELETION METHODS
    # ==========================================

    def delete_vacancy(self, vacancy_id: int) -> bool:
        """Удаляет вакансию по ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count > 0

    def delete_old_vacancies(self, days: int = 30) -> int:
        """Удаляет старые вакансии."""
        return self.cleanup_old(days)

    def bulk_delete_vacancies(self, vacancy_ids: List[int], batch_size: int = 100) -> Tuple[int, int]:
        """Массовое удаление вакансий батчами."""
        if not vacancy_ids:
            return 0, 0
        
        success_count = 0
        error_count = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i in range(0, len(vacancy_ids), batch_size):
            batch = vacancy_ids[i:i + batch_size]
            try:
                placeholders = ','.join(['?'] * len(batch))
                cursor.execute(f"DELETE FROM vacancies WHERE id IN ({placeholders})", batch)
                success_count += cursor.rowcount
            except Exception as e:
                error_count += len(batch)
                
        conn.commit()
        conn.close()
        return success_count, error_count

    def delete_by_criteria(self, status: str = None, source: str = None, older_than_days: int = None) -> int:
        """Удаление по критериям."""
        query = "DELETE FROM vacancies WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if source:
            query += " AND source = ?"
            params.append(source)
        if older_than_days is not None:
            cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
            query += " AND last_seen < ?"
            params.append(cutoff)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def soft_delete_vacancy(self, vacancy_id: int) -> bool:
        """Мягкое удаление вакансии."""
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vacancies 
            SET is_deleted = 1, deleted_at = ? 
            WHERE id = ?
        """, (now, vacancy_id))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count > 0
