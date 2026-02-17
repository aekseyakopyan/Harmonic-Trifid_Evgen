#!/bin/bash

cd /Users/set/.gemini/antigravity/playground/Evgeniy

echo "🛑 Остановка Harmonic Trifid"

for pidfile in pids/*.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        name=$(basename "$pidfile" .pid)
        
        if kill -0 $pid 2>/dev/null; then
            echo "Останавливаю $name (PID: $pid)..."
            kill $pid
            rm "$pidfile"
        else
            echo "$name уже не запущен"
            rm "$pidfile"
        fi
    fi
done

echo "✅ Все процессы остановлены"
