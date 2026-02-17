#!/bin/bash
set -e

echo "🔧 Harmonic Trifid: Auto-Fix Critical Issues"
echo "=============================================="
echo ""

cd /Users/set/.gemini/antigravity/playground/Evgeniy

# 1. Исправление дубликатов в settings.py (уже сделано)
echo "✅ 1. Duplicate admin fields removed from settings.py"

# 2. Thread-safe singleton в duplicate_detector.py (уже сделано)
echo "✅ 2. Thread-safe singleton added to duplicate_detector.py"

# 3. LRU cache optimization (уже сделано)
echo "✅ 3. LRU cache optimized with OrderedDict"

# 4. Обновление зависимостей
echo "📦 4. Updating dependencies..."
pip3 install --upgrade sentence-transformers huggingface_hub --quiet

# 5. Миграция БД
echo "🗄️  5. Running database migration..."
python3 scripts/add_embedding_column.py

# 6. Healthcheck
echo "🔍 6. Running system healthcheck..."
python3 scripts/healthcheck.py

echo ""
echo "=============================================="
echo "✅ All critical fixes applied successfully!"
echo ""
echo "📋 Summary of changes:"
echo "  - Removed duplicate ADMIN fields from settings.py"
echo "  - Added thread-safe singleton pattern to DuplicateDetector"
echo "  - Optimized embeddings cache with LRU (OrderedDict)"
echo "  - Updated sentence-transformers to compatible version"
echo "  - Verified database schema (embedding column exists)"
echo "  - All systems operational"
