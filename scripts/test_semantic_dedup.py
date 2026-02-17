#!/usr/bin/env python3
"""
Тестирование semantic deduplication на edge cases.
"""

import sys
import asyncio
import os

# Добавляем корень проекта в пути импорта
sys.path.insert(0, os.getcwd())

from systems.parser.duplicate_detector import get_duplicate_detector
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)


def test_semantic_similarity():
    """Тест semantic similarity calculation"""
    print("=== Тест 1: Semantic Similarity ===\n")
    
    # Инициализируем без DB для чистых unit тестов
    detector = get_duplicate_detector()
    
    if not detector.semantic_enabled:
        print("❌ Semantic deduplication не доступна")
        return
    
    test_pairs = [
        # Pair 1: Явные перефразировки (должны быть дублями)
        (
            "Ищу SEO-специалиста для продвижения сайта. Бюджет 50000₽.",
            "Нужен сеошник, чтобы вывести ресурс в топ. До 50к готов платить.",
            True  # Expected duplicate
        ),
        
        # Pair 2: Разные формулировки одной задачи
        (
            "Требуется разработка интернет-магазина на WordPress.",
            "Ищу веб-разработчика для создания сайта-магазина. CMS - ВордПресс.",
            True
        ),
        
        # Pair 3: Похожая тема, но разные задачи (НЕ дубли)
        (
            "Нужен SEO-специалист для продвижения интернет-магазина косметики.",
            "Ищу контекстолога для настройки Яндекс.Директ для косметики.",
            False
        ),
        
        # Pair 4: Точная копия (должен быть дубль)
        (
            "Разработка лендинга. Бюджет до 100 тысяч рублей.",
            "Разработка лендинга. Бюджет до 100 тысяч рублей.",
            True
        ),
        
        # Pair 5: Совершенно разные темы (НЕ дубли)
        (
            "Нужен SEO-специалист для продвижения сайта.",
            "Ищу дизайнера для создания логотипа.",
            False
        ),
    ]
    
    results = []
    
    for i, (text1, text2, expected_dup) in enumerate(test_pairs, 1):
        semantic_sim = detector.calculate_semantic_similarity(text1, text2)
        exact_sim = detector.calculate_exact_similarity(text1, text2)
        
        is_duplicate = semantic_sim > detector.semantic_threshold
        
        status = "✅" if is_duplicate == expected_dup else "❌"
        
        print(f"{status} Pair {i}:")
        print(f"   Text 1: {text1[:60]}...")
        print(f"   Text 2: {text2[:60]}...")
        print(f"   Semantic: {semantic_sim:.3f} (threshold: {detector.semantic_threshold})")
        print(f"   Exact: {exact_sim:.3f}")
        print(f"   Result: {'DUPLICATE' if is_duplicate else 'UNIQUE'}")
        print(f"   Expected: {'DUPLICATE' if expected_dup else 'UNIQUE'}")
        print()
        
        results.append(is_duplicate == expected_dup)
    
    accuracy = sum(results) / len(results) * 100
    print(f"Accuracy: {accuracy:.1f}% ({sum(results)}/{len(results)})")


def test_exact_vs_semantic():
    """Сравнение exact match vs semantic similarity"""
    print("\n=== Тест 2: Exact vs Semantic ===\n")
    
    detector = get_duplicate_detector()
    
    if not detector.semantic_enabled:
        print("❌ Semantic deduplication не доступна")
        return
    
    # Кейсы где semantic лучше exact match
    edge_cases = [
        (
            "Ищу SEO-специалиста для продвижения сайта клиники",
            "Нужен сеошник для раскрутки медицинского сайта"
        ),
        (
            "Требуется разработка корпоративного сайта на React",
            "Создание корпоративного веб-ресурса с использованием ReactJS"
        ),
        (
            "Настройка автоматизации Авито магазина",
            "Интеграция с Avito для автоматического размещения товаров"
        ),
    ]
    
    print("Кейсы где SEMANTIC > EXACT:\n")
    
    for i, (text1, text2) in enumerate(edge_cases, 1):
        semantic_sim = detector.calculate_semantic_similarity(text1, text2)
        exact_sim = detector.calculate_exact_similarity(text1, text2)
        
        improvement = semantic_sim - exact_sim
        status = "✅" if improvement > 0.2 else "⚠️"
        
        print(f"{status} Case {i}:")
        print(f"   Text 1: {text1}")
        print(f"   Text 2: {text2}")
        print(f"   Semantic: {semantic_sim:.3f}")
        print(f"   Exact: {exact_sim:.3f}")
        print(f"   Improvement: +{improvement:.3f}")
        print()


def test_threshold_tuning():
    """Тест различных threshold values"""
    print("\n=== Тест 3: Threshold Tuning ===\n")
    
    detector = get_duplicate_detector()
    
    if not detector.semantic_enabled:
        print("❌ Semantic deduplication не доступна")
        return
    
    # Набор примеров с разной степенью similarity
    test_cases = [
        ("Нужен SEO. Бюджет 50к.", "Ищу сеошника. До 50 тысяч.", "close_paraphrase"),
        ("Разработка сайта на React", "Создание веб-приложения ReactJS", "paraphrase"),
        ("SEO продвижение сайта", "Контекстная реклама Яндекс.Директ", "related_topic"),
        ("Нужен дизайнер", "Ищу программиста Python", "different_topic"),
    ]
    
    thresholds = [0.70, 0.75, 0.80, 0.85]
    
    print("Similarity scores и classifications:\n")
    
    for text1, text2, category in test_cases:
        sim = detector.calculate_semantic_similarity(text1, text2)
        
        print(f"Category: {category}")
        print(f"  Text 1: {text1}")
        print(f"  Text 2: {text2}")
        print(f"  Similarity: {sim:.3f}")
        print(f"  Classified as duplicate at thresholds:")
        
        for threshold in thresholds:
            is_dup = sim > threshold
            print(f"    {threshold}: {'✅ YES' if is_dup else '❌ NO'}")
        print()
    
    print(f"Рекомендуемый threshold: 0.75 (текущий: {detector.semantic_threshold})")


async def test_integration():
    """Тест интеграции с БД"""
    print("\n=== Тест 4: Database Integration ===\n")
    
    from systems.parser.vacancy_db import VacancyDatabase
    
    db = VacancyDatabase()
    await db.init_db()
    detector = get_duplicate_detector(db_manager=db)
    
    if not detector.semantic_enabled:
        print("❌ Semantic deduplication не доступна")
        return
    
    # Имитируем входящий лид
    test_lead = "Нужен SEO-специалист для продвижения сайта клиники. Бюджет до 100к."
    
    print("Проверка дубликата для:")
    print(f"  {test_lead}\n")
    
    is_dup, similarity, method = await detector.is_duplicate(
        text=test_lead,
        message_id=999999,
        source_channel="test_channel"
    )
    
    print(f"Результат:")
    print(f"  Is duplicate: {is_dup}")
    print(f"  Similarity: {similarity:.3f}")
    print(f"  Method: {method}")
    
    # Статистика
    stats = detector.get_statistics()
    print(f"\n📊 Detector stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    try:
        test_semantic_similarity()
        test_exact_vs_semantic()
        test_threshold_tuning()
        
        print("\n" + "="*50)
        asyncio.run(test_integration())
        
        print("\n✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
