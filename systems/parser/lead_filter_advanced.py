
import re
import json
import asyncio
import ast
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse

from core.ai_engine.resilient_llm import resilient_llm_client
from systems.parser.duplicate_detector import DuplicateDetector
from systems.parser.entity_extractor import EntityExtractor, extract_entities_hybrid
from systems.parser.lead_scoring import calculate_lead_priority
from systems.parser.ml_classifier import ml_classifier
from systems.parser.bert_classifier import bert_classifier
from systems.parser.workflow import LeadWorkflow
from systems.parser.vacancy_db import VacancyDatabase
from core.utils.structured_logger import logger

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================

BLACKLIST_CONFIG = {
    # Спам-домены
    "domains": [
        "forms.gle",
        "docs.google.com/forms",
        "kwork.ru",
        "fl.ru",
        "freelance.ru",
    ],
    
    # Спам-боты и каналы
    "bots": [
        "@getclient_tg_bot",
        "vk.com/freelance_all",
    ],
    
    # Явные мошеннические паттерны
    "scam_patterns": [
        r"чистыми.*\$\d+.*в день",  # "чистыми от $200 в день"
        r"набор в.*команду.*eu",     # пирамиды EU
        r"стабильные.*\d+.*день",    # "стабильные 5000₽ в день"
        r"легкий заработок",
        r"без вложений.*\d+.*рублей",
        r"пассивный доход от",
    ],
    
    # Ключевые слова мошенничества
    "scam_keywords": [
        "воркер", "воркеров", "дропы", "обнал", 
        "кардинг", "прогрев аккаунтов", "регистрация аккаунтов",
        "европа бан", "anti-detect", "antidetect"
    ],
    
    # Нерелевантные ниши (жёсткие)
    "irrelevant_hard": [
        "натяжные потолки",
        "ремонт квартир",
        "грузоперевозки",
        "юридические услуги",
        "бухгалтерия",
        "1с программист",
    ],
}

SCORING_CONFIG = {
    # CLIENT markers (заказчик) — ПОЛОЖИТЕЛЬНЫЕ баллы
    "client_strong": {  # +3 балла каждый
        "patterns": [
            r"\bнужен\b",
            r"\bтребуется\b",
            r"\bищу\s+(?:спец|специалист|исполнител)",
            r"\bкто\s+(?:сделает|поможет|настроит)",
            r"\bесть\s+задач",
            r"\bзаказ\b",
        ],
        "weight": 3
    },
    
    "client_medium": {  # +2 балла
        "keywords": [
            "подскажите", "посоветуйте", "помогите разобраться",
            "нужна помощь", "консультация", "аудит"
        ],
        "weight": 2
    },
    
    "client_weak": {  # +1 балл
        "keywords": [
            "бюджет", "сроки", "стоимость работы", "оплата по результату"
        ],
        "weight": 1
    },
    
    # SELLER markers (исполнитель) — ОТРИЦАТЕЛЬНЫЕ баллы
    "seller_strong": {  # -4 балла
        "patterns": [
            r"#помогу\b",
            r"\bя\s+(?:специалист|таргетолог|сеошник|маркетолог)",
            r"\bпредлагаю\s+услуг",
            r"\bмое\s+портфолио",
            r"\bвозьму\s+на\s+ведение",
            r"\bготов\s+(?:работать|взяться|помочь)",
        ],
        "weight": -4
    },
    
    "seller_medium": {  # -3 балла
        "keywords": [
            "мой опыт", "мои кейсы", "работал с", "сертифицированный",
            "прошёл обучение", "меня зовут", "я — ", "настрою вам",
            "пишите в лс", "пишите мне", "свяжитесь со мной"
        ],
        "weight": -3
    },
    
    "seller_weak": {  # -2 балла
        "keywords": [
            "резюме", "опыт работы", "команда", "агентство",
            "наши услуги", "прайс", "тарифы"
        ],
        "weight": -2
    },
    
    # SPAM indicators — ОТРИЦАТЕЛЬНЫЕ
    "spam_strong": {  # -5 баллов
        "keywords": [
            "подпишитесь на канал", "переходи в бот", "больше проектов в боте",
            "узнать больше", "жми на кнопку", "регистрируйся",
            "обучающий курс", "бесплатный вебинар"
        ],
        "weight": -5
    },
    
    "spam_medium": {  # -3 балла
        "keywords": [
            "набор сотрудников", "требуются", "вакансия", "ищем в команду",
            "удаленная работа на постоянной основе"
        ],
        "weight": -3
    },
    
    # QUALITY indicators — ПОЛОЖИТЕЛЬНЫЕ
    "quality_indicators": {  # +2 балла
        "keywords": [
            "техническое задание", "тз", "бриф", "детали проекта",
            "скайп", "zoom", "созвон"
        ],
        "weight": 2
    },
}

