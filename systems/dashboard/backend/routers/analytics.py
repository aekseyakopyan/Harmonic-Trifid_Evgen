from fastapi import APIRouter
from db.connection import get_db
from core.config import VACANCIES_DB_PATH
from typing import Literal
import aiosqlite, os

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


@router.get("/funnel")
async def funnel():
    """Воронка фильтрации: сколько лидов на каждом статусе."""
    async with get_db() as db:
        by_status = await db.execute_fetchall(
            "SELECT COALESCE(status,'new') as status, COUNT(*) as cnt FROM leads GROUP BY status ORDER BY cnt DESC"
        )
        by_tier = await db.execute_fetchall(
            "SELECT COALESCE(tier,'COLD') as tier, COUNT(*) as cnt FROM leads WHERE is_archived=0 GROUP BY tier"
        )
        total = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads"))[0]["c"]
        archived = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads WHERE is_archived=1"))[0]["c"]

    # Данные из vacancies.db если доступны
    vac_stats = {"accepted": 0, "rejected": 0, "pending": 0}
    if os.path.exists(VACANCIES_DB_PATH):
        try:
            async with aiosqlite.connect(VACANCIES_DB_PATH) as vdb:
                vdb.row_factory = aiosqlite.Row
                rows = await (await vdb.execute(
                    "SELECT status, COUNT(*) as cnt FROM vacancies GROUP BY status"
                )).fetchall()
                for r in rows:
                    vac_stats[r["status"]] = r["cnt"]
        except Exception:
            pass

    return {
        "by_status": [dict(r) for r in by_status],
        "by_tier": [dict(r) for r in by_tier],
        "total": total,
        "archived": archived,
        "vacancies": vac_stats,
    }


@router.get("/qual_distribution")
async def qual_distribution():
    """Распределение оценок qual_score и fit_score."""
    async with get_db() as db:
        qual = await db.execute_fetchall(
            "SELECT qual_score as score, COUNT(*) as cnt FROM leads WHERE qual_score IS NOT NULL GROUP BY qual_score ORDER BY qual_score"
        )
        fit = await db.execute_fetchall(
            "SELECT fit_score as score, COUNT(*) as cnt FROM leads WHERE fit_score IS NOT NULL GROUP BY fit_score ORDER BY fit_score"
        )
        rated = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE qual_score IS NOT NULL OR fit_score IS NOT NULL"
        ))[0]["c"]
        avg_qual = (await db.execute_fetchall(
            "SELECT ROUND(AVG(qual_score),1) as v FROM leads WHERE qual_score IS NOT NULL"
        ))[0]["v"]
        avg_fit = (await db.execute_fetchall(
            "SELECT ROUND(AVG(fit_score),1) as v FROM leads WHERE fit_score IS NOT NULL"
        ))[0]["v"]
    return {
        "qual": [dict(r) for r in qual],
        "fit": [dict(r) for r in fit],
        "rated_count": rated,
        "avg_qual": avg_qual,
        "avg_fit": avg_fit,
    }


@router.get("/home")
async def home_stats():
    """Все ключевые метрики для главной страницы."""
    async with get_db() as db:
        total = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads WHERE is_archived=0"))[0]["c"]
        hot = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads WHERE tier='HOT' AND is_archived=0"))[0]["c"]
        warm = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads WHERE tier='WARM' AND is_archived=0"))[0]["c"]
        cold = (await db.execute_fetchall("SELECT COUNT(*) as c FROM leads WHERE tier='COLD' AND is_archived=0"))[0]["c"]
        new_today = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE created_at >= date('now') AND is_archived=0"
        ))[0]["c"]
        new_week = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE created_at >= datetime('now','-7 days') AND is_archived=0"
        ))[0]["c"]
        dialogs_active = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM dialogs WHERE status='active'"
        ))[0]["c"]
        qualified = (await db.execute_fetchall(
            "SELECT COUNT(*) as c FROM leads WHERE status='qualified' AND is_archived=0"
        ))[0]["c"]
        recent = await db.execute_fetchall(
            "SELECT id, full_name, username, tier, status, created_at FROM leads WHERE is_archived=0 ORDER BY created_at DESC LIMIT 5"
        )
    return {
        "total": total,
        "hot": hot,
        "warm": warm,
        "cold": cold,
        "new_today": new_today,
        "new_week": new_week,
        "dialogs_active": dialogs_active,
        "qualified": qualified,
        "conversion_rate": round(qualified / total * 100, 1) if total else 0,
        "recent_leads": [dict(r) for r in recent],
    }


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


