
from typing import Dict, List, Any

def calculate_lead_priority(
    text: str,
    source: str,
    direction: str,
    features: Dict[str, Any],
    heuristic_score: int,
    source_reliability: Dict[str, List[str]],
    direction_relevance: Dict[str, List[str]]
) -> Dict[str, Any]:
    """
    Рассчитывает приоритет лида (0-100).
    """
    priority = 50  # базовый
    factors = []
    
    # 1. Бюджет (чем выше — тем лучше)
    avg_budget = features.get("avg_budget", 0)
    if avg_budget > 50000:
        priority += 20
        factors.append("+20: BUDGET > 50k")
    elif avg_budget > 20000:
        priority += 15
        factors.append("+15: BUDGET > 20k")
    elif avg_budget > 10000:
        priority += 10
        factors.append("+10: BUDGET > 10k")
    elif avg_budget > 5000:
        priority += 5
        factors.append("+5: BUDGET > 5k")
    
    # 2. Срочность (ключевые слова)
    urgency_keywords = ["срочно", "быстро", "сегодня", "завтра", "asap"]
    text_lower = text.lower()
    if any(kw in text_lower for kw in urgency_keywords):
        priority += 10
        factors.append("+10: URGENT")
    
    # 3. Качество запроса (детали, ТЗ)
    quality_indicators = [
        "техническое задание", "тз", "бриф", "детали", 
        "скайп", "zoom", "созвон", "встреча"
    ]
    quality_count = sum(1 for kw in quality_indicators if kw in text_lower)
    if quality_count > 0:
        priority += quality_count * 5
        factors.append(f"+{quality_count * 5}: QUALITY_SIGNALS x{quality_count}")
    
    # 4. Надёжность источника
    if source in source_reliability.get("high", []):
        priority += 10
        factors.append("+10: TRUSTED_SOURCE")
    elif source in source_reliability.get("low", []):
        priority -= 10
        factors.append("-10: LOW_TRUST_SOURCE")
    
    # 5. Core ниша
    if direction in direction_relevance.get("core", []):
        priority += 15
        factors.append("+15: CORE_EXPERTISE")
    
    # 7. Эвристический score
    if heuristic_score >= 5:
        priority += 10
        factors.append("+10: HIGH_HEURISTIC_SCORE")
    
    # Ограничиваем диапазон 0-100
    priority = max(0, min(100, priority))
    
    return {
        "priority": priority,
        "factors": factors,
        "tier": "HOT" if priority >= 70 else "WARM" if priority >= 50 else "COLD"
    }
