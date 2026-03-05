from fastapi import APIRouter, HTTPException
from db.connection import get_db
from models.pipeline import PipelineConfigPatch, BlacklistBulk
from typing import Optional

router = APIRouter()


@router.get("/config")
async def get_config():
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM pipeline_config ORDER BY key")
    return [dict(r) for r in rows]


@router.patch("/config/{key}")
async def patch_config(key: str, patch: PipelineConfigPatch):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT key FROM pipeline_config WHERE key=?", [key])
        if not rows:
            raise HTTPException(404, f"Config key '{key}' not found")
        await db.execute(
            "UPDATE pipeline_config SET value=?, updated_at=datetime('now') WHERE key=?",
            [patch.value, key],
        )
        await db.commit()
    return {"key": key, "value": patch.value}


@router.get("/blacklist")
async def get_blacklist(type: Optional[str] = None):
    async with get_db() as db:
        if type:
            rows = await db.execute_fetchall(
                "SELECT * FROM pipeline_blacklist WHERE type=? ORDER BY added_at DESC", [type]
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM pipeline_blacklist ORDER BY type, added_at DESC"
            )
    return [dict(r) for r in rows]


@router.post("/blacklist/words")
async def add_blacklist(payload: BlacklistBulk):
    added = []
    async with get_db() as db:
        for v in payload.values:
            v = v.strip()
            if not v:
                continue
            try:
                await db.execute(
                    "INSERT INTO pipeline_blacklist(type,value) VALUES(?,?)",
                    [payload.type, v],
                )
                added.append(v)
            except Exception:
                pass
        await db.commit()
    return {"added": added}


@router.delete("/blacklist/words")
async def remove_blacklist(payload: BlacklistBulk):
    async with get_db() as db:
        for v in payload.values:
            await db.execute(
                "DELETE FROM pipeline_blacklist WHERE type=? AND value=?",
                [payload.type, v],
            )
        await db.commit()
    return {"removed": payload.values}


@router.get("/stats")
async def pipeline_stats():
    async with get_db() as db:
        total = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads"))[0]["c"]
        by_tier = await db.execute_fetchall(
            "SELECT COALESCE(tier,'COLD') as tier, COUNT(*) as cnt FROM leads GROUP BY tier"
        )
        by_stage = await db.execute_fetchall(
            "SELECT COALESCE(pipeline_stage,0) as stage, COUNT(*) as cnt FROM leads GROUP BY pipeline_stage"
        )
        archived = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE is_archived=1"
        ))[0]["c"]
    return {
        "total": total,
        "archived": archived,
        "by_tier": [dict(r) for r in by_tier],
        "by_stage": [dict(r) for r in by_stage],
    }
