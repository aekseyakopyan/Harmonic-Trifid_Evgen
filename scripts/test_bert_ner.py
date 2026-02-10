#!/usr/bin/env python3
"""
Тестирование BERT NER для извлечения сущностей.
Проверяет hybrid extraction (BERT + fallback).
"""

import sys
import os

# Добавляем корень проекта в пути импорта
sys.path.insert(0, os.getcwd())

from systems.parser.bert_ner import bert_ner
from systems.parser.entity_extractor import extract_entities_hybrid
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)

def test_ner_extraction():
    print("=== Тестирование BERT NER ===\n")
    
    test_cases = [
        "Бюджет 50 000 руб, дедлайн завтра.",
        "Ищем Python разработчика, ставка до 200к. Стек: Django, DRF.",
        "Нужен сайт на Тильде. Бюджет 15000р. Срочно!",
        "Требуется дизайнер. Оплата по договоренности.",
        "Разработка мобильного приложения. Бюджет от 1 млн рублей. Контакт: @pm_manager"
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"--- Case {i} ---")
        print(f"Text: {text}")
        
        # 1. Direct BERT NER
        bert_res = bert_ner.extract_all(text)
        print(f"BERT raw: {bert_res}")
        
        # 2. Hybrid Extraction
        hybrid_res = extract_entities_hybrid(text)
        print(f"Hybrid result: {hybrid_res}")
        print(f"Method used: {hybrid_res.get('method')}")
        
        # Check budget extraction accuracy
        budget = hybrid_res.get('budget', {})
        print(f"Extracted Budget: {budget.get('min')} - {budget.get('max')} {budget.get('currency')}")
        print()

if __name__ == "__main__":
    test_ner_extraction()
