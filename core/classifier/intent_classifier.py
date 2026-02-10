from typing import Dict, Any
from core.classifier.nlp_utils import clean_text
import re

class MessageClassifier:
    async def classify(self, message: str) -> Dict[str, Any]:
        """
        Classifies the message into intent, category, and lead score.
        For MVP, this uses regex and keyword matching.
        """
        text = clean_text(message)
        
        # 1. Determine Intent
        intent = "general_inquiry"
        if any(w in text for w in ["сколько", "цена", "стоимость", "прайс"]):
            intent = "pricing_inquiry"
        elif any(w in text for w in ["нужно", "сделать", "заказать", "хочу"]):
            intent = "service_request"
        elif any(w in text for w in ["привет", "здравствуйте", "добрый"]):
            intent = "greeting"

        # 2. Determine Category
        category = "general"
        if any(w in text for w in ["seo", "сео", "продвижение", "поиск"]):
            category = "SEO"
        elif any(w in text for w in ["сайт", "лендинг", "разработка", "веб", "магазин"]):
            category = "Development"
        elif any(w in text for w in ["реклама", "директ", "контекст", "таргет"]):
            category = "Ads"

        # 3. Determine Tone (Sentiment)
        tone = "neutral"
        positive_words = ["спасибо", "круто", "отлично", "хорошо", "буду", "да", "верно", "ок", "интересно"]
        negative_words = ["нет", "дорого", "плохо", "не", "ошибка", "долго", "сложно", "спам"]
        hurry_words = ["срочно", "быстрее", "когда", "сейчас", "горит"]
        
        if any(w in text for w in positive_words):
            tone = "positive"
        elif any(w in text for w in negative_words):
            tone = "negative"
        if any(w in text for w in hurry_words):
            tone += "_hurry"

        # 4. Simple Lead Scoring (1-10)
        score = 3.0
        if intent == "service_request": score += 3.0
        if category != "general": score += 2.0
        if any(w in text for w in ["бюджет", "срочно", "тз", "задание"]): score += 2.0
        
        return {
            "intent": intent,
            "category": category,
            "tone": tone,
            "lead_score": score,
            "entities": self._extract_entities(text)
        }

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extracts things like budget or site URLs."""
        entities = {}
        
        # Simple URL extraction
        urls = re.findall(r'(https?://[^\s]+)', text)
        if urls:
            entities["url"] = urls[0]
            
        # Simple budget extraction (regex for numbers followed by currency)
        budget = re.findall(r'(\d+)\s*(?:руб|р|usd|\$)', text)
        if budget:
            entities["budget"] = int(budget[0])
            
        return entities
