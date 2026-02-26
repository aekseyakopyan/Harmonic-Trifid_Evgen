from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from core.config.settings import settings
from core.database.connection import async_session
from core.database.models import Lead, MessageLog
from sqlalchemy import select, func
import asyncio
from pathlib import Path

router = APIRouter()

class ParserToggleRequest(BaseModel):
    enabled: bool

class VacancyItem(BaseModel):
    id: int
    specialization: str
    source_chat: str
    found_at: datetime
    status: str
    relevance_score: Optional[int] = None

@router.get("/status")
async def get_parser_status():
    """Get current parser status and statistics"""
    try:
        # Читаем текущие настройки
        enabled = settings.OUTREACH_ENABLED
        test_mode = settings.OUTREACH_TEST_MODE
        
        # Получаем статистику за сегодня
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with async_session() as session:
            # Считаем найденные вакансии (входящие сообщения с intent=vacancy)
            vacancies_stmt = select(func.count(MessageLog.id)).where(
                MessageLog.created_at >= today_start,
                MessageLog.direction == 'incoming'
            )
            vacancies_result = await session.execute(vacancies_stmt)
            vacancies_found = vacancies_result.scalar() or 0
            
            # Считаем отправленные отклики (исходящие с intent=outreach)
            responses_stmt = select(func.count(MessageLog.id)).where(
                MessageLog.created_at >= today_start,
                MessageLog.direction == 'outgoing',
                MessageLog.intent == 'outreach'
            )
            responses_result = await session.execute(responses_stmt)
            responses_sent = responses_result.scalar() or 0
            
            # Считаем ошибки
            errors_stmt = select(func.count(MessageLog.id)).where(
                MessageLog.created_at >= today_start,
                MessageLog.status == 'failed'
            )
            errors_result = await session.execute(errors_stmt)
            errors_count = errors_result.scalar() or 0

        # Считаем лиды в обработке (из vacancies.db через aiosqlite)
        import aiosqlite
        import traceback
        vacancies_needs_review = 0
        try:
            async with aiosqlite.connect(str(settings.VACANCY_DB_PATH)) as db_conn:
                async with db_conn.execute("SELECT COUNT(*) FROM vacancies WHERE needs_review = 1") as cursor:
                    row = await cursor.fetchone()
                    vacancies_needs_review = row[0] if row else 0
        except Exception as e:
            print(f"Error counting needs_review vacancies: {e}")
            traceback.print_exc()

        async with async_session() as session:
            # Последний запуск (последнее исходящее сообщение с outreach)
            last_run_stmt = select(MessageLog.created_at).where(
                MessageLog.intent == 'outreach',
                MessageLog.direction == 'outgoing'
            ).order_by(MessageLog.created_at.desc()).limit(1)
            last_run_result = await session.execute(last_run_stmt)
            last_run = last_run_result.scalar()
            
            # Последние вакансии
            recent_stmt = select(MessageLog).where(
                MessageLog.direction == 'incoming'
            ).order_by(MessageLog.created_at.desc()).limit(10)
            recent_result = await session.execute(recent_stmt)
            recent_messages = recent_result.scalars().all()
        
        # Определяем текущую активность и статус
        running = enabled and not test_mode
        if not enabled:
            status = "disabled"
            current_activity = "Парсер выключен"
        elif test_mode:
            status = "test"
            current_activity = f"Тестовый режим: чат {settings.OUTREACH_TEST_CHAT_ID or 'не указан'}"
        else:
            status = "active"
            current_activity = "Мониторинг активных чатов..."
        
        # Формируем последние вакансии
        recent_vacancies = []
        for msg in recent_messages[:10]:
            recent_vacancies.append({
                "id": msg.id,
                "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                "found_at": msg.created_at.isoformat(),
                "category": msg.category or "general",
                "intent": msg.intent or "unknown"
            })
        
        return {
            "enabled": enabled,
            "running": running,
            "status": status,
            "current_activity": current_activity,
            "test_mode": test_mode,
            "test_chat_id": settings.OUTREACH_TEST_CHAT_ID,
            "stats": {
                "vacancies_found_today": vacancies_found,
                "responses_sent_today": responses_sent,
                "vacancies_needs_review": vacancies_needs_review,
                "errors_today": errors_count,
                "last_run": last_run.isoformat() if last_run else None,
                "success_rate": round((responses_sent / vacancies_found * 100) if vacancies_found > 0 else 0, 1)
            },
            "recent_vacancies": recent_vacancies
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/toggle")
async def toggle_parser(data: ParserToggleRequest):
    """Toggle parser on/off (emergency kill switch)"""
    try:
        env_path = Path(settings.BASE_DIR) / ".env"
        
        # Читаем .env
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Обновляем OUTREACH_ENABLED
        new_lines = []
        updated = False
        for line in lines:
            if line.startswith("OUTREACH_ENABLED="):
                new_lines.append(f"OUTREACH_ENABLED={str(data.enabled).lower()}\n")
                updated = True
            else:
                new_lines.append(line)
        
        # Если не нашли, добавляем
        if not updated:
            new_lines.append(f"OUTREACH_ENABLED={str(data.enabled).lower()}\n")
        
        # Сохраняем
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        # Обновляем в памяти
        settings.OUTREACH_ENABLED = data.enabled
        
        return {
            "success": True,
            "enabled": data.enabled,
            "message": "Парсер включен" if data.enabled else "Парсер аварийно остановлен"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing")
async def get_processing_vacancies():
    """Get list of vacancies currently in review (Active Learning batch)"""
    import aiosqlite
    import traceback
    try:
        async with aiosqlite.connect(str(settings.VACANCY_DB_PATH)) as db_conn:
            db_conn.row_factory = aiosqlite.Row
            async with db_conn.execute(
                "SELECT id, text, source, direction, informativeness_score, last_seen "
                "FROM vacancies WHERE needs_review = 1 ORDER BY last_seen DESC LIMIT 50"
            ) as cursor:
                rows = await cursor.fetchall()
                
                return [{
                    "id": row["id"],
                    "content": row["text"][:150] + "..." if len(row["text"]) > 150 else row["text"],
                    "source": row["source"],
                    "direction": row["direction"] or "Unknown",
                    "found_at": row["last_seen"],
                    "informativeness": round(row["informativeness_score"] or 0, 3)
                } for row in rows]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{vacancy_id}")
async def approve_vacancy(vacancy_id: int):
    """Approve vacancy: set status='accepted', needs_review=0 (Active Learning positive label)"""
    import aiosqlite
    try:
        async with aiosqlite.connect(str(settings.VACANCY_DB_PATH)) as db:
            await db.execute(
                "UPDATE vacancies SET status='accepted', needs_review=0 WHERE id=?",
                (vacancy_id,)
            )
            await db.commit()
        return {"success": True, "action": "approved", "id": vacancy_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject/{vacancy_id}")
async def reject_vacancy(vacancy_id: int):
    """Reject vacancy: set status='rejected', needs_review=0 (Active Learning negative label)"""
    import aiosqlite
    try:
        async with aiosqlite.connect(str(settings.VACANCY_DB_PATH)) as db:
            await db.execute(
                "UPDATE vacancies SET status='rejected', needs_review=0 WHERE id=?",
                (vacancy_id,)
            )
            await db.commit()
        return {"success": True, "action": "rejected", "id": vacancy_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
