from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.models import Lead, MessageLog
from core.database.session import get_db
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_leads(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all leads with optional search"""
    query = select(Lead).order_by(desc(Lead.last_interaction))
    
    
    if search and search.strip():
        from sqlalchemy import or_, func
        query = query.where(
            or_(
                func.coalesce(Lead.full_name, '').ilike(f"%{search}%"),
                func.coalesce(Lead.username, '').ilike(f"%{search}%")
            )
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return [{
        "id": lead.id,
        "telegram_id": lead.telegram_id,
        "username": lead.username,
        "full_name": lead.full_name,
        "last_interaction": lead.last_interaction.isoformat() if lead.last_interaction else None,
        "lead_score": lead.lead_score
    } for lead in leads]

@router.get("/{lead_id}/history")
async def get_lead_history(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get message history for a specific lead"""
    # Check if lead exists
    lead_query = select(Lead).where(Lead.id == lead_id)
    lead_result = await db.execute(lead_query)
    lead = lead_result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get messages
    messages_query = (
        select(MessageLog)
        .where(MessageLog.lead_id == lead_id)
        .order_by(MessageLog.created_at)
    )
    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()
    
    return {
        "lead": {
            "id": lead.id,
            "username": lead.username,
            "full_name": lead.full_name,
        },
        "messages": [{
            "id": msg.id,
            "direction": msg.direction,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "intent": msg.intent,
            "category": msg.category
        } for msg in messages]
    }
