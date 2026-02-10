"""
BERT-based NER и semantic entity extraction.
Использует sentence embeddings для контекстного извлечения ниши проекта.
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from typing import Dict, List, Optional
from datetime import datetime

from systems.parser.text_normalizer import text_normalizer
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)


class BERTEntityExtractor:
    """
    Продвинутое извлечение сущностей через BERT embeddings и text normalization.
    
    Извлекает:
    1. Budget - с поддержкой текстовых числительных
    2. Deadline - с преобразованием в datetime
    3. Contacts - email, phone, telegram
    4. Niche - через semantic similarity с эталонами
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Sentence encoder для semantic similarity
        # Мы используем rubert-tiny для скорости и малого размера
        try:
            self.encoder = SentenceTransformer("cointegrated/rubert-tiny")
        except Exception as e:
            logger.error("Failed to load BERT model", error=str(e))
            self.encoder = None
        
        # Эталонные embeddings для ниш
        self.niche_templates = {
            "SEO": [
                "SEO продвижение оптимизация сайта поисковые системы Яндекс Google",
                "раскрутка сайта позиции топ выдачи органический трафик",
                "поисковая оптимизация внутренняя внешняя ссылки запросы",
            ],
            "Разработка сайтов": [
                "разработка сайта создание веб-ресурса frontend backend программирование",
                "лендинг интернет-магазин корпоративный сайт веб-дизайн верстка",
                "WordPress Tilda Битрикс CMS платформа конструктор",
            ],
            "Автоматизация Avito": [
                "автоматизация Авито магазин парсинг объявлений размещение выгрузка",
                "интеграция Avito API автопродление товары каталог синхронизация",
                "скрипт бот Авито авторазмещение мультиаккаунт",
            ],
            "Контекстная реклама": [
                "контекстная реклама Яндекс Директ Google Ads настройка кампания",
                "PPC таргетинг объявления ставки конверсия рекламный бюджет",
                "Яндекс Директ Google AdWords контекст настройка ведение",
            ],
            "SMM": [
                "SMM продвижение соцсети Instagram VK Telegram Facebook таргет",
                "контент-менеджер посты сторис реклама подписчики охваты",
                "социальные сети продвижение группа сообщество аудитория",
            ],
            "Аналитика": [
                "аналитика данных метрики Яндекс Метрика Google Analytics отчеты",
                "веб-аналитика статистика конверсии воронка цели события",
                "анализ трафика аудитория сегментация дашборд визуализация",
            ],
            "Дизайн": [
                "дизайн графический веб-дизайн UI UX интерфейс макет Figma",
                "логотип фирменный стиль баннер иллюстрация брендинг айдентика",
                "прототип wireframe моушн анимация видеомонтаж motion design",
            ],
            "Копирайтинг": [
                "копирайтинг тексты статьи описания контент рерайтинг seo-тексты",
                "написание текстов продающий текст коммерческое предложение landing",
                "контент-мейкер редактор статья блог карточка товара описание",
            ]
        }
        
        # Предвычисление embeddings для ниш
        self.niche_embeddings = {}
        if self.encoder:
            for niche, templates in self.niche_templates.items():
                embeddings = [self.encoder.encode(t) for t in templates]
                # Среднее embedding для ниши
                self.niche_embeddings[niche] = np.mean(embeddings, axis=0)
        
        self._initialized = True
        
        logger.info(
            "bert_ner_initialized",
            model="cointegrated/rubert-tiny",
            niches_count=len(self.niche_embeddings) if self.niche_embeddings else 0
        )
    
    def extract_budget_advanced(self, text: str) -> Dict:
        """
        Улучшенное извлечение бюджета с поддержкой текстовых числительных.
        
        Args:
            text: текст лида
            
        Returns:
            {
                "min": int|None,
                "max": int|None,
                "currency": str,
                "text": str,
                "confidence": float,
                "method": str
            }
        """
        # Поиск контекста с бюджетом
        budget_patterns = [
            r'бюджет[:\s]+([^.!?\n]+)',
            r'цена[:\s]+([^.!?\n]+)',
            r'стоимость[:\s]+([^.!?\n]+)',
            r'оплата[:\s]+([^.!?\n]+)',
        ]
        
        budget_context = None
        for pattern in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                budget_context = match.group(1)
                break
        
        if not budget_context:
            # Fallback: весь текст
            budget_context = text
        
        # Извлечение через text normalizer
        budget_range = text_normalizer.parse_budget_range(budget_context)
        
        # Определение валюты
        currency = "RUB"  # По умолчанию рубли
        if any(c in text.lower() for c in ["$", "usd", "dollar"]):
            currency = "USD"
        elif any(c in text.lower() for c in ["€", "eur", "euro"]):
            currency = "EUR"
        
        # Расчет confidence
        confidence = 0.0
        method = "text_normalization"
        
        if budget_range["min"] or budget_range["max"]:
            # Есть числа → высокий confidence
            if budget_range["min"] and budget_range["max"]:
                confidence = 0.9  # Диапазон → очень уверены
            else:
                confidence = 0.75  # Только одна граница
            
            # Проверка разумности значений
            values = [v for v in [budget_range["min"], budget_range["max"]] if v]
            if any(v < 100 or v > 10000000 for v in values):
                # Подозрительные значения
                confidence *= 0.7
        
        return {
            "min": budget_range["min"],
            "max": budget_range["max"],
            "currency": currency,
            "text": budget_context[:100],
            "confidence": confidence,
            "method": method
        }
    
    def extract_deadline_advanced(self, text: str) -> Dict:
        """
        Улучшенное извлечение дедлайна с преобразованием в datetime.
        
        Returns:
            {
                "urgency": str,  # "urgent"|"asap"|"today"|"specific_date"
                "date": datetime|None,
                "text": str,
                "confidence": float
            }
        """
        # Определение urgency level
        urgency = "normal"
        if any(word in text.lower() for word in ["срочно", "асап", "asap"]):
            urgency = "urgent"
        elif "сегодня" in text.lower():
            urgency = "today"
        
        # Извлечение даты
        deadline_date = text_normalizer.parse_deadline(text)
        
        # Извлечение текстового контекста
        deadline_patterns = [
            r'срок[и]?[:\s]+([^.!?\n]+)',
            r'дедлайн[:\s]+([^.!?\n]+)',
            r'(?:до|к)\s+([^.!?\n]+)',
        ]
        
        deadline_text = ""
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline_text = match.group(1)
                break
        
        # Confidence
        confidence = 0.0
        if deadline_date:
            if urgency in ["urgent", "asap", "today"]:
                confidence = 0.95
            else:
                confidence = 0.8
        elif urgency in ["urgent", "asap"]:
            confidence = 0.7  # Urgency без конкретной даты
        
        return {
            "urgency": urgency,
            "date": deadline_date,
            "text": deadline_text[:100],
            "confidence": confidence
        }
    
    def extract_contacts_advanced(self, text: str) -> Dict:
        """
        Извлечение контактов (email, phone, telegram).
        
        Returns:
            {
                "emails": list,
                "phones": list,
                "telegram": list,
                "has_contacts": bool
            }
        """
        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Phone (российские номера)
        phone_pattern = r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
        phones = re.findall(phone_pattern, text)
        
        # Telegram
        telegram_pattern = r'@[a-zA-Z0-9_]{5,}'
        telegram = re.findall(telegram_pattern, text)
        
        return {
            "emails": emails,
            "phones": phones,
            "telegram": telegram,
            "has_contacts": bool(emails or phones or telegram)
        }
    
    def extract_niche_semantic(self, text: str) -> Dict:
        """
        Контекстное извлечение ниши через semantic similarity.
        
        Returns:
            {
                "primary": str,
                "secondary": list,
                "confidence": float,
                "all_scores": dict
            }
        """
        if not self.encoder or not self.niche_embeddings:
            return {
                "primary": "unknown",
                "secondary": [],
                "confidence": 0.0,
                "all_scores": {}
            }
            
        # Кодировать текст лида
        text_embedding = self.encoder.encode(text)
        
        # Расчет similarity со всеми нишами
        similarities = {}
        for niche, niche_emb in self.niche_embeddings.items():
            sim = cosine_similarity(
                [text_embedding],
                [niche_emb]
            )[0][0]
            similarities[niche] = float(sim)
        
        # Сортировка по убыванию
        sorted_niches = sorted(
            similarities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        primary = sorted_niches[0][0]
        primary_score = sorted_niches[0][1]
        
        # Secondary niches (score > 0.5)
        secondary = [
            niche for niche, score in sorted_niches[1:]
            if score > 0.5
        ]
        
        return {
            "primary": primary,
            "secondary": secondary[:2],  # Топ-2 secondary
            "confidence": primary_score,
            "all_scores": similarities
        }
    
    def extract_all(self, text: str) -> Dict:
        """
        Извлечение всех сущностей из текста.
        
        Returns:
            {
                "budget": dict,
                "deadline": dict,
                "contacts": dict,
                "niche": dict,
                "extraction_time_ms": int
            }
        """
        import time
        start_time = time.time()
        
        budget = self.extract_budget_advanced(text)
        deadline = self.extract_deadline_advanced(text)
        contacts = self.extract_contacts_advanced(text)
        niche = self.extract_niche_semantic(text)
        
        extraction_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            "entities_extracted",
            has_budget=bool(budget["min"] or budget["max"]),
            has_deadline=bool(deadline["date"]),
            has_contacts=contacts["has_contacts"],
            primary_niche=niche.get("primary"),
            extraction_time_ms=extraction_time
        )
        
        return {
            "budget": budget,
            "deadline": deadline,
            "contacts": contacts,
            "niche": niche,
            "extraction_time_ms": extraction_time
        }


# Singleton instance
bert_ner = BERTEntityExtractor()
