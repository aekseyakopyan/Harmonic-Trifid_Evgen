#!/usr/bin/env python3
"""
Тестирование BERT NER на различных форматах текста.
"""

import sys
import os

# Добавляем корень проекта в пути импорта
sys.path.insert(0, os.getcwd())

from systems.parser.bert_ner import bert_ner
from systems.parser.text_normalizer import text_normalizer
import json

def test_text_normalization():
    """Тест нормализации текстовых числительных"""
    print("=== Тест 1: Text Normalization ===\n")
    
    test_cases = [
        ("пятьдесят тысяч рублей", 50000),
        ("сто двадцать пять тысяч", 125000),
        ("три с половиной миллиона", 3500000),
        ("50к", 50000),
        ("2.5 млн", 2500000),
        ("триста сорок", 340),
    ]
    
    for text, expected in test_cases:
        result = text_normalizer.text_to_number(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' → {result} (expected: {expected})")
    
    print()

def test_budget_extraction():
    """Тест извлечения бюджетов"""
    print("=== Тест 2: Budget Extraction ===\n")
    
    test_leads = [
        "Нужен SEO-специалист. Бюджет от 50 до 100 тысяч рублей.",
        "Разработка сайта. Стоимость до двухсот тысяч.",
        "Ищу маркетолога. Оплата примерно 75к в месяц.",
        "Продвижение магазина. Бюджет договорной, но не более 150 тыс.",
        "SEO аудит. Цена: пятьдесят тысяч ₽",
    ]
    
    for lead_text in test_leads:
        result = bert_ner.extract_budget_advanced(lead_text)
        
        print(f"Текст: {lead_text[:60]}...")
        print(f"  Min: {result['min']}")
        print(f"  Max: {result['max']}")
        print(f"  Currency: {result['currency']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print()

def test_deadline_extraction():
    """Тест извлечения дедлайнов"""
    print("=== Тест 3: Deadline Extraction ===\n")
    
    test_leads = [
        "Нужен срочно! ASAP!",
        "Запустить до конца недели.",
        "Сделать завтра или послезавтра.",
        "Срок: через две недели.",
        "До 25 числа текущего месяца.",
        "До конца месяца нужно закончить.",
    ]
    
    for lead_text in test_leads:
        result = bert_ner.extract_deadline_advanced(lead_text)
        
        print(f"Текст: {lead_text}")
        print(f"  Urgency: {result['urgency']}")
        print(f"  Date: {result['date']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print()

def test_niche_extraction():
    """Тест определения ниши"""
    print("=== Тест 4: Niche Classification ===\n")
    
    test_leads = [
        "Нужен SEO-специалист для продвижения сайта в Яндексе.",
        "Ищу frontend разработчика для создания лендинга на React.",
        "Требуется настроить автоматизацию Авито магазина с парсингом.",
        "Нужен таргетолог для запуска рекламы в Instagram и VK.",
        "Ищу аналитика данных для настройки Яндекс.Метрики.",
        "Разработка дизайна мобильного приложения в Figma.",
    ]
    
    for lead_text in test_leads:
        result = bert_ner.extract_niche_semantic(lead_text)
        
        print(f"Текст: {lead_text[:60]}...")
        print(f"  Primary: {result['primary']} (confidence: {result['confidence']:.3f})")
        if result['secondary']:
            print(f"  Secondary: {', '.join(result['secondary'])}")
        print()

def test_full_extraction():
    """Тест полного извлечения всех сущностей"""
    print("=== Тест 5: Full Entity Extraction ===\n")
    
    complex_lead = """
    Ищу SEO-специалиста для продвижения интернет-магазина косметики.
    
    Задачи:
    - Аудит сайта
    - Внутренняя и внешняя оптимизация
    - Сбор семантики
    - Написание SEO-текстов
    
    Бюджет: от пятидесяти до ста тысяч рублей в месяц.
    Срок: начать срочно, желательно завтра.
    Контакты: @test_username, email: test@example.com
    """
    
    result = bert_ner.extract_all(complex_lead)
    
    print("Результаты извлечения:\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    test_text_normalization()
    test_budget_extraction()
    test_deadline_extraction()
    test_niche_extraction()
    test_full_extraction()
    
    print("\n✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
