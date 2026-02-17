import aiosqlite
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
import pandas as pd
from dataclasses import dataclass
import os
import sys

# Add project root to sys.path to allow running as a script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

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
    """Управление базой данных вакансий с поддержкой дедупликации (асинхронно)."""
    
    def __init__(self, db_path: str = None):
        """
        Инициализация базы данных.
        """
        self.db_path = db_path or str(settings.VACANCY_DB_PATH)
    
    async def init_db(self):
        """Создание таблицы, если её ещё нет (асинхронно)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
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
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash ON vacancies(hash)
            """)
            
            await db.commit()
    
    def _generate_hash(self, text: str) -> str:
        """Генерирует уникальный hash для текста вакансии."""
        clean_text = "".join(text.lower().split())
        return hashlib.md5(clean_text.encode()).hexdigest()

    def _get_similarity(self, text1: str, text2: str) -> float:
        """Вычисляет коэффициент схожести Жаккара."""
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

    async def find_similar(self, text: str, threshold: float = 0.7, days: int = 3) -> Optional[Dict]:
        """Ищет похожую вакансию в базе за последние N дней."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, text, last_seen, source 
                FROM vacancies 
                WHERE status = 'accepted' AND last_seen > ?
            """, (cutoff_date,)) as cursor:
                rows = await cursor.fetchall()
        
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
    
    async def is_processed(self, text: str, fuzzy: bool = True) -> bool:
        """Проверяет, была ли вакансия уже обработана ранее."""
        vacancy_hash = self._generate_hash(text)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM vacancies WHERE hash = ?", (vacancy_hash,)) as cursor:
                result = await cursor.fetchone()
        
        if result:
            return True
            
        if fuzzy:
            similar = await self.find_similar(text)
            if similar:
                return True
                
        return False
    
    async def add_accepted(self, text: str, source: str, direction: str = None, 
                           contact_link: str = None, date: Optional[str] = None) -> bool:
        """Добавляет принятую вакансию в базу."""
        vacancy_hash = self._generate_hash(text)
        if date is None:
            date = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO vacancies (hash, status, text, source, direction, contact_link, response, rejection_reason, first_seen, last_seen)
                    VALUES (?, 'accepted', ?, ?, ?, ?, NULL, NULL, ?, ?)
                """, (vacancy_hash, text, source, direction, contact_link, date, date))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                await db.execute("""
                    UPDATE vacancies SET last_seen = ? WHERE hash = ?
                """, (date, vacancy_hash))
                await db.commit()
                return False
    
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
    async def add_rejected(self, text: str, source: str, reason: str, date: Optional[str] = None) -> bool:
        """Добавляет отклонённую вакансию в базу."""
        vacancy_hash = self._generate_hash(text)
        if date is None:
            date = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO vacancies (hash, status, text, source, direction, contact_link, response, rejection_reason, first_seen, last_seen)
                    VALUES (?, 'rejected', ?, ?, NULL, NULL, NULL, ?, ?, ?)
                """, (vacancy_hash, text, source, reason, date, date))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                await db.execute("""
                    UPDATE vacancies SET last_seen = ? WHERE hash = ?
                """, (date, vacancy_hash))
                await db.commit()
                return False

    async def get_stats(self) -> Dict[str, int]:
        """Получает статистику по всей базе данных."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM vacancies") as cursor:
                row = await cursor.fetchone()
                total = row[0]
            
            async with db.execute("SELECT COUNT(*) FROM vacancies WHERE status = 'accepted'") as cursor:
                row = await cursor.fetchone()
                accepted = row[0]
            
            async with db.execute("SELECT COUNT(*) FROM vacancies WHERE status = 'rejected'") as cursor:
                row = await cursor.fetchone()
                rejected = row[0]
        
        return {
            'total': total,
            'accepted': accepted,
            'rejected': rejected
        }
    
    async def cleanup_old(self, days: int = 30) -> int:
        """Удаляет записи старше указанного количества дней."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("DELETE FROM vacancies WHERE last_seen < ?", (cutoff_date,)) as cursor:
                deleted_count = cursor.rowcount
            await db.commit()
        
        return deleted_count
    
    async def get_recent_accepted(self, limit: int = 100) -> List[Dict]:
        """Получает последние принятые вакансии."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT hash, text, source, direction, contact_link, response, first_seen, last_seen
                FROM vacancies
                WHERE status = 'accepted'
                ORDER BY last_seen DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
        
        results = []
        for row in rows:
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
        return results

    # ==========================================
    # ACTIVE LEARNING METHODS
    # ==========================================

    async def update_lead_informativeness(self, lead_id: int, informativeness: float, needs_review: bool = True):
        """Обновление score информативности."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE vacancies 
                SET informativeness_score = ?, needs_review = ?
                WHERE id = ?
            """, (informativeness, 1 if needs_review else 0, lead_id))
            await db.commit()

    async def update_lead_label(self, lead_id: int, is_lead: bool, labeled_by: str, labeled_at: datetime):
        """Сохранение ручной разметки."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE vacancies 
                SET manual_label = ?, labeled_by = ?, labeled_at = ?, needs_review = 0
                WHERE id = ?
            """, (1 if is_lead else 0, labeled_by, labeled_at.isoformat(), lead_id))
            await db.commit()

    async def get_labeled_data(self) -> pd.DataFrame:
        """Получение всех размеченных данных для обучения."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT text, manual_label as is_lead
                FROM vacancies
                WHERE manual_label IS NOT NULL
            """) as cursor:
                rows = await cursor.fetchall()
        
        return pd.DataFrame(rows, columns=['text', 'is_lead']) if rows else pd.DataFrame(columns=['text', 'is_lead'])

    async def get_recent_leads(self, hours: int = 24) -> List[Lead]:
        """Получение последних лидов за временное окно."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, hash, text, source, last_seen, message_id, chat_id, tier, 
                       informativeness_score, needs_review, manual_label
                FROM vacancies
                WHERE last_seen > ?
            """, (cutoff,)) as cursor:
                rows = await cursor.fetchall()
        
        leads = []
        for row in rows:
            try:
                ts = datetime.fromisoformat(row[4]).timestamp()
            except Exception as e:  
                ts = 0.0
            leads.append(Lead(
                id=row[0], hash=row[1], text=row[2], source_channel=row[3],
                timestamp=ts, message_id=row[5], chat_id=row[6],
                tier=row[7], informativeness_score=row[8] or 0.0,
                needs_review=bool(row[9]), manual_label=row[10]
            ))
        return leads

    async def get_unlabeled_leads_since(self, cutoff_time: datetime) -> List[Lead]:
        """Получение неразмеченных лидов."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, hash, text, source, last_seen, 0, 0, NULL, 
                       informativeness_score, needs_review, manual_label, embedding
                FROM vacancies 
                WHERE last_seen > ? 
                  AND manual_label IS NULL
                  AND (informativeness_score IS NULL OR informativeness_score = 0)
            """, (cutoff_time.isoformat(),)) as cursor:
                rows = await cursor.fetchall()
        
        leads = []
        for row in rows:
            try:
                ts = datetime.fromisoformat(row[4]).timestamp()
            except Exception as e:  
                ts = 0.0
                
            leads.append(Lead(
                id=row[0], hash=row[1], text=row[2], source_channel=row[3],
                timestamp=ts, message_id=5, chat_id=6,
                tier=None, informativeness_score=row[8] or 0.0,
                needs_review=bool(row[9]), manual_label=row[10], embedding=row[11]
            ))
        return leads

    async def get_new_labeled_count_since_last_train(self) -> int:
        """Подсчет новых размеченных примеров."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM vacancies WHERE manual_label IS NOT NULL") as cursor:
                row = await cursor.fetchone()
                return row[0]

    async def update_lead_embedding(self, lead_id: int, embedding: bytes):
        """Сохранить embedding для лида."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE vacancies SET embedding = ? WHERE id = ?", (embedding, lead_id))
            await db.commit()

    async def get_leads_without_embeddings(self, limit: int = 1000) -> List[Lead]:
        """Получить leads без embeddings."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, hash, text, source, last_seen, message_id, chat_id, tier, 
                       informativeness_score, needs_review, manual_label, embedding
                FROM vacancies 
                WHERE embedding IS NULL 
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
        
        leads = []
        for row in rows:
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
        return leads

    async def get_leads_since(self, cutoff_time: datetime, limit: int = 500) -> List[Lead]:
        """Получение лидов с определенной даты."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, hash, text, source, last_seen, message_id, chat_id, tier, 
                       informativeness_score, needs_review, manual_label, embedding
                FROM vacancies
                WHERE last_seen > ?
                ORDER BY last_seen DESC
                LIMIT ?
            """, (cutoff_time.isoformat(), limit)) as cursor:
                rows = await cursor.fetchall()
        
        leads = []
        for row in rows:
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
        return leads

    # ==========================================
    # DELETION METHODS (ASYNC)
    # ==========================================

    async def delete_vacancy(self, vacancy_id: int) -> bool:
        """Удаляет вакансию по ID."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,)) as cursor:
                count = cursor.rowcount
            await db.commit()
        return count > 0

    async def delete_old_vacancies(self, days: int = 30) -> int:
        """Удаляет старые вакансии."""
        return await self.cleanup_old(days)

    async def bulk_delete_vacancies(self, vacancy_ids: List[int], batch_size: int = 100) -> Tuple[int, int]:
        """Массовое удаление вакансий батчами."""
        if not vacancy_ids:
            return 0, 0
        
        success_count = 0
        error_count = 0
        
        async with aiosqlite.connect(self.db_path) as db:
            for i in range(0, len(vacancy_ids), batch_size):
                batch = vacancy_ids[i:i + batch_size]
                try:
                    placeholders = ','.join(['?'] * len(batch))
                    async with db.execute(f"DELETE FROM vacancies WHERE id IN ({placeholders})", batch) as cursor:
                        success_count += cursor.rowcount
                except Exception as e:  
                    error_count += len(batch)
            await db.commit()
        return success_count, error_count

    async def delete_by_criteria(self, status: str = None, source: str = None, older_than_days: int = None) -> int:
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
            
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                count = cursor.rowcount
            await db.commit()
        return count

    async def soft_delete_vacancy(self, vacancy_id: int) -> bool:
        """Мягкое удаление вакансии."""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                UPDATE vacancies 
                SET is_deleted = 1, deleted_at = ? 
                WHERE id = ?
            """, (now, vacancy_id)) as cursor:
                count = cursor.rowcount
            await db.commit()
        return count > 0

if __name__ == "__main__":
    db = VacancyDatabase("test_vacancies.db")
    async def run_test():
        print("Testing VacancyDatabase deletion methods...")
        await db.init_db()
        
        # Add dummy data
        await db.add_accepted("Test vacancy 1", "Channel A", "SEO")
        await db.add_accepted("Test vacancy 2", "Channel B", "Dev")
        
        # Test delete_vacancy
        res = await db.delete_vacancy(1)
        print(f"Delete vacancy 1: {res}")
        
        # Test bulk_delete
        s, e = await db.bulk_delete_vacancies([1, 2])
        print(f"Bulk delete results: {s} success, {e} errors")
        
        # Test delete_by_criteria
        count = await db.delete_by_criteria(status="accepted")
        print(f"Deleted by criteria: {count}")
        
        # Test soft_delete
        await db.add_accepted("Soft delete test", "Channel C")
        res = await db.soft_delete_vacancy(3)
        print(f"Soft delete vacancy 3: {res}")
        
        import os
        if os.path.exists("test_vacancies.db"):
            os.remove("test_vacancies.db")
        print("Tests completed.")
    
    import asyncio
    asyncio.run(run_test())