@router.get("/qual_trend")
async def qual_trend(period: Literal["week", "month"] = "week"):
    """Тренд средних оценок qual_score/fit_score по дням."""
    since = PERIOD_SQL.get(period, PERIOD_SQL["week"])
    async with get_db() as db:
        rows = await db.execute_fetchall(
            f"""SELECT strftime('%Y-%m-%d', created_at) as dt,
                       ROUND(AVG(qual_score),2) as avg_qual,
                       ROUND(AVG(fit_score),2) as avg_fit,
                       COUNT(*) as cnt
                FROM leads
                WHERE created_at >= {since}
                  AND (qual_score IS NOT NULL OR fit_score IS NOT NULL)
                GROUP BY dt ORDER BY dt""",
        )
    return [dict(r) for r in rows]


@router.get("/filter_stats")
async def filter_stats():
    """Статистика причин отклонения из vacancies.db."""
    result = {"top_reasons": [], "by_level": {}, "total_rejected": 0, "total_accepted": 0}
    if not os.path.exists(VACANCIES_DB_PATH):
        return result
    try:
        async with aiosqlite.connect(VACANCIES_DB_PATH) as vdb:
            vdb.row_factory = aiosqlite.Row
            # Total counts
            totals = await (await vdb.execute(
                "SELECT status, COUNT(*) as cnt FROM vacancies GROUP BY status"
            )).fetchall()
            for r in totals:
                if r["status"] == "accepted":
                    result["total_accepted"] = r["cnt"]
                elif r["status"] == "rejected":
                    result["total_rejected"] = r["cnt"]

            # Top rejection reasons
            try:
                reasons = await (await vdb.execute(
                    """SELECT rejection_reason, COUNT(*) as cnt
                       FROM vacancies WHERE status='rejected' AND rejection_reason IS NOT NULL
                       GROUP BY rejection_reason ORDER BY cnt DESC LIMIT 30"""
                )).fetchall()
                result["top_reasons"] = [dict(r) for r in reasons]
            except Exception:
                pass

            # By filter level (L1/L2/ML/LLM prefix)
            try:
                level_rows = await (await vdb.execute(
                    """SELECT
                         CASE
                           WHEN rejection_reason LIKE 'L1%' OR rejection_reason LIKE 'BLACKLIST%' OR rejection_reason LIKE 'EXECUTOR%' OR rejection_reason LIKE 'CRYPTO%' OR rejection_reason LIKE 'MLM%' OR rejection_reason LIKE 'SPAM%' OR rejection_reason LIKE 'AGENCY%' OR rejection_reason LIKE 'STAFF%' OR rejection_reason LIKE 'DUPLICATE%' THEN 'L1'
                           WHEN rejection_reason LIKE 'L2%' OR rejection_reason LIKE 'SCORE%' THEN 'L2'
                           WHEN rejection_reason LIKE 'ML%' THEN 'ML'
                           WHEN rejection_reason LIKE 'LLM%' THEN 'LLM'
                           ELSE 'Other'
                         END as level,
                         COUNT(*) as cnt
                       FROM vacancies WHERE status='rejected' AND rejection_reason IS NOT NULL
                       GROUP BY level ORDER BY cnt DESC"""
                )).fetchall()
                result["by_level"] = {r["level"]: r["cnt"] for r in level_rows}
            except Exception:
                pass
    except Exception:
        pass
    return result
