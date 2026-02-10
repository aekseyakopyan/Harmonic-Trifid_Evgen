#!/usr/bin/env python3
"""
Migration script для вычисления embeddings для existing leads.
Запускается один раз после внедрения semantic deduplication.
"""

import sys
import asyncio
import os
from datetime import datetime, timedelta

# Добавляем корень проекта в пути импорта
sys.path.insert(0, os.getcwd())

from systems.parser.duplicate_detector import get_duplicate_detector
from systems.parser.vacancy_db import VacancyDatabase
from core.utils.structured_logger import get_logger

logger = get_logger(__name__)


async def migrate_embeddings():
    """
    Вычислить и сохранить embeddings для всех leads без embeddings.
    """
    print("=== Embedding Migration Script ===\n")
    
    # Initialize
    db = VacancyDatabase()
    detector = get_duplicate_detector(db_manager=db)
    
    if not detector.semantic_enabled:
        print("❌ Semantic deduplication не доступна")
        print("   Проверьте установку sentence-transformers")
        return
    
    print("✅ Semantic deduplication инициализирована")
    print(f"   Model: cointegrated/rubert-tiny")
    print(f"   Semantic threshold: {detector.semantic_threshold}")
    print()
    
    # Получить все leads без embeddings
    print("1. Загружаю leads без embeddings...")
    
    # Пытаемся получить leads без embeddings напрямую
    leads_without_embeddings = await asyncio.to_thread(db.get_leads_without_embeddings, 10000)
    
    total_count = len(leads_without_embeddings)
    print(f"✅ Найдено {total_count} leads без embeddings")
    
    if total_count == 0:
        print("\n✅ Миграция не требуется")
        return
    
    # Batch processing
    print(f"\n2. Вычисление embeddings (batch size: 32)...")
    
    processed = await detector.precompute_embeddings_batch(
        leads=leads_without_embeddings,
        batch_size=32
    )
    
    print(f"\n✅ Миграция завершена")
    print(f"   Обработано: {processed}/{total_count}")
    if total_count > 0:
        print(f"   Success rate: {processed/total_count*100:.1f}%")
    
    # Статистика
    stats = detector.get_statistics()
    print(f"\n📊 Статистика детектора:")
    print(f"   Cache size: {stats['cache_size']}/{stats['cache_max_size']}")
    print(f"   Time window: {stats['time_window_hours']}h")


if __name__ == "__main__":
    try:
        asyncio.run(migrate_embeddings())
    except KeyboardInterrupt:
        print("\n\n❌ Миграция прервана пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
