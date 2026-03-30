#!/bin/bash
set -e

echo "🔧 Исправление зависимостей Harmonic Trifid..."

cd /Users/set/.gemini/antigravity/playground/Evgeniy

echo "✅ Зависимости уже исправлены в requirements.txt!"
echo ""
echo "📋 Внесенные изменения:"
echo "  ❌ Удален несуществующий пакет: ub>=0.25.1"
echo "  ✅ Закреплены версии ML-библиотек:"
echo "     - torch==2.1.2"
echo "     - transformers==4.35.2"
echo "     - sentence-transformers==2.2.2"
echo "  ✅ Добавлены отсутствующие пакеты:"
echo "     - aiogram>=3.0.0 (Telegram Bot Framework)"
echo "     - openpyxl>=3.1.0 (Excel Export)"
echo "     - joblib>=1.3.0 (ML Model Persistence)"
echo "     - nltk>=3.8.0 (NLP Processing)"
echo "     - fuzzywuzzy>=0.18.0 (Fuzzy String Matching)"
echo "     - python-levenshtein>=0.21.0 (Levenshtein Distance)"
echo ""
echo "📦 Для установки обновленных зависимостей выполните:"
echo "pip install -r requirements.txt --upgrade"
