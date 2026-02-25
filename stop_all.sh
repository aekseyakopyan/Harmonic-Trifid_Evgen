#!/bin/bash
echo "🛑 Остановка всех процессов Harmonic Trifid..."

# Остановка по PID если файлы есть
if [ -d "pids" ]; then
    for pidfile in pids/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            echo "Убиваю процесс $pid ($pidfile)"
            kill -9 $pid 2>/dev/null || true
            rm "$pidfile"
        fi
    done
fi

# Жёсткий pkill по паттерну проекта для надёжности
pkill -9 -f "Harmonic-Trifid_Evgen" || true

echo "✅ Все процессы остановлены."
