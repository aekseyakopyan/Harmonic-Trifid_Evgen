#!/bin/bash
# Скрипт для запуска Celery workers и Beat scheduler

set -e

PROJECT_DIR="/Users/set/.gemini/antigravity/playground/Evgeniy"
cd "$PROJECT_DIR"

echo "=== Starting Harmonic Trifid Celery Services ==="

# Проверка Redis
echo "Checking Redis connection..."
redis-cli ping > /dev/null 2>&1 || {
    echo "❌ Redis not running! Starting Redis via Docker..."
    docker run -d -p 6379:6379 --name harmonic-redis redis:7-alpine || docker start harmonic-redis
    sleep 2
}
echo "✅ Redis connected"

# Создание папки для логов
mkdir -p logs

# Запуск Celery Worker
echo "Starting Celery Worker..."
celery -A systems.parser.celery_config worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=leads,notifications,maintenance \
    --hostname=worker@%h \
    --logfile=logs/celery_worker.log \
    --pidfile=logs/celery_worker.pid \
    --detach

echo "✅ Celery Worker started (4 concurrent workers)"

# Запуск Celery Beat (scheduler для periodic tasks)
echo "Starting Celery Beat..."
celery -A systems.parser.celery_config beat \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --pidfile=logs/celery_beat.pid \
    --detach

echo "✅ Celery Beat started"

# Запуск Flower (monitoring dashboard)
echo "Starting Flower monitoring dashboard..."
celery -A systems.parser.celery_config flower \
    --port=5555 \
    --broker=redis://localhost:6379/0 \
    --logfile=logs/flower.log \
    --pidfile=logs/flower.pid \
    --detach

echo "✅ Flower dashboard started at http://localhost:5555"

# Статус проверка
sleep 2
echo ""
echo "=== Service Status ==="
celery -A systems.parser.celery_config inspect active || echo "Worker not yet active, check logs"

echo ""
echo "✅ All Celery services started successfully!"