SOURCE_RELIABILITY = {
    "high": [  # Надёжные источники (+1 балл)
        "Разработка и IT - Kwork фриланс заказы",
        "Таргет | Арбитраж | Вакансии",
    ],
    "medium": [],  # Нейтральные (0)
    "low": [  # Ненадёжные (-1 балл)
        "ЖВБ – Фриланс и отзывы за деньги",
        "ФРИЛАНС | ВАКАНСИИ INSTAGRAM",
    ],
    "blacklist": [  # Автоматический reject
        "VK Freelance All",
    ]
}

DIRECTION_RELEVANCE = {
    "core": [  # Основные ниши (+2 балла)
        "SEO",
        "контекстная реклама",
        "авито",
        "разработка сайтов",
    ],
    "secondary": [  # Второстепенные (+1 балл)
        "интернет-маркетинг",
        "веб-дизайн",
    ],
    "irrelevant": [  # Нерелевантные (-2 балла)
        "таргетированная реклама",  # если вы НЕ делаете таргет
        "Keyword Match",  # обычно мусор
    ]
}

# ==========================================
# УРОВЕНЬ 0: НОРМАЛИЗАЦИЯ
# ==========================================

def normalize_and_extract_features(text: str) -> Dict[str, Any]:
    """
    Нормализует текст и извлекает структурные признаки.
    """
    text_lower = text.lower()
    
    # 1. Извлекаем URL
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    domains = [urlparse(url).netloc for url in urls]
    
    # 2. Считаем эмодзи (часто в спаме много)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    emoji_count = len(emoji_pattern.findall(text))
    
    # 3. Хештеги
    hashtags = re.findall(r'#\w+', text_lower)
    
    # 4. Упоминания пользователей/ботов
    mentions = re.findall(r'@\w+', text)
    
    # 5. Длина текста
    text_clean = re.sub(r'[^\w\s]', '', text_lower)
    words = text_clean.split()
    word_count = len(words)
    
    # 6. Caps Lock ratio (спам часто в CAPS)
    caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if len(text) > 0 else 0
    
    # 7. Бюджетные упоминания
    budget_matches = re.findall(r'(\d+[\s]*(?:₽|руб|rub|\$|usd|евро|eur))', text_lower)
    has_budget = len(budget_matches) > 0
    
    # Извлекаем числа из бюджета
    budget_values = []
    for match in budget_matches:
        nums = re.findall(r'\d+', match)
        if nums:
            budget_values.append(int(nums[0]))
    
    avg_budget = sum(budget_values) / len(budget_values) if budget_values else 0
    
    return {
        "text_lower": text_lower,
        "text_clean": text_clean,
        "words": words,
        "word_count": word_count,
        "urls": urls,
        "domains": domains,
        "emoji_count": emoji_count,
        "emoji_density": emoji_count / word_count if word_count > 0 else 0,
        "hashtags": hashtags,
        "mentions": mentions,
        "caps_ratio": caps_ratio,
        "has_budget": has_budget,
        "budget_values": budget_values,
        "avg_budget": avg_budget,
    }

