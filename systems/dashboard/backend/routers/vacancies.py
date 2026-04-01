from fastapi import APIRouter, Query
from core.config import VACANCIES_DB_PATH
from typing import Optional
import aiosqlite

router = APIRouter()


@router.get("/")
async def list_vacancies(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
):
    where_clauses = []
    params = []

    if status and status != "all":
        where_clauses.append("status = ?")
        params.append(status)
    if direction:
        where_clauses.append("direction LIKE ?")
        params.append(f"%{direction}%")
    if search:
        where_clauses.append("(text LIKE ? OR source LIKE ? OR contact_link LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    async with aiosqlite.connect(VACANCIES_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        count_row = await db.execute_fetchall(
            f"SELECT COUNT(*) as c FROM vacancies {where_sql}", params
        )
        total = count_row[0]["c"]

        rows = await db.execute_fetchall(
            f"""
            SELECT id, hash, status, text, source, direction,
                   contact_link, response, rejection_reason,
                   score, draft_response,
                   first_seen, last_seen, created_at
            FROM vacancies {where_sql}
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, skip],
        )

    items = []
    for r in rows:
        d = dict(r)
        if d.get("text") and len(d["text"]) > 300:
            d["text"] = d["text"][:300] + "..."
        if d.get("draft_response") and len(d["draft_response"]) > 200:
            d["draft_response"] = d["draft_response"][:200] + "..."
        items.append(d)

    return {"total": total, "items": items}


@router.get("/stats")
async def vacancies_stats():
    async with aiosqlite.connect(VACANCIES_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        by_status = await db.execute_fetchall(
            "SELECT status, COUNT(*) as cnt FROM vacancies GROUP BY status ORDER BY cnt DESC"
        )
        by_direction = await db.execute_fetchall(
            """SELECT direction, COUNT(*) as cnt FROM vacancies
               WHERE status='accepted' GROUP BY direction ORDER BY cnt DESC LIMIT 10"""
        )
        today = await db.execute_fetchall(
            """SELECT COUNT(*) as cnt FROM vacancies
               WHERE date(last_seen) = date('now')"""
        )
    return {
        "by_status": [dict(r) for r in by_status],
        "by_direction": [dict(r) for r in by_direction],
        "today": today[0]["cnt"] if today else 0,
    }
