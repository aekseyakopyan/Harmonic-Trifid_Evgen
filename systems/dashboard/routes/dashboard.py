from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.models import Lead, MessageLog
from core.database.session import get_db
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()

@router.get("/metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    """Get dashboard metrics: total leads, active dialogues, conversion rate, trends"""
    
    # Base filters
    conditions = []
    if date_from:
        conditions.append(Lead.created_at >= date_from)
    if date_to:
        conditions.append(Lead.created_at <= date_to)
        
    # Total leads
    leads_query = select(func.count(Lead.id))
    if conditions:
        leads_query = leads_query.where(*conditions)
    total_leads = (await db.execute(leads_query)).scalar() or 0
    
    # Tier distribution
    hot_query = select(func.count(Lead.id)).where(Lead.tier == "HOT")
    warm_query = select(func.count(Lead.id)).where(Lead.tier == "WARM")
    if conditions:
        hot_query = hot_query.where(*conditions)
        warm_query = warm_query.where(*conditions)
        
    hot_leads = (await db.execute(hot_query)).scalar() or 0
    warm_leads = (await db.execute(warm_query)).scalar() or 0
    
    # Active dialogues (interacted in last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    active_query = select(func.count(Lead.id)).where(Lead.last_interaction >= yesterday)
    active_result = await db.execute(active_query)
    active_dialogues = active_result.scalar()
    
    # Total messages
    total_messages_query = select(func.count(MessageLog.id))
    total_messages_result = await db.execute(total_messages_query)
    total_messages = total_messages_result.scalar()
    
    # Meetings scheduled
    meetings_query = select(func.count(Lead.id)).where(Lead.meeting_scheduled == True)
    if conditions:
        meetings_query = meetings_query.where(*conditions)
    meetings_scheduled = (await db.execute(meetings_query)).scalar() or 0
    
    # Conversion rate
    conversion_rate = round((meetings_scheduled / total_leads * 100) if total_leads > 0 else 0, 2)
    
    # Trend calculation
    trend_data = await calculate_trend(db, date_from, date_to)
    
    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "warm_leads": warm_leads,
        "meetings_scheduled": meetings_scheduled,
        "active_dialogues": active_dialogues or 0,
        "total_messages": total_messages or 0,
        "conversion_rate": conversion_rate,
        "trend": trend_data
    }

async def calculate_trend(db: AsyncSession, date_from: Optional[datetime], date_to: Optional[datetime]):
    """Calculate trend compared to previous period"""
    if not date_from or not date_to:
        return {"direction": "stable", "percent": 0.0}
        
    period_length = (date_to - date_from).days or 1
    prev_from = date_from - timedelta(days=period_length)
    
    # Current period count
    curr_query = select(func.count(Lead.id)).where(Lead.created_at >= date_from, Lead.created_at <= date_to)
    curr_count = (await db.execute(curr_query)).scalar() or 0
    
    # Previous period count
    prev_query = select(func.count(Lead.id)).where(Lead.created_at >= prev_from, Lead.created_at < date_from)
    prev_count = (await db.execute(prev_query)).scalar() or 0
    
    if prev_count == 0:
        change = 100.0 if curr_count > 0 else 0.0
    else:
        change = ((curr_count - prev_count) / prev_count) * 100
        
    return {
        "direction": "up" if change > 0 else "down" if change < 0 else "stable",
        "percent": round(abs(change), 1)
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
