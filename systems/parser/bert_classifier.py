import torch
import time
from typing import Dict, Any
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from core.config.settings import settings
from core.utils.structured_logger import logger

class BERTLeadClassifier:
    """
    Классификатор лидов на базе BERT (ruBERT-tiny).
    """
    def __init__(self, model_name: str = "cointegrated/rubert-tiny"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def predict(self, text: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # Токенизация
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            truncation=True, 
            max_length=512, 
            padding=True
        ).to(self.device)
        
        # Инференс
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
            confidence = probabilities[0][1].item()
            
        inference_time = int((time.time() - start_time) * 1000)
        
        result = {
            "is_lead": confidence > 0.5,
            "confidence": confidence,
            "method": "bert",
            "inference_time_ms": inference_time
        }
        
        return result

# Singleton
bert_classifier = BERTLeadClassifier()
