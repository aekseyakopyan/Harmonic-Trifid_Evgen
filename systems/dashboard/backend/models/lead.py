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


class LeadPatch(BaseModel):
    tier: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    niche: Optional[str] = None
    source_channel: Optional[str] = None


class LeadListResponse(BaseModel):
    items: list[LeadOut]
    total: int
    skip: int
    limit: int
