#!/bin/bash
echo "🛑 Остановка всех процессов Harmonic Trifid..."

# Graceful shutdown по PID: сначала SIGTERM, потом SIGKILL
if [ -d "pids" ]; then
    for pidfile in pids/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                echo "SIGTERM → PID $pid ($pidfile)"
                kill -15 "$pid" 2>/dev/null || true
            fi
            rm "$pidfile"
        fi
    done
    sleep 3  # Ждём graceful exit (SQLite WAL flush, Pyrogram session save)
fi

# Graceful pkill по паттерну проекта
pkill -15 -f "Harmonic-Trifid_Evgen" 2>/dev/null || true
sleep 3
# Добиваем тех, кто не вышел
pkill -9 -f "Harmonic-Trifid_Evgen" 2>/dev/null || true

echo "✅ Все процессы остановлены."
