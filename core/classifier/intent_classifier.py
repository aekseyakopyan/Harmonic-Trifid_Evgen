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
        if any(w in text for w in [
            "сколько", "цена", "стоимость", "прайс", "тариф",
            "расценки", "прайслист", "ценник", "почем", "по чем",
            "коммерческое предложение", "стоит", "бюджет на",
        ]):
            intent = "pricing_inquiry"
        elif any(w in text for w in [
            "нужно", "нужен", "нужна", "сделать", "заказать", "хочу",
            "ищем", "ищу", "требуется", "помогите", "подключите",
            "возьметесь", "беретесь", "берете", "можете", "готовы",
            "сотрудничество", "проект", "задача", "интересует",
            "предложение", "рассмотрим", "рассматриваем",
        ]):
            intent = "service_request"
        elif any(w in text for w in [
            "привет", "здравствуйте", "добрый", "доброе утро",
            "добрый день", "добрый вечер", "приветствую", "хай",
            "hello", "hi", "доброго дня", "доброго времени",
        ]):
            intent = "greeting"

        # 2. Determine Category (используем русские названия для совместимости с DIRECTION_KEYWORDS и retriever)
        category = "маркетинг"
        if any(w in text for w in [
            "таргет вк", "реклама вк", "vk ads", "mytarget",
            "таргет одноклассники", "реклама вконтакте", "таргетолог вк",
            "таргетинг вк", "таргет в вк", "vk реклама", "реклама в вк",
            "продвижение вконтакте", "продвижение вк", "таргет mytarget",
            "реклама в одноклассниках", "ok.ru реклама",
            "настройка таргета вк", "ведение таргета вк",
            "вк таргетолог", "таргетированная реклама вк",
        ]):
            category = "таргет вк"
        elif any(w in text for w in [
            "seo", "сео", "продвижение", "поиск", "ранжирование", "органика",
            "поисковое продвижение", "продвижение в поиске",
            "позиции яндекс", "позиции google", "топ выдачи",
            "семантическое ядро", "семантика", "ссылочная масса",
            "технический аудит", "линкбилдинг", "seo оптимизация",
            "органический трафик", "трафик из поиска", "выход в топ",
            "первая страница поиска", "seo специалист", "seo аудит",
            "yandex seo", "google seo", "поисковый трафик",
        ]):
            category = "SEO"
        elif any(w in text for w in [
            "авито", "avito", "авито реклама", "авито про",
            "продвижение авито", "объявления авито", "авито xl",
            "авито магазин", "авито бизнес", "поднятие объявлений",
            "продвижение объявлений", "авито специалист",
        ]):
            category = "авито"
        elif any(w in text for w in [
            "сайт", "лендинг", "разработка", "веб", "магазин",
            "wordpress", "tilda", "тильда", "landing page",
            "корпоративный сайт", "интернет-магазин", "интернет магазин",
            "сайт визитка", "сайт под ключ", "верстка", "вёрстка",
            "веб разработка", "битрикс", "1с-битрикс", "opencart",
            "woocommerce", "react", "vue", "frontend", "backend",
            "редизайн", "создать сайт", "сделать сайт",
            "разработчик сайтов", "e-commerce", "электронный магазин",
        ]):
            category = "разработка сайтов"
        elif any(w in text for w in [
            "реклама", "директ", "контекст", "ppc", "google ads",
            "яндекс директ", "yandex direct", "настройка директ",
            "ведение директ", "контекстолог", "рся", "кмс",
            "ретаргетинг", "ремаркетинг", "реклама в яндексе",
            "реклама в google", "настройка рекламы", "ведение рекламы",
            "рекламная кампания", "cpc", "cpa",
            "performance маркетинг", "платный трафик", "платная реклама",
        ]):
            category = "контекстная реклама"

        # 3. Determine Tone (Sentiment)
        tone = "neutral"
        positive_words = [
            "спасибо", "круто", "отлично", "хорошо", "буду", "да", "верно",
            "ок", "интересно", "супер", "замечательно", "прекрасно",
            "согласен", "договорились", "понял", "окей", "конечно",
            "разумеется", "обсудим", "попробуем", "рассмотрим", "здорово",
            "именно", "точно", "правильно", "отличный вариант",
        ]
        negative_words = [
            "нет", "дорого", "плохо", "не", "ошибка", "долго", "сложно", "спам",
            "не нужно", "не интересует", "не интересно", "слишком дорого",
            "не могу", "не подходит", "не то", "разочарован",
            "не устраивает", "отказываемся", "передумал",
        ]
        hurry_words = [
            "срочно", "быстрее", "когда", "сейчас", "горит", "asap",
            "горящий", "нужно сегодня", "нужно завтра",
            "как можно быстрее", "в кратчайшие сроки", "дедлайн",
            "жмут сроки", "поджимают сроки", "немедленно", "срочная задача",
        ]

        if any(w in text for w in positive_words):
            tone = "positive"
        elif any(w in text for w in negative_words):
            tone = "negative"
        if any(w in text for w in hurry_words):
            tone += "_hurry"

        # 4. Simple Lead Scoring (1-10)
        score = 3.0
        if intent == "service_request": score += 3.0
        if category != "маркетинг": score += 2.0
        if any(w in text for w in [
            "бюджет", "срочно", "тз", "задание",
            "техническое задание", "бриф", "смета", "договор",
            "предоплата", "проект", "задача поставлена",
        ]): score += 2.0
        
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
