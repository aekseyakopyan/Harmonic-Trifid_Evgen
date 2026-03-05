from fastapi import APIRouter
from db.connection import get_db
from typing import Literal

router = APIRouter()

PERIOD_SQL = {
    "day": "datetime('now','-1 day')",
    "week": "datetime('now','-7 days')",
    "month": "datetime('now','-30 days')",
}


@router.get("/overview")
async def overview(period: Literal["day", "week", "month"] = "week"):
    since = PERIOD_SQL[period]
    async with get_db() as db:
        total = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads WHERE is_archived=0"))[0]["c"]
        new_in_period = (await db.execute_fetchall(
            f"SELECT COUNT(*) as c FROM leads WHERE created_at >= {since} AND is_archived=0"
        ))[0]["c"]
        hot = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE tier='HOT' AND is_archived=0"
        ))[0]["c"]
        warm = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE tier='WARM' AND is_archived=0"
        ))[0]["c"]
        dialogs_active = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM dialogs WHERE status='active'"
        ))[0]["c"]
        dialogs_total = (await db.execute_fetchall(
            f"SELECT COUNT(*) as c FROM dialogs WHERE started_at >= {since}"
        ))[0]["c"]
        msgs_total = (await db.execute_fetchall(
            f"SELECT COUNT(*) as c FROM dialog_messages WHERE sent_at >= {since}"
        ))[0]["c"]

    return {
        "period": period,
        "total_leads": total,
        "new_leads": new_in_period,
        "hot_leads": hot,
        "warm_leads": warm,
        "dialogs_active": dialogs_active,
        "dialogs_in_period": dialogs_total,
        "messages_in_period": msgs_total,
        "conversion_rate": round(hot / total * 100, 1) if total else 0,
    }


@router.get("/leads_timeline")
async def leads_timeline(period: Literal["day", "week", "month"] = "week"):
    fmt = {
        "day": ("%H:00", "strftime('%H', created_at)"),
        "week": ("%Y-%m-%d", "strftime('%Y-%m-%d', created_at)"),
        "month": ("%Y-%m-%d", "strftime('%Y-%m-%d', created_at)"),
    }[period]
    since = PERIOD_SQL[period]
    async with get_db() as db:
        rows = await db.execute_fetchall(
            f"SELECT {fmt[1]} as dt, COUNT(*) as cnt FROM leads WHERE created_at >= {since} AND is_archived=0 GROUP BY dt ORDER BY dt",
        )
    return [{"date": r["dt"], "count": r["cnt"]} for r in rows]


@router.get("/by_niche")
async def by_niche():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT COALESCE(niche,'Unknown') as niche, COUNT(*) as cnt FROM leads WHERE is_archived=0 GROUP BY niche ORDER BY cnt DESC LIMIT 20"
        )
    return [dict(r) for r in rows]


@router.get("/by_source")
async def by_source():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT COALESCE(source_channel,'Unknown') as source_channel, COUNT(*) as cnt FROM leads WHERE is_archived=0 GROUP BY source_channel ORDER BY cnt DESC LIMIT 20"
        )
    return [dict(r) for r in rows]


@router.get("/alexey_load")
async def alexey_load():
    async with get_db() as db:
        by_hour = await db.execute_fetchall(
            """SELECT strftime('%H', sent_at) as hour, COUNT(*) as cnt
               FROM dialog_messages WHERE role='assistant'
               AND sent_at >= datetime('now','-7 days')
               GROUP BY hour ORDER BY hour"""
        )
        total_sent = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM dialog_messages WHERE role='assistant' AND sent_at >= datetime('now','-7 days')"
        ))[0]["c"]
        manual_sent = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM dialog_messages WHERE is_manual=1 AND sent_at >= datetime('now','-7 days')"
        ))[0]["c"]
    return {
        "total_sent_7d": total_sent,
        "manual_sent_7d": manual_sent,
        "auto_sent_7d": total_sent - manual_sent,
        "by_hour": [dict(r) for r in by_hour],
    }
