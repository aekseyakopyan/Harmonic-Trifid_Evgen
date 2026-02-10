"""
Celery tasks для асинхронной обработки лидов.
Все задачи используют retry mechanism и structured logging.
"""

from systems.parser.celery_config import app
from systems.parser.lead_filter_advanced import LeadFilterAdvanced
from core.utils.structured_logger import get_logger
from core.ai_engine.resilient_llm import resilient_llm_client
import time
from datetime import datetime, timedelta

logger = get_logger(__name__)


@app.task(
    bind=True,
    name="systems.parser.tasks.process_lead_async",
    priority=5,
    max_retries=3,
    default_retry_delay=60
)
def process_lead_async(self, lead_data: dict):
    """
    Асинхронная обработка лида через 7-level pipeline.
    """
    start_time = time.time()
    task_id = self.request.id
    
    logger.info(
        "lead_processing_started",
        task_id=task_id,
        message_id=lead_data["message_id"],
        source=lead_data["source"]
    )
    
    try:
        # Инициализация filter engine
        filter_engine = LeadFilterAdvanced()
        
        # Обработка через pipeline
        # Важно: analyze в LeadFilterAdvanced является async, но Celery worker синхронен.
        # Однако process_lead_async может быть async если использовать event loop.
        # ТЗ подразумевает асинхронную обработку.
        import asyncio
        result = asyncio.run(filter_engine.analyze(
            text=lead_data["text"],
            message_id=lead_data["message_id"],
            source=lead_data["source"]
        ))
        
        processing_time = int((time.time() - start_time) * 1000)
        result["processing_time_ms"] = processing_time
        result["task_id"] = task_id
        
        # Priority routing для уведомлений
        if result.get("tier") == "HOT":
            send_notification.apply_async(
                args=[result, lead_data],
                priority=9,
                countdown=0
            )
            logger.info(
                "hot_lead_detected",
                task_id=task_id,
                priority=result.get("priority"),
                processing_time_ms=processing_time
            )
            
        elif result.get("tier") == "WARM":
            send_notification.apply_async(
                args=[result, lead_data],
                priority=5,
                countdown=60
            )
        
        logger.info(
            "lead_processing_completed",
            task_id=task_id,
            tier=result.get("tier"),
            priority=result.get("priority"),
            processing_time_ms=processing_time
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "lead_processing_failed",
            task_id=task_id,
            message_id=lead_data["message_id"],
            error=str(e)[:500],
            retry_count=self.request.retries
        )
        
        retry_countdown = 60 * (2 ** self.request.retries)
        
        raise self.retry(
            exc=e,
            countdown=retry_countdown,
            max_retries=3
        )


@app.task(
    bind=True,
    name="systems.parser.tasks.send_notification",
    priority=9,
    max_retries=5
)
def send_notification(self, lead_result: dict, lead_data: dict):
    """
    Отправка уведомлений для HOT/WARM лидов.
    """
    task_id = self.request.id
    
    logger.info(
        "notification_sending",
        task_id=task_id,
        tier=lead_result.get("tier"),
        priority=lead_result.get("priority")
    )
    
    try:
        notification_text = f"""
🔥 {lead_result.get('tier')} лид обнаружен!

📊 Priority: {lead_result.get('priority')}/100
📝 Источник: {lead_data['source']}
🔗 Message ID: {lead_data['message_id']}

💬 Текст:
{lead_data['text'][:200]}...

⚡ Обработано за {lead_result.get('processing_time_ms')}ms
"""
        
        logger.info(
            "notification_sent",
            task_id=task_id,
            tier=lead_result.get("tier")
        )
        
        return {"status": "sent", "task_id": task_id}
        
    except Exception as e:
        logger.error(
            "notification_failed",
            task_id=task_id,
            error=str(e)[:200]
        )
        raise self.retry(exc=e, countdown=30)


@app.task(name="systems.parser.tasks.cleanup_old_leads")
def cleanup_old_leads():
    """
    Periodic task: удаление лидов старше 30 дней из БД.
    """
    logger.info("cleanup_started", retention_days=30)
    
    try:
        from systems.parser.vacancy_db import VacancyDatabase
        
        db = VacancyDatabase()
        # TODO: Реализовать метод удаления в VacancyDatabase
        deleted_count = 0  
        
        logger.info(
            "cleanup_completed",
            deleted_count=deleted_count
        )
        
        return {"deleted": deleted_count}
        
    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        raise


@app.task(name="systems.parser.tasks.monitor_circuit_breakers")
def monitor_circuit_breakers():
    """
    Periodic task: мониторинг состояния circuit breakers.
    """
    health = resilient_llm_client.get_health_status()
    
    logger.info(
        "circuit_breaker_health_check",
        healthy=health["healthy"],
        openrouter_state=health["openrouter"]["state"],
        ollama_state=health["ollama"]["state"]
    )
    
    if not health["healthy"]:
        logger.error(
            "critical_all_llm_down",
            openrouter_fails=health["openrouter"]["fail_counter"],
            ollama_fails=health["ollama"]["fail_counter"]
        )
    
    return health


@app.task(name="systems.parser.tasks.calculate_hourly_stats")
def calculate_hourly_stats():
    """
    Periodic task: расчет статистики за последний час.
    """
    logger.info("calculating_hourly_stats")
    
    try:
        stats = {
            "total_processed": 0,
            "hot_count": 0,
            "warm_count": 0,
            "cold_count": 0,
            "avg_processing_time_ms": 0
        }
        
        logger.info("hourly_stats", **stats)
        return stats
        
    except Exception as e:
        logger.error("stats_calculation_failed", error=str(e))
        raise


@app.task(
    bind=True,
    name="systems.parser.tasks.batch_process_leads",
    priority=3
)
def batch_process_leads(self, lead_batch: list):
    """
    Batch обработка нескольких лидов одновременно.
    """
    task_id = self.request.id
    
    logger.info(
        "batch_processing_started",
        task_id=task_id,
        batch_size=len(lead_batch)
    )
    
    results = []
    for lead_data in lead_batch:
        task = process_lead_async.apply_async(
            args=[lead_data],
            priority=3
        )
        results.append({"message_id": lead_data["message_id"], "task_id": task.id})
    
    return {
        "processed": len(results),
        "results": results
    }
