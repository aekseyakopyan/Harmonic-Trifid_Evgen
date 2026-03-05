from fastapi import APIRouter, HTTPException
from db.connection import get_db
from models.dialog import DialogOut, DialogPatch, ManualMessage
from core.ws_manager import manager
from typing import Optional

router = APIRouter()


@router.get("/")
async def list_dialogs(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    lead_id: Optional[int] = None,
):
    where_clauses = []
    params: list = []
    if status:
        where_clauses.append("d.status = ?")
        params.append(status)
    if lead_id:
        where_clauses.append("d.lead_id = ?")
        params.append(lead_id)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    async with get_db() as db:
        count_row = await db.execute_fetchall(
            f"SELECT COUNT(*) as cnt FROM dialogs d {where_sql}", params
        )
        total = count_row[0]["cnt"] if count_row else 0
        rows = await db.execute_fetchall(
            f"SELECT d.*, l.username, l.full_name FROM dialogs d LEFT JOIN leads l ON d.lead_id=l.id {where_sql} ORDER BY d.last_message_at DESC LIMIT ? OFFSET ?",
            params + [limit, skip],
        )
    return {"items": [dict(r) for r in rows], "total": total, "skip": skip, "limit": limit}


@router.get("/{dialog_id}")
async def get_dialog(dialog_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT d.*, l.username, l.full_name FROM dialogs d LEFT JOIN leads l ON d.lead_id=l.id WHERE d.id=?",
            [dialog_id],
        )
        if not rows:
            raise HTTPException(404, "Dialog not found")
        msgs = await db.execute_fetchall(
            "SELECT * FROM dialog_messages WHERE dialog_id=? ORDER BY sent_at",
            [dialog_id],
        )
    return {"dialog": dict(rows[0]), "messages": [dict(m) for m in msgs]}


@router.post("/{lead_id}/start")
async def start_dialog(lead_id: int, channel: str = "telegram", target_user: Optional[str] = None):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT id FROM leads WHERE id=?", [lead_id])
        if not rows:
            raise HTTPException(404, "Lead not found")
        cursor = await db.execute(
            "INSERT INTO dialogs(lead_id,channel,target_user,status,auto_mode,started_at) VALUES(?,?,?,'active',1,datetime('now'))",
            [lead_id, channel, target_user],
        )
        dialog_id = cursor.lastrowid
        await db.commit()
    await manager.broadcast("dialogs", {"event": "dialog_started", "id": dialog_id, "lead_id": lead_id})
    return {"id": dialog_id, "status": "active"}


@router.post("/{dialog_id}/stop")
async def stop_dialog(dialog_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT id FROM dialogs WHERE id=?", [dialog_id])
        if not rows:
            raise HTTPException(404, "Dialog not found")
        await db.execute(
            "UPDATE dialogs SET status='stopped', ended_at=datetime('now') WHERE id=?",
            [dialog_id],
        )
        await db.commit()
    await manager.broadcast("dialogs", {"event": "dialog_stopped", "id": dialog_id})
    return {"ok": True}


@router.patch("/{dialog_id}")
async def patch_dialog(dialog_id: int, patch: DialogPatch):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT id FROM dialogs WHERE id=?", [dialog_id])
        if not rows:
            raise HTTPException(404, "Dialog not found")
        updates = {k: v for k, v in patch.model_dump().items() if v is not None}
        if updates:
            set_sql = ", ".join(f"{k} = ?" for k in updates)
            await db.execute(
                f"UPDATE dialogs SET {set_sql} WHERE id=?",
                list(updates.values()) + [dialog_id],
            )
            await db.commit()
    return {"ok": True}


@router.post("/{dialog_id}/message")
async def send_manual_message(dialog_id: int, msg: ManualMessage):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT id FROM dialogs WHERE id=?", [dialog_id])
        if not rows:
            raise HTTPException(404, "Dialog not found")
        cursor = await db.execute(
            "INSERT INTO dialog_messages(dialog_id,role,content,sent_at,is_manual) VALUES(?,?,?,datetime('now'),1)",
            [dialog_id, msg.role, msg.content],
        )
        msg_id = cursor.lastrowid
        await db.execute(
            "UPDATE dialogs SET last_message_at=datetime('now') WHERE id=?",
            [dialog_id],
        )
        await db.commit()
    await manager.broadcast(
        "dialogs",
        {"event": "new_message", "dialog_id": dialog_id, "id": msg_id, "role": msg.role},
    )
    return {"id": msg_id}
