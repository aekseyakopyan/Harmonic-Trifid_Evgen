"""
Semantic Duplicate Detection через sentence embeddings.
Hybrid approach: semantic similarity + exact match fallback.
"""

from difflib import SequenceMatcher
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import asyncio
from typing import Tuple, Optional, List
from datetime import datetime, timedelta

from core.utils.structured_logger import get_logger

logger = get_logger(__name__)


class DuplicateDetector:
    """
    Детектор дубликатов с поддержкой semantic similarity.
    
    Стратегии:
    1. Semantic similarity через embeddings (primary)
    2. Exact match через SequenceMatcher (fallback)
    3. 48-hour time window для кросспостинга
    """
    
    _instance = None
    
    def __new__(cls, db_manager=None):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_manager=None):
        if self._initialized:
            if db_manager is not None and self.db is None:
                self.db = db_manager
                logger.debug("duplicate_detector_db_updated")
            return
        
        self.db = db_manager
        self.time_window_hours = 48
        
        # Thresholds
        self.semantic_threshold = 0.75  # Cosine similarity для semantic duplicates
        self.exact_threshold = 0.85      # SequenceMatcher для exact match
        self.semantic_low_bound = 0.60   # Ниже этого → fallback на exact match
        
        # Sentence encoder для semantic similarity
        try:
            self.encoder = SentenceTransformer("cointegrated/rubert-tiny")
            self.semantic_enabled = True
            logger.info(
                "semantic_dedup_initialized",
                model="cointegrated/rubert-tiny",
                semantic_threshold=self.semantic_threshold,
                exact_threshold=self.exact_threshold
            )
        except Exception as e:
            logger.error("encoder_load_failed", error=str(e))
            self.encoder = None
            self.semantic_enabled = False
        
        # Cache для embeddings (в памяти для быстрого доступа)
        self.embeddings_cache = {}
        self.cache_max_size = 1000
        
        self._initialized = True
    
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """
        Получить sentence embedding для текста.
        Использует cache для ускорения.
        
        Args:
            text: текст для кодирования
            
        Returns:
            numpy array embedding или None при ошибке
        """
        if not self.semantic_enabled:
            return None
        
        # Нормализация текста для cache key
        text_key = text.lower().strip()[:500]  # Первые 500 символов
        
        # Проверка cache
        if text_key in self.embeddings_cache:
            return self.embeddings_cache[text_key]
        
        try:
            # Кодирование
            embedding = self.encoder.encode(text)
            
            # Сохранение в cache с ограничением размера
            if len(self.embeddings_cache) >= self.cache_max_size:
                # Удалить 10% старых записей (простая стратегия)
                items_to_remove = list(self.embeddings_cache.keys())[:100]
                for key in items_to_remove:
                    del self.embeddings_cache[key]
            
            self.embeddings_cache[text_key] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error("encoding_failed", error=str(e)[:200])
            return None
    
    def serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """
        Сериализовать embedding для хранения в БД.
        
        Args:
            embedding: numpy array
            
        Returns:
            bytes для записи в BLOB колонку
        """
        return pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)
    
    def deserialize_embedding(self, data: bytes) -> Optional[np.ndarray]:
        """
        Десериализовать embedding из БД.
        
        Args:
            data: bytes из BLOB колонки
            
        Returns:
            numpy array или None
        """
        if not data:
            return None
        
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error("embedding_deserialization_failed", error=str(e))
            return None
    
    def calculate_semantic_similarity(
        self,
        text1: str,
        text2: str,
        embedding1: Optional[np.ndarray] = None,
        embedding2: Optional[np.ndarray] = None
    ) -> float:
        """
        Расчет semantic similarity между двумя текстами.
        
        Args:
            text1, text2: тексты для сравнения
            embedding1, embedding2: опциональные pre-computed embeddings
            
        Returns:
            cosine similarity [0, 1]
        """
        # Получить embeddings
        if embedding1 is None:
            embedding1 = self.encode_text(text1)
        if embedding2 is None:
            embedding2 = self.encode_text(text2)
        
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        # Cosine similarity
        similarity = cosine_similarity(
            [embedding1],
            [embedding2]
        )[0][0]
        
        return float(similarity)
    
    def calculate_exact_similarity(self, text1: str, text2: str) -> float:
        """
        Расчет exact match similarity через SequenceMatcher.
        Старый метод, используется как fallback.
        
        Args:
            text1, text2: тексты для сравнения
            
        Returns:
            similarity ratio [0, 1]
        """
        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()
        
        return SequenceMatcher(None, text1_lower, text2_lower).ratio()
    
    async def is_duplicate(
        self,
        text: str,
        message_id: int,
        source_channel: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Проверка является ли текст дубликатом существующих лидов.
        
        Hybrid approach:
        1. Semantic similarity (primary) - для перефразировок
        2. Exact match (fallback) - для копипаста
        
        Args:
            text: текст лида для проверки
            message_id: ID сообщения
            source_channel: канал источник (для логирования)
            
        Returns:
            (is_duplicate, similarity_score, method)
        """
        if not self.db:
            logger.warning("duplicate_check_skipped", reason="no_db_manager")
            return False, 0.0, "no_db"
        
        # Получить recent leads (48 часов)
        cutoff_time = datetime.now() - timedelta(hours=self.time_window_hours)
        
        try:
            # VacancyDatabase methods are synchronous but we call them in thread to avoid blocking loop if needed
            # For simplicity, since it's sqlite, we just call them (blocking).
            recent_leads = await asyncio.to_thread(
                self.db.get_leads_since,
                cutoff_time,
                limit=500
            )
        except Exception as e:
            logger.error("db_query_failed", error=str(e)[:200])
            return False, 0.0, "db_error"
        
        if not recent_leads:
            return False, 0.0, "no_recent_leads"
        
        # Кодировать новый текст
        new_embedding = self.encode_text(text)
        
        # Проверка каждого recent lead
        max_semantic_sim = 0.0
        max_exact_sim = 0.0
        duplicate_found = False
        matching_lead_id = None
        method = "none"
        
        for lead in recent_leads:
            # Пропустить самого себя
            if lead.message_id == message_id:
                continue
            
            # Стратегия 1: Semantic similarity
            if self.semantic_enabled and new_embedding is not None:
                # Получить embedding из БД или вычислить
                lead_embedding = None
                
                if hasattr(lead, 'embedding') and lead.embedding:
                    lead_embedding = self.deserialize_embedding(lead.embedding)
                
                if lead_embedding is None:
                    lead_embedding = self.encode_text(lead.text)
                
                if lead_embedding is not None:
                    semantic_sim = self.calculate_semantic_similarity(
                        text, lead.text,
                        embedding1=new_embedding,
                        embedding2=lead_embedding
                    )
                    
                    max_semantic_sim = max(max_semantic_sim, semantic_sim)
                    
                    # Проверка threshold
                    if semantic_sim > self.semantic_threshold:
                        duplicate_found = True
                        matching_lead_id = lead.id
                        method = "semantic"
                        
                        logger.info(
                            "semantic_duplicate_found",
                            new_message_id=message_id,
                            duplicate_message_id=lead.message_id,
                            similarity=semantic_sim,
                            source=source_channel
                        )
                        
                        return True, semantic_sim, method
            
            # Стратегия 2: Exact match (fallback)
            # Применяется если semantic similarity низкая или unavailable
            if not self.semantic_enabled or max_semantic_sim < self.semantic_low_bound:
                exact_sim = self.calculate_exact_similarity(text, lead.text)
                max_exact_sim = max(max_exact_sim, exact_sim)
                
                if exact_sim > self.exact_threshold:
                    duplicate_found = True
                    matching_lead_id = lead.id
                    method = "exact_match"
                    
                    logger.info(
                        "exact_duplicate_found",
                        new_message_id=message_id,
                        duplicate_message_id=lead.message_id,
                        similarity=exact_sim,
                        source=source_channel
                    )
                    
                    return True, exact_sim, method
        
        # Дубликат не найден
        logger.debug(
            "duplicate_check_passed",
            message_id=message_id,
            max_semantic_sim=max_semantic_sim,
            max_exact_sim=max_exact_sim,
            recent_leads_count=len(recent_leads)
        )
        
        return False, max(max_semantic_sim, max_exact_sim), method
    
    def get_statistics(self) -> dict:
        """
        Получить статистику работы детектора.
        
        Returns:
            {
                "semantic_enabled": bool,
                "cache_size": int,
                "time_window_hours": int,
                "semantic_threshold": float,
                "exact_threshold": float
            }
        """
        return {
            "semantic_enabled": self.semantic_enabled,
            "cache_size": len(self.embeddings_cache),
            "cache_max_size": self.cache_max_size,
            "time_window_hours": self.time_window_hours,
            "semantic_threshold": self.semantic_threshold,
            "exact_threshold": self.exact_threshold
        }
    
    async def precompute_embeddings_batch(
        self,
        leads: List,
        batch_size: int = 32
    ) -> int:
        """
        Batch вычисление embeddings для existing leads.
        Используется для миграции или periodic updates.
        
        Args:
            leads: список lead объектов
            batch_size: размер батча для encoding
            
        Returns:
            количество обработанных leads
        """
        if not self.semantic_enabled:
            logger.warning("precompute_skipped", reason="semantic_disabled")
            return 0
        
        processed_count = 0
        
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i + batch_size]
            
            try:
                # Batch encoding
                texts = [lead.text for lead in batch]
                embeddings = self.encoder.encode(texts)
                
                # Сохранить в БД
                for lead, embedding in zip(batch, embeddings):
                    serialized = self.serialize_embedding(embedding)
                    
                    await asyncio.to_thread(
                        self.db.update_lead_embedding,
                        lead_id=lead.id,
                        embedding=serialized
                    )
                
                processed_count += len(batch)
                
                logger.info(
                    "embeddings_batch_processed",
                    processed=processed_count,
                    total=len(leads)
                )
                
            except Exception as e:
                logger.error(
                    "batch_encoding_failed",
                    batch_start=i,
                    error=str(e)[:200]
                )
        
        return processed_count


# Singleton instance factory
def get_duplicate_detector(db_manager=None):
    """Factory для получения singleton instance"""
    return DuplicateDetector(db_manager)
