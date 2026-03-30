import os
import time
import torch
from typing import Dict, Any
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Путь к дообученной модели (создаётся scripts/finetune_bert.py)
FINETUNED_PATH = os.path.join(os.path.dirname(__file__), "bert_finetuned")
FALLBACK_MODEL  = "cointegrated/rubert-tiny2"
THRESHOLD       = 0.60


class BERTLeadClassifier:
    """
    Классификатор лидов на базе rubert-tiny2.
    Дообучен на квал-лидах (направление + задача + срочность).
    Использует MPS (Apple Silicon) если доступен.
    """

    def __init__(self):
        # Выбор устройства
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        # Загрузка дообученной модели или базовой
        if os.path.isdir(FINETUNED_PATH) and os.path.exists(os.path.join(FINETUNED_PATH, "config.json")):
            model_path = FINETUNED_PATH
            self._version = "BERT_FINETUNED_v1"
        else:
            model_path = FALLBACK_MODEL
            self._version = "BERT_BASE"

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, num_labels=2
        )
        self.model.to(self.device)
        self.model.eval()

    def predict(self, text: str) -> Dict[str, Any]:
        start = time.time()

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            confidence = float(probs[0][1].item())

        return {
            "is_lead":          confidence >= THRESHOLD,
            "confidence":       confidence,
            "method":           self._version,
            "inference_time_ms": int((time.time() - start) * 1000),
        }


# Singleton
bert_classifier = BERTLeadClassifier()
