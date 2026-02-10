from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.models import Case
from core.database.session import get_db
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CaseCreate(BaseModel):
    title: str
    category: str
    description: str
    results: str
    image_url: Optional[str] = None
    project_url: Optional[str] = None
    is_active: bool = True

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    results: Optional[str] = None
    image_url: Optional[str] = None
    project_url: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/")
async def get_cases(
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get all cases with optional filtering"""
    query = select(Case)
    
    if active_only:
        query = query.where(Case.is_active == True)
    
    if category:
        query = query.where(Case.category.ilike(f"%{category}%"))
    
    result = await db.execute(query)
    cases = result.scalars().all()
    
    return [{
        "id": case.id,
        "title": case.title,
        "category": case.category,
        "description": case.description,
        "results": case.results,
        "image_url": case.image_url,
        "project_url": case.project_url,
        "is_active": case.is_active
    } for case in cases]

@router.post("/")
async def create_case(case_data: CaseCreate, db: AsyncSession = Depends(get_db)):
    """Create a new case"""
    new_case = Case(**case_data.dict())
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    return {"id": new_case.id, "message": "Case created successfully"}

@router.put("/{case_id}")
async def update_case(case_id: int, case_data: CaseUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing case"""
    query = select(Case).where(Case.id == case_id)
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    for key, value in case_data.dict(exclude_unset=True).items():
        setattr(case, key, value)
    
    await db.commit()
    return {"message": "Case updated successfully"}

@router.delete("/{case_id}")
async def delete_case(case_id: int, db: AsyncSession = Depends(get_db)):
    """Delete (deactivate) a case"""
    query = select(Case).where(Case.id == case_id)
    result = await db.execute(query)
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case.is_active = False
    await db.commit()
    return {"message": "Case deactivated successfully"}
