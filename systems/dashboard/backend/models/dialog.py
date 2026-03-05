from pydantic import BaseModel
from typing import Optional


class DialogOut(BaseModel):
    id: int
    lead_id: int
    channel: str
    target_user: Optional[str]
    status: str
    auto_mode: int
    last_message_at: Optional[str]
    started_at: Optional[str]
    ended_at: Optional[str]
    result: Optional[str]
    notes: Optional[str]


class DialogMessageOut(BaseModel):
    id: int
    dialog_id: int
    role: str
    content: str
    sent_at: str
    is_manual: int


class DialogPatch(BaseModel):
    auto_mode: Optional[int] = None
    notes: Optional[str] = None
    result: Optional[str] = None


class ManualMessage(BaseModel):
    content: str
    role: str = "assistant"
