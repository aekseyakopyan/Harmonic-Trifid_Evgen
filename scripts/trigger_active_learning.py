#!/usr/bin/env python3
"""
Manual trigger для Active Learning pipeline.
Используется для тестирования или ручного запуска.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

from systems.parser.active_learner import active_learner
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    print("=== Active Learning Pipeline Manual Trigger ===\n")
    
    # 1. Отбор информативных примеров
    print("1. Отбираю информативные примеры...")
    samples = active_learner.select_informative_samples()
    
    print(f"✅ Отобрано: {len(samples)} лидов")
    if samples:
        print(f"📊 Avg informativeness: {sum(s['informativeness'] for s in samples) / len(samples):.3f}")
        print(f"📈 Top-5 most informative:")
        for i, sample in enumerate(samples[:5], 1):
            print(f"   {i}. ID={sample['lead_id']}, score={sample['informativeness']:.3f}")
    
    print()
    
    # 2. Проверка условий для retraining
    print("2. Проверяю условия для переобучения...")
    retrain_result = active_learner.trigger_retrain()
    
    if retrain_result["retrain_triggered"]:
        print(f"✅ Переобучение запущено!")
        print(f"   Новых примеров: {retrain_result['new_labeled_count']}")
        if "metrics" in retrain_result:
            print(f"   Train accuracy: {retrain_result['metrics']['train_accuracy']:.3f}")
            print(f"   Val F1-score: {retrain_result['metrics']['val_f1']:.3f}")
    else:
        print(f"⏳ Переобучение не требуется")
        print(f"   Причина: {retrain_result['reason']}")
    
    print("\n✅ Pipeline completed")
