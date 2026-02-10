#!/bin/bash
# Скрипт для остановки Celery services

set -e

PROJECT_DIR="/Users/set/.gemini/antigravity/playground/Evgeniy"
cd "$PROJECT_DIR"

echo "=== Stopping Harmonic Trifid Celery Services ==="

# Stop Worker
if [ -f logs/celery_worker.pid ]; then
    echo "Stopping Celery Worker..."
    kill -TERM $(cat logs/celery_worker.pid) 2>/dev/null || true
    rm logs/celery_worker.pid
    echo "✅ Worker stopped"
fi

# Stop Beat
if [ -f logs/celery_beat.pid ]; then
    echo "Stopping Celery Beat..."
    kill -TERM $(cat logs/celery_beat.pid) 2>/dev/null || true
    rm logs/celery_beat.pid
    echo "✅ Beat stopped"
fi

# Stop Flower
if [ -f logs/flower.pid ]; then
    echo "Stopping Flower..."
    kill -TERM $(cat logs/flower.pid) 2>/dev/null || true
    rm logs/flower.pid
    echo "✅ Flower stopped"
fi

echo ""
echo "✅ All Celery services stopped"
