from pydantic import BaseModel
from typing import Optional


class PipelineConfigItem(BaseModel):
    key: str
    value: str
    updated_at: Optional[str]


class PipelineConfigPatch(BaseModel):
    value: str


class BlacklistEntry(BaseModel):
    type: str  # word | channel | niche
    value: str


class BlacklistBulk(BaseModel):
    type: str
    values: list[str]
