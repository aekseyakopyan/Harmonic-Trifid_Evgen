#!/bin/bash
set -e

# Автоопределение директории скрипта
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🚀 Запуск Harmonic Trifid (Full Stack)"

# Создание необходимых директорий
mkdir -p logs pids backups cache/llm logs/outreach

# 1. Alexey (Userbot)
echo "🤖 Запуск Alexey Userbot..."
export PYTHONPATH=. && nohup ./venv/bin/python3 systems/alexey/main.py > logs/alexey.log 2>&1 &
echo $! > pids/alexey.pid

# 2. Today Parser (Real-time monitoring)
echo "📡 Запуск Today Parser..."
export PYTHONPATH=. && nohup ./venv/bin/python3 main.py parse today > logs/parser.log 2>&1 &
echo $! > pids/parser.pid

# 3. Chat Joiner (Excel based)
echo "🤝 Запуск Chat Joiner..."
# Запускаем с аргументами, чтобы избежать interactive input
export PYTHONPATH=. && nohup ./venv/bin/python3 apps/chat_joiner.py --file assets/chat_lists/chats_1600.xlsx --col Чаты > logs/chat_joiner.log 2>&1 &
echo $! > pids/chat_joiner.pid

# 4. Gwen Supervisor
echo "🛡️ Запуск Gwen Supervisor..."
export PYTHONPATH=. && nohup ./venv/bin/python3 systems/gwen/bot.py > logs/gwen.log 2>&1 &
echo $! > pids/gwen.pid

# 5. Mini App API
echo "📊 Запуск Mini App API..."
export PYTHONPATH=. && nohup ./venv/bin/python3 systems/miniapp/api.py > logs/miniapp.log 2>&1 &
echo $! > pids/miniapp.pid

echo "✅ Все 5 компонентов запущены в фоне!"
echo ""
echo "Проверка:"
ps aux | grep -E "python3|alexey|gwen|api.py|parser|joiner" | grep -v grep | grep Harmonic-Trifid
