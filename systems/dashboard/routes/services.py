from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.models import Service
from core.database.session import get_db
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_range: Optional[str] = None
    process: Optional[str] = None
    timeline: Optional[str] = None

@router.get("/")
async def get_services(db: AsyncSession = Depends(get_db)):
    """Get all services"""
    query = select(Service)
    result = await db.execute(query)
    services = result.scalars().all()
    
    return [{
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "price_range": service.price_range,
        "process": service.process,
        "timeline": service.timeline
    } for service in services]

@router.get("/{service_id}")
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific service"""
    query = select(Service).where(Service.id == service_id)
    result = await db.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "price_range": service.price_range,
        "process": service.process,
        "timeline": service.timeline
    }

@router.put("/{service_id}")
async def update_service(service_id: int, service_data: ServiceUpdate, db: AsyncSession = Depends(get_db)):
    """Update service description and details"""
    query = select(Service).where(Service.id == service_id)
    result = await db.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    for key, value in service_data.dict(exclude_unset=True).items():
        setattr(service, key, value)
    
    await db.commit()
    return {"message": "Service updated successfully"}
