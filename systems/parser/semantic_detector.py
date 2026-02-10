import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from core.config.settings import settings

class SemanticDuplicateDetector:
    """
    Детектор дубликатов на основе Sentence Embeddings и косинусного сходства.
    """
    def __init__(self, model_name: str = "cointegrated/rubert-tiny"):
        self.model = SentenceTransformer(model_name)
        self.threshold = 0.75  # ТЗ: 0.75

    def get_embedding(self, text: str) -> np.ndarray:
        """Генерирует эмбеддинг для текста."""
        return self.model.encode(text)

    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Вычисляет косинусное сходство между двумя векторами."""
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(emb1, emb2) / (norm1 * norm2)

    def is_duplicate(self, new_text: str, existing_leads: List[Dict[str, Any]]) -> tuple[bool, float, Optional[str]]:
        """
        Проверка текста на семантический дубликат.
        Args:
            new_text: Текст нового сообщения
            existing_leads: Список лидов из БД (с эмбеддингами)
        Returns:
            (is_duplicate, max_similarity, original_hash)
        """
        new_emb = self.get_embedding(new_text)
        max_sim = 0.0
        match_hash = None
        
        for lead in existing_leads:
            # Предполагаем, что эмбеддинг хранится как np.ndarray или BLOB
            lead_emb = lead.get('embedding')
            if lead_emb is None:
                continue
            
            sim = self.calculate_similarity(new_emb, lead_emb)
            if sim > max_sim:
                max_sim = sim
                match_hash = lead.get('hash')
        
        return (max_sim >= self.threshold, float(max_sim), match_hash)

# Сохраняем обратную совместимость или обновляем DuplicateDetector
