from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from db.connection import get_db
from models.lead import LeadOut, LeadPatch, LeadListResponse
from core.ws_manager import manager
from typing import Optional
import json
import csv
import io

router = APIRouter()


def row_to_lead(row) -> dict:
    d = dict(row)
    for f in ("last_interaction", "created_at", "updated_at"):
        if d.get(f):
            d[f] = str(d[f])
    return d


@router.get("/", response_model=LeadListResponse)
async def list_leads(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    is_archived: int = 0,
    niche: Optional[str] = None,
    sort: str = "last_interaction",
    order: str = "desc",
):
    allowed_sort = {"last_interaction", "lead_score", "priority", "created_at", "id"}
    if sort not in allowed_sort:
        sort = "last_interaction"
    order_sql = "DESC" if order.lower() == "desc" else "ASC"

    where_clauses = ["is_archived = ?"]
    params: list = [is_archived]

    if search:
        where_clauses.append("(COALESCE(full_name,'') LIKE ? OR COALESCE(username,'') LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if tier:
        where_clauses.append("tier = ?")
        params.append(tier)
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if niche:
        where_clauses.append("niche = ?")
        params.append(niche)

    where_sql = " AND ".join(where_clauses)

    async with get_db() as db:
        count_row = await db.execute_fetchall(
            f"SELECT COUNT(*) as cnt FROM leads WHERE {where_sql}", params
        )
        total = count_row[0]["cnt"] if count_row else 0

        rows = await db.execute_fetchall(
            f"SELECT * FROM leads WHERE {where_sql} ORDER BY {sort} {order_sql} LIMIT ? OFFSET ?",
            params + [limit, skip],
        )
    items = [row_to_lead(r) for r in rows]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{lead_id}")
async def get_lead(lead_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM leads WHERE id = ?", [lead_id])
    if not rows:
        raise HTTPException(404, "Lead not found")
    return row_to_lead(rows[0])


@router.patch("/{lead_id}")
async def patch_lead(lead_id: int, patch: LeadPatch):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM leads WHERE id = ?", [lead_id])
        if not rows:
            raise HTTPException(404, "Lead not found")
        old = dict(rows[0])

        updates = {k: v for k, v in patch.model_dump().items() if v is not None}
        if not updates:
            return old

        set_sql = ", ".join(f"{k} = ?" for k in updates)
        await db.execute(
            f"UPDATE leads SET {set_sql}, updated_at = datetime('now') WHERE id = ?",
            list(updates.values()) + [lead_id],
        )
        await db.execute(
            "INSERT INTO audit_log(action,entity_type,entity_id,old_value,new_value) VALUES(?,?,?,?,?)",
            ["patch", "lead", lead_id, json.dumps(old), json.dumps(updates)],
        )
        await db.commit()
        rows = await db.execute_fetchall("SELECT * FROM leads WHERE id = ?", [lead_id])
    await manager.broadcast("leads", {"event": "lead_updated", "id": lead_id})
    return row_to_lead(rows[0])


@router.post("/{lead_id}/reprocess")
async def reprocess_lead(lead_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT id FROM leads WHERE id = ?", [lead_id])
        if not rows:
            raise HTTPException(404, "Lead not found")
        await db.execute(
            "UPDATE leads SET pipeline_stage = 0, pipeline_log = '{}' WHERE id = ?",
            [lead_id],
        )
        await db.execute(
            "INSERT INTO audit_log(action,entity_type,entity_id) VALUES(?,?,?)",
            ["reprocess", "lead", lead_id],
        )
        await db.commit()
    await manager.broadcast("pipeline", {"event": "reprocess", "lead_id": lead_id})
    return {"ok": True}


@router.post("/{lead_id}/archive")
async def archive_lead(lead_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT id FROM leads WHERE id = ?", [lead_id])
        if not rows:
            raise HTTPException(404, "Lead not found")
        await db.execute(
            "UPDATE leads SET is_archived = 1, updated_at = datetime('now') WHERE id = ?",
            [lead_id],
        )
        await db.execute(
            "INSERT INTO audit_log(action,entity_type,entity_id) VALUES(?,?,?)",
            ["archive", "lead", lead_id],
        )
        await db.commit()
    await manager.broadcast("leads", {"event": "lead_archived", "id": lead_id})
    return {"ok": True}


@router.get("/{lead_id}/history")
async def lead_history(lead_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM audit_log WHERE entity_type='lead' AND entity_id=? ORDER BY ts DESC LIMIT 100",
            [lead_id],
        )
    return [dict(r) for r in rows]


@router.post("/export")
async def export_leads(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    is_archived: int = 0,
):
    where_clauses = ["is_archived = ?"]
    params: list = [is_archived]
    if tier:
        where_clauses.append("tier = ?")
        params.append(tier)
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(where_clauses)

    async with get_db() as db:
        rows = await db.execute_fetchall(
            f"SELECT id,telegram_id,username,full_name,lead_score,tier,priority,niche,source_channel,status,last_interaction,created_at FROM leads WHERE {where_sql} ORDER BY last_interaction DESC",
            params,
        )

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=dict(rows[0]).keys())
        writer.writeheader()
        for r in rows:
            writer.writerow(dict(r))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
