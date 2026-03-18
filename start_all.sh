#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🚀 Запуск Harmonic Trifid (Full Stack)"
echo "======================================"

mkdir -p logs pids backups cache/llm logs/outreach

# Функция: запускает процесс только если не запущен (защита от дублей)
start_once() {
    local name="$1"
    local pidfile="pids/${name}.pid"
    shift

    if [ -f "$pidfile" ]; then
        local old_pid=$(cat "$pidfile")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "⚠️  $name уже запущен (PID $old_pid) — пропускаем"
            return 0
        fi
        rm -f "$pidfile"
    fi

    echo "▶  $name..."
    export PYTHONPATH=.
    nohup "$@" > "logs/${name}.log" 2>&1 &
    echo $! > "$pidfile"
    echo "   PID: $!"
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  МОДУЛЬ 1: КОММУНИКАЦИЯ С ЛЮДЬМИ + ОТКЛИКИ"
echo "  Pyrogram userbot — получает входящие,"
echo "  отвечает от лица Алексея, через GwenCommander"
echo "  отправляет первичные отклики на вакансии."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
start_once "alexey" ./venv/bin/python3 systems/alexey/main.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  МОДУЛЬ 2: ПАРСИНГ / ПОИСК ЛИДОВ"
echo "  Мониторит чаты → фильтрует вакансии"
echo "  → кладёт в vacancies.db для Module 1."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
start_once "parser" ./venv/bin/python3 main.py parse today

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ВСПОМОГАТЕЛЬНЫЕ СЕРВИСЫ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
start_once "gwen_bot" ./venv/bin/python3 systems/gwen/bot.py
start_once "miniapp"  ./venv/bin/python3 systems/miniapp/api.py

echo ""
echo "✅ Запуск завершён!"
echo ""
echo "Процессы:"
ps aux | grep -E "Harmonic-Trifid_Evgen.*(alexey|parser|gwen|miniapp)" | grep -v grep | awk '{print "  PID " $2 " | " $11 " " $12}'
echo ""
echo "Логи:"
echo "  tail -f logs/alexey.log    ← Диалоги + отклики (Module 1)"
echo "  tail -f logs/parser.log    ← Парсинг вакансий (Module 2)"
echo "  tail -f logs/gwen_bot.log  ← Supervisor бот"
