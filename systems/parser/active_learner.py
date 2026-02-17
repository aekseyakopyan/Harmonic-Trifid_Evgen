"""
Active Learning Pipeline для автоматического отбора информативных примеров.
Использует Uncertainty Sampling и Query by Committee для минимизации ручной разметки.
"""

from systems.parser.bert_classifier import bert_classifier
from systems.parser.ml_classifier import ml_classifier
from systems.parser.vacancy_db import VacancyDatabase, Lead
from core.utils.structured_logger import get_logger
from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime, timedelta
import torch

logger = get_logger(__name__)


class ActiveLearningPipeline:
    """
    Pipeline для интеллектуального отбора примеров на разметку.
    """
    
    def __init__(self):
        self.db = VacancyDatabase()
        
        # Committee из моделей (используем существующие инстансы если возможно)
        self.bert_tiny = bert_classifier
        self.ml_classifier = ml_classifier
        
        self.uncertainty_threshold = 0.4 
        self.weekly_batch_size = 50
        
        logger.info(
            "active_learner_initialized",
            weekly_batch_size=self.weekly_batch_size
        )
    
    def calculate_informativeness(self, text: str) -> Dict[str, float]:
        """Расчет informativeness score для текста."""
        predictions = []
        
        # BERT prediction
        bert_pred = self.bert_tiny.predict(text)
        predictions.append(bert_pred["confidence"])
        
        # ML prediction
        ml_pred = self.ml_classifier.predict(text)
        predictions.append(ml_pred["confidence"])
        
        predictions = np.array(predictions)
        
        # 1. Least Confidence: 1 - max(P(y))
        least_confidence = 1 - np.max(predictions)
        
        # 2. Margin Sampling
        margin = min([abs(p - 0.5) for p in predictions])
        margin_score = 1 - (margin * 2) 
        
        # 3. Entropy
        def binary_entropy(p):
            p = np.clip(p, 1e-10, 1 - 1e-10)
            return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
        
        avg_entropy = np.mean([binary_entropy(p) for p in predictions])
        
        # 4. Committee Variance
        committee_variance = np.var(predictions)
        
        informativeness = (
            0.25 * least_confidence +
            0.35 * margin_score +
            0.20 * avg_entropy +
            0.20 * committee_variance
        )
        
        return {
            "informativeness": float(informativeness),
            "least_confidence": float(least_confidence),
            "margin": float(margin_score),
            "entropy": float(avg_entropy),
            "committee_variance": float(committee_variance),
            "predictions": predictions.tolist()
        }
    
    async def select_informative_samples(self, time_window_hours: int = 168) -> List[Dict]:
        """Отбор самых информативных неразмеченных лидов."""
        logger.info("selecting_informative_samples", hours=time_window_hours)
        
        await self.db.init_db()
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        unlabeled_leads = await self.db.get_unlabeled_leads_since(cutoff_time)
        
        # Фильтруем WARM (самые спорные)
        warm_leads = [lead for lead in unlabeled_leads if lead.tier == 'WARM']
        
        # Если WARM мало, берем все неразмеченные
        candidates = warm_leads if len(warm_leads) >= 10 else unlabeled_leads
        
        scored_leads = []
        for lead in candidates[:200]:
            try:
                # В VacancyDatabase.get_unlabeled_leads_since мы получаем объекты Lead
                text = lead.text
                if not text:
                  continue
                
                scores_dict = self.calculate_informativeness(text)
                # scores_dict возвращает dict с ключами "informativeness", "least_confidence", etc.
                
                # Добавляем метаданные
                item = {
                    "lead_id": lead.id,
                    "message_id": lead.message_id,
                    "text": text,
                    "source": lead.source_channel,
                    "timestamp": lead.timestamp,
                }
                item.update(scores_dict) # Merge scores into item
                
                scored_leads.append(item)
            except Exception as e:
                logger.error(f"informativeness_failed for lead {lead.id}: {e}")
        
        scored_leads.sort(key=lambda x: x["informativeness"], reverse=True)
        top_samples = scored_leads[:self.weekly_batch_size]
        
        for sample in top_samples:
            await self.db.update_lead_informativeness(
                lead_id=sample["lead_id"],
                informativeness=sample["informativeness"],
                needs_review=True
            )
            
        return top_samples
    
    async def trigger_retrain(self) -> Dict:
        """Запуск переобучения при накоплении данных."""
        await self.db.init_db()
        new_labeled_count = await self.db.get_new_labeled_count_since_last_train()
        
        if new_labeled_count >= 50:
            return await self.retrain_pipeline()
        
        return {
            "retrain_triggered": False,
            "new_labeled_count": new_labeled_count,
            "reason": f"Need {50 - new_labeled_count} more labeled samples"
        }
    
    async def retrain_pipeline(self) -> Dict:
        """Пайплайн переобучения."""
        logger.info("retrain_pipeline_started")
        try:
            await self.db.init_db()
            train_data = await self.db.get_labeled_data()
            if len(train_data) < 50:
                return {"status": "failed", "reason": "insufficient_data", "retrain_triggered": False}
            
            from systems.parser.train_bert import train_bert_classifier
            metrics = train_bert_classifier(
                train_data=train_data,
                output_dir="models/bert_retrained"
            )
            return {"status": "success", "metrics": metrics, "model_version": datetime.now().isoformat(), "retrain_triggered": True}
        except Exception as e:
            logger.error("retrain_failed", error=str(e))
            return {"status": "failed", "error": str(e), "retrain_triggered": False}

    async def calculate_learning_curve_metrics(self) -> Dict:
        """Метрики прогресса обучения."""
        # Упрощенная версия
        await self.db.init_db()
        new_labeled_count = await self.db.get_new_labeled_count_since_last_train()
        return {
            "total_labeled": new_labeled_count,
            "weekly_labeled": new_labeled_count, # Упрощение
            "informativeness_avg": 0.5 # Заглушка
        }

active_learner = ActiveLearningPipeline()
