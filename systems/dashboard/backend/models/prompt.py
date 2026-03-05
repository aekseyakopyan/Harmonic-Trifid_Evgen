from pydantic import BaseModel
from typing import Optional


class PromptOut(BaseModel):
    id: int
    name: str
    stage: str
    content: str
    version: int
    is_active: int
    created_at: str


class PromptCreate(BaseModel):
    name: str
    stage: str
    content: str


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    stage: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[int] = None


class PromptVersionOut(BaseModel):
    id: int
    prompt_id: int
    version: int
    content: str
    created_at: str
