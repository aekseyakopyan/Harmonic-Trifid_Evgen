from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.models import Lead, MessageLog
from core.database.session import get_db
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/metrics")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    """Get dashboard metrics: total leads, active dialogues, conversion rate"""
    
    # Total leads
    leads_result = await db.execute(select(Lead))
    all_leads = leads_result.scalars().all()
    total_leads = len(all_leads)
    
    # Active dialogues (interacted in last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    active_query = select(func.count(Lead.id)).where(Lead.last_interaction >= yesterday)
    active_result = await db.execute(active_query)
    active_dialogues = active_result.scalar()
    
    # Total messages
    total_messages_query = select(func.count(MessageLog.id))
    total_messages_result = await db.execute(total_messages_query)
    total_messages = total_messages_result.scalar()
    
    # Messages today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages_query = select(func.count(MessageLog.id)).where(MessageLog.created_at >= today_start)
    today_messages_result = await db.execute(today_messages_query)
    messages_today = today_messages_result.scalar()
    
    return {
        "total_leads": total_leads or 0,
        "active_dialogues": active_dialogues or 0,
        "total_messages": total_messages or 0,
        "messages_today": messages_today or 0,
        "conversion_rate": 0  # TODO: calculate based on meeting_scheduled
    }

@router.get("/recent-activity")
async def get_recent_activity(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get recent message activity"""
    query = (
        select(MessageLog)
        .order_by(MessageLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return [{
        "id": msg.id,
        "lead_id": msg.lead_id,
        "direction": msg.direction,
        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None
    } for msg in messages]
