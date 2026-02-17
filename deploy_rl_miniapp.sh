#!/bin/bash
set -e

echo "🚀 Деплой RL + Mini App"
echo "========================"

cd /Users/set/.gemini/antigravity/playground/Evgeniy

# 1. Проверка миграции
echo "1️⃣ Проверка RL таблиц..."
python3 scripts/migrate_add_rl_tables.py

# 2. Установка зависимостей
echo "2️⃣ Установка зависимостей..."
pip3 install fastapi uvicorn --quiet

# 3. Запуск Mini App API
echo "3️⃣ Запуск Mini App API..."
nohup python3 systems/miniapp/api.py > logs/miniapp.log 2>&1 &
echo $! > pids/miniapp.pid

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "Mini App доступен на: http://localhost:8080"
echo "API docs: http://localhost:8080/docs"
echo ""
echo "Следующие шаги:"
echo "1. Настроить ngrok для публичного доступа:"
echo "   ngrok http 8080"
echo "2. Добавить URL в Telegram Bot (@BotFather → /newapp)"
echo "3. Протестировать: /app в боте Gwen"
echo ""
echo "Логи: tail -f logs/miniapp.log"
