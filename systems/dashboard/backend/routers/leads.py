from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from db.connection import get_db
from models.lead import LeadOut, LeadPatch, LeadListResponse
from core.ws_manager import manager
from core.config import VACANCIES_DB_PATH
from typing import Optional
import json
import csv
import io
import aiosqlite
import os

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


@router.post("/bulk")
async def bulk_patch_leads(lead_ids: list[int], action: str, value: str = ""):
    """Массовое обновление лидов. action: set_tier, set_status, archive"""
    if not lead_ids:
        return {"updated": 0}
    placeholders = ",".join("?" * len(lead_ids))
    async with get_db() as db:
        if action == "set_tier" and value in ("HOT", "WARM", "COLD"):
            await db.execute(
                f"UPDATE leads SET tier=?, updated_at=datetime('now') WHERE id IN ({placeholders})",
                [value] + lead_ids,
            )
        elif action == "set_status" and value in ("new", "contacted", "qualified", "lost"):
            await db.execute(
                f"UPDATE leads SET status=?, updated_at=datetime('now') WHERE id IN ({placeholders})",
                [value] + lead_ids,
            )
        elif action == "archive":
            await db.execute(
                f"UPDATE leads SET is_archived=1, updated_at=datetime('now') WHERE id IN ({placeholders})",
                lead_ids,
            )
        await db.execute(
            "INSERT INTO audit_log(action,entity_type,entity_id,new_value) VALUES(?,?,?,?)",
            [f"bulk_{action}", "lead", 0, f"ids={lead_ids[:10]},value={value}"],
        )
        await db.commit()
    await manager.broadcast("leads", {"event": "bulk_updated", "ids": lead_ids})
    return {"updated": len(lead_ids)}


@router.get("/{lead_id}/vacancies")
async def lead_vacancies(lead_id: int):
    """Возвращает оригинальные тексты вакансий из vacancies.db для данного лида."""
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM leads WHERE id = ?", [lead_id])
    if not rows:
        raise HTTPException(404, "Lead not found")
    lead = dict(rows[0])
    username = lead.get("username")
    telegram_id = lead.get("telegram_id")

    if not os.path.exists(VACANCIES_DB_PATH):
        return []

    try:
        async with aiosqlite.connect(VACANCIES_DB_PATH) as vdb:
            vdb.row_factory = aiosqlite.Row
            results = []
            if telegram_id:
                rows2 = await (await vdb.execute(
                    "SELECT id, text, source_channel, created_at, status FROM vacancies WHERE sender_id=? ORDER BY created_at DESC LIMIT 10",
                    [str(telegram_id)]
                )).fetchall()
                results.extend([dict(r) for r in rows2])
            if username and not results:
                rows2 = await (await vdb.execute(
                    "SELECT id, text, source_channel, created_at, status FROM vacancies WHERE text LIKE ? ORDER BY created_at DESC LIMIT 5",
                    [f"%@{username}%"]
                )).fetchall()
                results.extend([dict(r) for r in rows2])
            return results
    except Exception as e:
        return []


_FILTER_EXPECTED_PATTERNS = [
    "вакансия здесь размещена", "вакансии здесь размещены", "vakansii", "freelance_rabota",
    "нужны авторы отзывов", "bitcoin", "binance", "usdt", "крипто", "трейдинг",
    "неизвестная команда", "доступные команды", "login code",
    "ищу дизайнера", "нужен дизайнер", "ищем дизайнера", "#дизайнер",
    "ищу копирайтера", "ищем копирайтера", "#копирайтер",
    "ищу smm", "ищем smm", "#smm", "ведение соцсетей",
    "ищу программиста", "ищем программиста", "нужен программист",
    "принимаю заказы", "я фрилансер", "я дизайнер", "я копирайтер", "я разработчик",
    "ищу сотрудника", "ищу менеджера", "нужен менеджер по продажам",
    "продам аккаунт", "продам базу", "куплю аккаунт",
]


def _gap_analysis(vacancy_text: str, username: str) -> list[str]:
    """Возвращает паттерны которые ДОЛЖНЫ были заблокировать этот лид."""
    combined = ((vacancy_text or "") + " " + (username or "")).lower()
    missed = [p for p in _FILTER_EXPECTED_PATTERNS if p in combined]
    return missed