# ==========================================
# УРОВЕНЬ 1: ЖЁСТКИЕ БЛОКИРОВКИ
# ==========================================

def check_hard_blocks(text: str, features: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Проверяет жёсткие блокировки.
    Returns: (is_blocked, reason)
    """
    text_lower = features["text_lower"]
    
    # 1. Блокировка по доменам
    for domain in BLACKLIST_CONFIG["domains"]:
        if domain in text_lower:
            return (True, f"BLACKLIST_DOMAIN: {domain}")
    
    # 2. Блокировка по ботам
    for bot in BLACKLIST_CONFIG["bots"]:
        if bot in text_lower:
            return (True, f"BLACKLIST_BOT: {bot}")
    
    # 3. Мошеннические паттерны
    for pattern in BLACKLIST_CONFIG["scam_patterns"]:
        if re.search(pattern, text_lower):
            return (True, f"SCAM_PATTERN: {pattern}")
    
    # 4. Ключевые слова мошенничества
    for keyword in BLACKLIST_CONFIG["scam_keywords"]:
        if keyword in text_lower:
            return (True, f"SCAM_KEYWORD: {keyword}")
    
    # 5. Нерелевантные ниши
    for niche in BLACKLIST_CONFIG["irrelevant_hard"]:
        if niche in text_lower:
            return (True, f"IRRELEVANT_NICHE: {niche}")
    
    # 6. Слишком много эмодзи (spam indicator)
    if features["emoji_density"] > 0.3:  # больше 30% текста — эмодзи
        return (True, f"EMOJI_SPAM: density={features['emoji_density']:.2f}")
    
    # 7. Слишком короткий текст (меньше 5 слов)
    if features["word_count"] < 5:
        return (True, f"TOO_SHORT: {features['word_count']} words")
    
    return (False, "")

# ==========================================
# УРОВЕНЬ 2: ЭВРИСТИЧЕСКИЙ СКОРИНГ
# ==========================================

def calculate_heuristic_score(text: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Рассчитывает эвристический score.
    """
    text_lower = features["text_lower"]
    score = 0
    hits = []
    
    # Проверяем CLIENT markers
    for pattern in SCORING_CONFIG["client_strong"]["patterns"]:
        matches = re.findall(pattern, text_lower)
        if matches:
            weight = SCORING_CONFIG["client_strong"]["weight"]
            score += weight * len(matches)
            hits.append(f"+{weight}: {pattern}")
    
    for keyword in SCORING_CONFIG["client_medium"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["client_medium"]["weight"]
            score += weight
            hits.append(f"+{weight}: {keyword}")
    
    for keyword in SCORING_CONFIG["client_weak"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["client_weak"]["weight"]
            score += weight
            hits.append(f"+{weight}: {keyword}")
    
    # Проверяем SELLER markers
    for pattern in SCORING_CONFIG["seller_strong"]["patterns"]:
        matches = re.findall(pattern, text_lower)
        if matches:
            weight = SCORING_CONFIG["seller_strong"]["weight"]
            score += weight * len(matches)
            hits.append(f"{weight}: {pattern}")
    
    for keyword in SCORING_CONFIG["seller_medium"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["seller_medium"]["weight"]
            score += weight
            hits.append(f"{weight}: {keyword}")
    
    for keyword in SCORING_CONFIG["seller_weak"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["seller_weak"]["weight"]
            score += weight
            hits.append(f"{weight}: {keyword}")
    
    # SPAM markers
    for keyword in SCORING_CONFIG["spam_strong"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["spam_strong"]["weight"]
            score += weight
            hits.append(f"{weight}: SPAM - {keyword}")
    
    for keyword in SCORING_CONFIG["spam_medium"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["spam_medium"]["weight"]
            score += weight
            hits.append(f"{weight}: SPAM_MED - {keyword}")
    
    # QUALITY indicators
    for keyword in SCORING_CONFIG["quality_indicators"]["keywords"]:
        if keyword in text_lower:
            weight = SCORING_CONFIG["quality_indicators"]["weight"]
            score += weight
            hits.append(f"+{weight}: QUALITY - {keyword}")
    
    # Дополнительные модификаторы
    # Если есть бюджет больше 5000₽ → +1
    if features["avg_budget"] > 5000:
        score += 1
        hits.append(f"+1: BUDGET > 5000₽ ({features['avg_budget']})")
    
    # Если бюджет меньше 1000₽ → -2 (копеечные задания)
    if 0 < features["avg_budget"] < 1000:
        score -= 2
        hits.append(f"-2: LOW_BUDGET < 1000₽ ({features['avg_budget']})")
    
    return {
        "score": score,
        "hits": hits,
    }

# ==========================================
# УРОВЕНЬ 3: КОНТЕКСТНАЯ ВАЛИДАЦИЯ
# ==========================================

def apply_context_validation(score: int, source: str, direction: str, features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Применяет контекстную валидацию.
    """
    context_score = score
    context_hits = []
    
    # 1. Проверка источника
    if source in SOURCE_RELIABILITY["blacklist"]:
        return {
            "is_blocked": True,
            "reason": f"BLACKLIST_SOURCE: {source}",
            "final_score": -999,
            "context_hits": [],
        }
    
    if source in SOURCE_RELIABILITY["high"]:
        context_score += 1
        context_hits.append(f"+1: HIGH_TRUST_SOURCE")
    elif source in SOURCE_RELIABILITY["low"]:
        context_score -= 1
        context_hits.append(f"-1: LOW_TRUST_SOURCE")
    
    # 2. Проверка направления
    if direction in DIRECTION_RELEVANCE["core"]:
        context_score += 2
        context_hits.append(f"+2: CORE_NICHE ({direction})")
    elif direction in DIRECTION_RELEVANCE["secondary"]:
        context_score += 1
        context_hits.append(f"+1: SECONDARY_NICHE ({direction})")
    elif direction in DIRECTION_RELEVANCE["irrelevant"]:
        context_score -= 2
        context_hits.append(f"-2: IRRELEVANT_NICHE ({direction})")
    
    return {
        "is_blocked": False,
        "final_score": context_score,
        "context_hits": context_hits,
    }

# ==========================================
# УРОВЕНЬ 4: LLM ANALYSIS
# ==========================================

async def llm_deep_analysis(text: str, features: Dict[str, Any], score: int) -> Dict[str, Any]:
    """
    Глубокий анализ через LLM для пограничных случаев.
    """
    prompt = f"""
Проанализируй сообщение из Telegram-чата фрилансеров.

КОНТЕКСТ:
- Эвристический score: {score}
- Длина: {features['word_count']} слов
- Бюджет: {features['avg_budget']}₽ (если указан)

КРИТЕРИИ ДЛЯ is_real_lead = true:
1. Это ЗАПРОС ОТ ЗАКАЗЧИКА (ищет исполнителя)
2. Ниша: SEO, Яндекс.Директ, Авито, создание сайтов
3. Есть описание задачи или вопрос
4. НЕТ признаков: предложения услуг, резюме, портфолио

КРИТЕРИИ ДЛЯ is_real_lead = false:
- Это ИСПОЛНИТЕЛЬ (предлагает услуги, резюме, "я специалист")
- Мошенничество ("заработок от $X в день", пирамиды)
- Копеечные задания (отзывы, лайки, подписки)
- Вакансия в штат ("ищем в команду", "набор сотрудников")
- Реклама курсов/обучения
- Нерелевантная ниша (маркетплейсы, соцсети, натяжные потолки)

ТЕКСТ СООБЩЕНИЯ:
---
{text[:800]}
---

Ответь СТРОГО в JSON:
{{
  "is_real_lead": true/false,
  "role": "CLIENT" / "FREELANCER" / "SPAM" / "RECRUITER",
  "confidence": 0.0-1.0,
  "reason": "краткое объяснение на русском (1 предложение)",
  "red_flags": ["список тревожных признаков, если есть"]
}}
    """.strip()
    
    system_prompt = "Ты — экспертный фильтр лидов для digital-маркетинга. Отвечай только валидным JSON."
    
    # Используем ResilientLLMClient с автоматическим fallback и защитой
    return await resilient_llm_client.call_with_fallback(
        prompt=prompt,
        text=text,
        timeout=10
    )
        
    except Exception as e:
        return {
            "is_real_lead": False,
            "role": "ERROR",
            "confidence": 0.0,
            "reason": f"LLM error: {str(e)}",
            "red_flags": []
        }

# ==========================================
# MAIN PIPELINE
# ==========================================

async def filter_lead_advanced(
    text: str,
    source: str,
    direction: str,
    message_id: int = 0,
    use_llm_for_uncertain: bool = True,
    use_deduplication: bool = True
) -> Dict[str, Any]:
    """
    Полный пайплайн фильтрации лида с дедупликацией, ML и скорингом.
    """
    details = {}
    
    # 1. Шаг: Дедупликация
    if use_deduplication:
        # Initialize detector with DB manager (singleton handles reuse)
        db = VacancyDatabase()
        detector = DuplicateDetector(db_manager=db)
        
        is_dup, similarity, method = await detector.is_duplicate(
            text=text, 
            message_id=message_id, 
            source_channel=source
        )
        
        if is_dup:
            return {
                "is_lead": False,
                "confidence": 0.95,
                "reason": f"DUPLICATE: {similarity:.2%} similar (method: {method})",
                "stage": "DEDUPLICATION",
                "details": {
                    "similarity": similarity,
                    "method": method
                }
            }
    
    # Уровень 0: Нормализация
    features = normalize_and_extract_features(text)
    details["features"] = features
    
    # Уровень 1: Жёсткие блокировки
    is_blocked, block_reason = check_hard_blocks(text, features)
    if is_blocked:
        return {
            "is_lead": False,
            "confidence": 0.99,
            "reason": block_reason,
            "stage": "LEVEL_1_HARD_BLOCK",
            "details": details
        }
    
    # Уровень 2: Эвристический скоринг
    heuristic = calculate_heuristic_score(text, features)
    score = heuristic["score"]
    details["heuristic"] = heuristic
    
    # Уровень 3: Контекстная валидация
    context = apply_context_validation(score, source, direction, features)
    details["context"] = context
    
    if context.get("is_blocked"):
        return {
            "is_lead": False,
            "confidence": 0.99,
            "reason": context.get("reason", "Context Block"),
            "stage": "LEVEL_3_CONTEXT_BLOCK",
            "details": details
        }
    
    final_score = context["final_score"]
    
    # Решение на основе скоринга и гибридного подхода
    decision_made = False
    is_lead = False
    confidence = 0.0
    stage = ""
    reason = ""
    
    if final_score >= 3:
        is_lead = True
        confidence = 0.85
        reason = f"HEURISTIC_ACCEPT: score={final_score}"
        stage = "LEVEL_2_HEURISTIC"
        decision_made = True
    elif final_score <= -2:
        is_lead = False
        confidence = 0.85
        reason = f"HEURISTIC_REJECT: score={final_score}"
        stage = "LEVEL_2_HEURISTIC"
        decision_made = True
    
    # Если решение не принято или уверенность низкая, используем BERT
    if not decision_made or confidence < 0.8:
        bert_result = bert_classifier.predict(text)
        details["bert"] = bert_result
        
        # Комбинируем результаты
        if not decision_made:
            is_lead = bert_result["is_lead"]
            confidence = bert_result["confidence"]
            reason = f"BERT_ONLY: {bert_result['method']}"
            stage = "LEVEL_BERT"
        else:
            # Гибрид (усредняем уверенность эвристики и BERT)
            confidence = (confidence + bert_result["confidence"]) / 2
            is_lead = bert_result["is_lead"] if confidence > 0.5 else is_lead
            reason = f"HYBRID: heuristic={final_score}, bert={bert_result['confidence']:.2f}"
            stage = "LEVEL_BERT_HYBRID"
        decision_made = True

    # Если всё еще не уверены, используем LLM
    if (not decision_made or (0.4 < confidence < 0.6)) and use_llm_for_uncertain:
        llm_result = await llm_deep_analysis(text, features, final_score)
        details["llm"] = llm_result
        is_lead = llm_result.get("is_real_lead", False)
        confidence = llm_result.get("confidence", 0.0)
        reason = f"LLM: {llm_result.get('reason', 'No reason')}"
        stage = "LEVEL_4_LLM"
    elif not decision_made:
        is_lead = False
        confidence = 0.6
        reason = f"UNCERTAIN_REJECT: score={final_score}"
        stage = "LEVEL_2_CONSERVATIVE"

    # Финальные штрихи для принятых лидов
    if is_lead:
        # Извлечение сущностей
        entities = extract_entities_hybrid(text)
        details["entities"] = entities
        
        # Расчет приоритета
        priority_data = calculate_lead_priority(
            text, source, direction, features, final_score, 
            SOURCE_RELIABILITY, DIRECTION_RELEVANCE
        )
        
        # Обогащаем приоритет данными из сущностей
        if entities["budget"]["min"] > 50000:
            priority_data["priority"] += 15
            priority_data["factors"].append("+15: NER_HIGH_BUDGET")
        if entities["deadline"]["urgency"] in ["urgent", "asap", "today"]:
            priority_data["priority"] += 20
            priority_data["factors"].append("+20: NER_URGENCY")
        if entities["contact"]["has_contact"]:
            priority_data["priority"] += 5
            priority_data["factors"].append("+5: NER_HAS_CONTACT")
            
        priority_data["priority"] = max(0, min(100, priority_data["priority"]))
        
        result = {
            "is_lead": True,
            "confidence": confidence,
            "reason": reason,
            "stage": stage,
            "priority": priority_data["priority"],
            "tier": priority_data["tier"],
            "priority_factors": priority_data["factors"],
            "entities": entities,
            "details": details
        }
    else:
    # Structured Logging
    log_data = {
        "event": "lead_classified",
        "is_lead": is_lead,
        "confidence": confidence,
        "reason": reason,
        "stage": stage,
        "source": source,
        "niche": direction,
        "decision_trail": [
            f"hard_blocks_pass" if not is_blocked else f"hard_blocked: {block_reason}",
            f"heuristic_score: {final_score}",
            f"bert_confidence: {details.get('bert', {}).get('confidence', 0):.2f}" if "bert" in details else "bert_skipped",
            f"stage: {stage}"
        ]
    }
    
    if is_lead:
        log_data.update({
            "tier": result.get("tier"),
            "priority": result.get("priority")
        })
    
    logger.info("lead_classification_complete", **log_data)
        
    return result


class LeadFilterAdvanced:
    """Wrapper class for lead filtering pipeline."""
    
    def __init__(self):
        self.detector = DuplicateDetector()
        self.extractor = EntityExtractor()
        
    async def analyze(self, text: str, message_id: int = None, chat_id: int = None, source: str = "unknown") -> Dict[str, Any]:
        """Async analysis of a lead."""
        # Note: We assume direction is core for now or detected elsewhere
        direction = "SEO" # Default
        
        result = await filter_lead_advanced(
            text=text,
            source=source,
            direction=direction,
            message_id=message_id or 0,
            use_llm_for_uncertain=True,
            use_deduplication=True
        )
        
        # Guard for missing keys from filter_lead_advanced
        if "tier" not in result:
            result["tier"] = "COLD" if not result.get("is_lead") else "WARM"
        if "priority" not in result:
            result["priority"] = 0
            
        return result
