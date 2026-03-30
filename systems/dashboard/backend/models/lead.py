from pydantic import BaseModel
from typing import Optional
import json


class LeadOut(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    full_name: Optional[str]
    lead_score: float
    tier: Optional[str] = "COLD"
    priority: int = 0
    pipeline_stage: int = 0
    niche: Optional[str]
    source_channel: Optional[str]
    status: str = "new"
    is_archived: int = 0
    last_interaction: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    # Ручная оценка качества лида
    qual_score: Optional[int] = None   # 1-5: насколько лид целевой
    fit_score: Optional[int] = None    # 1-5: насколько нам подходит
    qual_notes: Optional[str] = None   # произвольные заметки


class LeadPatch(BaseModel):
    tier: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    niche: Optional[str] = None
    source_channel: Optional[str] = None
    qual_score: Optional[int] = None
    fit_score: Optional[int] = None
    qual_notes: Optional[str] = None


class LeadListResponse(BaseModel):
    items: list[LeadOut]
    total: int
    skip: int
    limit: int