def _analyze_spam_reason(username: str, vacancy_text: str) -> str:
    combined = ((vacancy_text or "") + " " + (username or "")).lower()
    patterns = [
        (["вакансия здесь размещена", "вакансии здесь размещены", "vakansii", "vakansii_rabota"], "Авто-бот биржи вакансий"),
        (["работодром", "vergiliyrd", "workdrom"], "Бот биржи труда"),
        (["freelance_rabota", "если вам нужен фриланс"], "Фриланс-биржа бот"),
        (["нужны авторы отзывов", "250 ₽ за каждый", "плати за отзыв"], "Накрутка отзывов"),
        (["bitcoin", "binance", "usdt", "крипто", "трейдинг", "инвестиц"], "Крипто/финансы"),
        (["неизвестная команда", "доступные команды:", "login code:", "😬"], "Системное сообщение бота"),
        (["getassistant", "marina_get"], "Сервис GetAssistant"),
        (["parser_lab"], "Сервис парсинга"),
        (["mailsphere"], "Сервис email-рассылок"),
        (["#дизайнер", "ищем дизайнера", "нужен дизайнер", "ux/ui", "ui/ux"], "Ищут дизайнера"),
        (["видеограф", "#видеограф", "видеомонтаж", "монтажёр"], "Видео/монтаж"),
        (["#smm", " smm ", "ведение соцсетей", "контент-план"], "SMM"),
        (["#копирайтер", "написание текстов", "копирайтинг"], "Копирайтинг"),
        (["1с ", "1с-программист", "программист 1с"], "1С / разработка"),
    ]
    for keywords, reason in patterns:
        if any(kw in combined for kw in keywords):
            return reason
    return "Нерелевантный запрос"


@router.get("/{lead_id}/draft")
async def get_lead_draft(lead_id: int):
    """Получить черновик отклика из vacancies.db."""
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT username FROM leads WHERE id = ?", [lead_id])
    if not rows:
        raise HTTPException(404, "Lead not found")
    username = dict(rows[0]).get("username")
    if not username or not os.path.exists(VACANCIES_DB_PATH):
        return {"draft": None}

    async with aiosqlite.connect(VACANCIES_DB_PATH) as vdb:
        vdb.row_factory = aiosqlite.Row
        rows2 = await vdb.execute_fetchall(
            """SELECT draft_response FROM vacancies
               WHERE contact_link LIKE ? AND status='accepted' AND draft_response IS NOT NULL
               ORDER BY last_seen DESC LIMIT 1""",
            [f"%{username}%"],
        )
    return {"draft": dict(rows2[0])["draft_response"] if rows2 else None}


@router.post("/{lead_id}/queue_outreach")
async def queue_outreach(lead_id: int):
    """Пометить лид как 'в работе' (contacted)."""
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM leads WHERE id = ?", [lead_id])
        if not rows:
            raise HTTPException(404, "Lead not found")
        lead = dict(rows[0])
        await db.execute(
            "UPDATE leads SET status='contacted', last_outreach_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
            [lead_id],
        )
        await db.execute("INSERT INTO audit_log(action,entity_type,entity_id) VALUES(?,?,?)", ["queue_outreach", "lead", lead_id])
        await db.execute(
            "INSERT INTO lead_feedback(lead_id, action, niche, vacancy_text) VALUES(?,?,?,?)",
            [lead_id, "wrote", lead.get("niche"), lead.get("vacancy_text")],
        )
        await db.commit()
    await manager.broadcast("leads", {"event": "lead_updated", "id": lead_id})
    return {"ok": True}


@router.post("/{lead_id}/mark_spam")
async def mark_spam(lead_id: int):
    """Архивировать лид как спам, занести username в чёрный список."""
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM leads WHERE id = ?", [lead_id])
        if not rows:
            raise HTTPException(404, "Lead not found")
        lead = dict(rows[0])
        reason = _analyze_spam_reason(lead.get("username", ""), lead.get("vacancy_text", "") or "")

        await db.execute(
            "UPDATE leads SET is_archived=1, status='spam', updated_at=datetime('now') WHERE id=?",
            [lead_id],
        )
        username = lead.get("username")
        if username:
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO pipeline_blacklist(type, value) VALUES('word', ?)",
                    [username.lower()],
                )
            except Exception:
                pass
        gap = _gap_analysis(lead.get("vacancy_text", ""), lead.get("username", ""))
        await db.execute(
            "INSERT INTO audit_log(action,entity_type,entity_id,new_value) VALUES(?,?,?,?)",
            ["mark_spam", "lead", lead_id, reason],
        )
        await db.execute(
            "INSERT INTO lead_feedback(lead_id, action, spam_reason, gap_analysis, niche, vacancy_text) VALUES(?,?,?,?,?,?)",
            [lead_id, "spam", reason, json.dumps(gap, ensure_ascii=False), lead.get("niche"), lead.get("vacancy_text")],
        )
        await db.commit()
    await manager.broadcast("leads", {"event": "lead_archived", "id": lead_id})
    return {"ok": True, "reason": reason, "username": username}


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
