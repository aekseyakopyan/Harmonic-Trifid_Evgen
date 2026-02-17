#!/bin/bash
set -e

cd /Users/set/.gemini/antigravity/playground/Evgeniy

echo "🚀 Запуск Harmonic Trifid"

# Создание необходимых директорий
mkdir -p logs pids backups cache/llm

# Запуск мониторинга в фоне
echo "📡 Запуск Parser Monitor..."
nohup python3 main.py monitor > logs/monitor.log 2>&1 &
echo $! > pids/monitor.pid

# Запуск Gwen
echo "🤖 Запуск Gwen Commander..."
nohup python3 systems/gwen/bot.py > logs/gwen.log 2>&1 &
echo $! > pids/gwen.pid

# Запуск Dashboard (если существует)
if [ -f "systems/dashboard/app.py" ]; then
    echo "📊 Запуск Dashboard..."
    nohup python3 systems/dashboard/app.py > logs/dashboard.log 2>&1 &
    echo $! > pids/dashboard.pid
fi

echo "✅ Все системы запущены!"
echo ""
echo "Проверка статуса:"
ps aux | grep -E "main.py|gwen|dashboard" | grep -v grep

echo ""
echo "Логи:"
echo "  tail -f logs/monitor.log"
echo "  tail -f logs/gwen.log"
echo ""
echo "Остановка: ./stop_all.sh"
