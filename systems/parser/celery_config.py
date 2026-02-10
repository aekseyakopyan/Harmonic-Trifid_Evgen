"""
Celery configuration для distributed task queue.
Обработка лидов через Redis broker с поддержкой priority queues и retry logic.
"""

from celery import Celery
from celery.schedules import crontab
import os

# Celery app instance
app = Celery(
    "harmonic_trifid",
    broker="redis://localhost:6379/0",      # Redis для broker
    backend="redis://localhost:6379/1"      # Redis для results
)

# Configuration
app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_expires=3600,  # Results хранятся 1 час
    
    # Timezone
    timezone="Europe/Moscow",
    enable_utc=False,
    
    # Priority queue support
    task_default_priority=5,  # Default priority (0-9, 9 = highest)
    task_acks_late=True,      # Acknowledge после выполнения
    task_reject_on_worker_lost=True,
    
    # Retry policy
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_retry_backoff=True,        # Exponential backoff
    task_retry_backoff_max=600,     # Max 10 минут между retries
    task_retry_jitter=True,         # Random jitter для избежания thundering herd
    
    # Performance
    worker_prefetch_multiplier=4,   # Prefetch 4 tasks per worker
    worker_max_tasks_per_child=1000,  # Restart worker после 1000 tasks
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Periodic tasks (через Celery Beat)
app.conf.beat_schedule = {
    # Cleanup старых лидов каждую ночь в 3:00
    "cleanup-old-leads": {
        "task": "systems.parser.tasks.cleanup_old_leads",
        "schedule": crontab(hour=3, minute=0),
    },
    
    # Мониторинг circuit breakers каждые 5 минут
    "monitor-circuit-breakers": {
        "task": "systems.parser.tasks.monitor_circuit_breakers",
        "schedule": crontab(minute="*/5"),
    },
    
    # Статистика по обработанным лидам каждый час
    "hourly-stats": {
        "task": "systems.parser.tasks.calculate_hourly_stats",
        "schedule": crontab(minute=0),
    },
}

# Task routes (можно направлять разные типы задач на разные queues)
app.conf.task_routes = {
    "systems.parser.tasks.process_lead_async": {"queue": "leads"},
    "systems.parser.tasks.send_notification": {"queue": "notifications"},
    "systems.parser.tasks.cleanup_old_leads": {"queue": "maintenance"},
}

print(f"[Celery] Initialized with broker: redis://localhost:6379/0")
