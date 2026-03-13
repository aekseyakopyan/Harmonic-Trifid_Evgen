"""
FastAPI backend для Telegram Mini App + Web Dashboard.
Предоставляет API для мониторинга системы, управления лидами и RL статистикой.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import aiosqlite
import asyncio
import subprocess
import os
import re
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config.settings import settings

app = FastAPI(title="Harmonic Trifid Dashboard API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_FILES = {
    "alexey": PROJECT_ROOT / "logs" / "alexey.log",
    "gwen":   PROJECT_ROOT / "logs" / "gwen.log",
    "parser": PROJECT_ROOT / "logs" / "parser.log",
    "joiner": PROJECT_ROOT / "logs" / "chat_joiner.log",
}

# ─────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────

class DealUpdateRequest(BaseModel):
    outreach_id: int
    deal_closed: bool
    conversation_length: int
    deal_amount: Optional[float] = None

class FeedbackRequest(BaseModel):
    outreach_id: int
    client_replied: bool
    reply_time_seconds: Optional[int] = None

# ─────────────────────────────────────────────
# SYSTEM STATUS
# ─────────────────────────────────────────────

@app.get("/api/system/status")
async def get_system_status():
    """Статус всех ключевых процессов системы."""
    services = {
        "alexey":   {"pattern": "systems/alexey/main.py",    "label": "Alexey Outreach"},
        "parser":   {"pattern": "main.py parse today",       "label": "Today Parser"},
        "gwen":     {"pattern": "systems/gwen/bot.py",       "label": "Gwen Supervisor"},
        "joiner":   {"pattern": "apps/chat_joiner.py",       "label": "Chat Joiner"},
        "miniapp":  {"pattern": "systems/miniapp/api.py",    "label": "Mini App API"},
        "dashboard":{"pattern": "systems/dashboard/main.py", "label": "Dashboard"},
    }

    result = {}
    try:
        proc = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        ps_out = proc.stdout
    except Exception:
        ps_out = ""

    for key, info in services.items():
        lines = [l for l in ps_out.splitlines() if info["pattern"] in l and "grep" not in l]
        running = len(lines) > 0
        pid = None
        uptime_str = None
        if running and lines:
            parts = lines[0].split()
            pid = parts[1] if len(parts) > 1 else None
            # column 8 = start time (ps aux)
            start_raw = parts[8] if len(parts) > 8 else None
            uptime_str = parts[9] if len(parts) > 9 else None  # CPU time as rough proxy
        result[key] = {
            "label": info["label"],
            "running": running,
            "pid": pid,
            "cpu_time": uptime_str,
        }

    # Server time
    now_utc = datetime.utcnow()
    hour_utc = now_utc.hour
    outreach_window = 8 <= hour_utc <= 23

    return {
        "services": result,
        "server_time_utc": now_utc.isoformat(),
        "outreach_window_active": outreach_window,
    }

# ─────────────────────────────────────────────
# VACANCIES STATS
# ─────────────────────────────────────────────

@app.get("/api/vacancies/stats")
async def get_vacancies_stats():
    """Статистика лидов из vacancies.db."""
    db_path = settings.VACANCY_DB_PATH
    async with aiosqlite.connect(db_path) as db:
        # All time by status
        cursor = await db.execute(
            "SELECT status, COUNT(*) FROM vacancies GROUP BY status ORDER BY 2 DESC"
        )
        by_status = {r[0]: r[1] for r in await cursor.fetchall()}

        # Last 24h
        cursor = await db.execute(
            "SELECT status, COUNT(*) FROM vacancies "
            "WHERE last_seen > datetime('now', '-1 day') GROUP BY status ORDER BY 2 DESC"
        )
        last_24h = {r[0]: r[1] for r in await cursor.fetchall()}

        # Queue: accepted + NULL/empty response
        cursor = await db.execute(
            "SELECT COUNT(*) FROM vacancies "
            "WHERE status='accepted' AND (response IS NULL OR response = '')"
        )
        queue_count = (await cursor.fetchone())[0]

        # Notified (stuck)
        cursor = await db.execute(
            "SELECT COUNT(*) FROM vacancies "
            "WHERE status='accepted' AND response='notified'"
        )
        notified_count = (await cursor.fetchone())[0]

        # Sent
        cursor = await db.execute(
            "SELECT COUNT(*) FROM vacancies WHERE response='sent'"
        )
        sent_count = (await cursor.fetchone())[0]

        # no_contact
        cursor = await db.execute(
            "SELECT COUNT(*) FROM vacancies WHERE response='no_contact_skip'"
        )
        no_contact = (await cursor.fetchone())[0]

        # Rejected 24h
        r24_rejected = last_24h.get("rejected", 0)
        r24_accepted  = last_24h.get("accepted", 0)
        total_24h = r24_rejected + r24_accepted
        acceptance_rate = round(r24_accepted / max(total_24h, 1) * 100, 1)

    return {
        "by_status": by_status,
        "last_24h": last_24h,
        "queue_pending": queue_count,
        "notified_stuck": notified_count,
        "sent_total": sent_count,
        "no_contact_total": no_contact,
        "acceptance_rate_24h": acceptance_rate,
        "total_24h": total_24h,
    }

# ─────────────────────────────────────────────
# QUEUE — список лидов в очереди
# ─────────────────────────────────────────────

@app.get("/api/vacancies/queue")
async def get_queue(limit: int = Query(50, le=200)):
    """Лиды в очереди на отправку (accepted + пустой response)."""
    db_path = settings.VACANCY_DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, hash, direction, contact_link, text, draft_response,
                   response, last_seen, tier, priority
            FROM vacancies
            WHERE status='accepted' AND (response IS NULL OR response = '')
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()

    leads = []
    for r in rows:
        leads.append({
            "id": r["id"],
            "hash": (r["hash"] or "")[:12],
            "direction": r["direction"],
            "contact": r["contact_link"],
            "text_preview": (r["text"] or "")[:150],
            "has_draft": bool(r["draft_response"]),
            "draft_preview": (r["draft_response"] or "")[:200],
            "response": r["response"],
            "last_seen": r["last_seen"],
            "tier": r["tier"],
            "priority": r["priority"],
        })
    return {"leads": leads, "total": len(leads)}

# ─────────────────────────────────────────────
# ACCEPTED — все квалифицированные лиды
# ─────────────────────────────────────────────

@app.get("/api/vacancies/accepted")
async def get_accepted_leads(
    limit: int = Query(100, le=1000),
    offset: int = 0,
    search: Optional[str] = None
):
    """Все квалифицированные лиды (status='accepted')."""
    db_path = settings.VACANCY_DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        query = "SELECT id, hash, direction, contact_link, text, response, last_seen, tier, priority FROM vacancies WHERE status='accepted'"
        params = []
        
        if search:
            query += " AND (text LIKE ? OR direction LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
            
        query += " ORDER BY last_seen DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        # Count total for pagination
        count_query = "SELECT COUNT(*) FROM vacancies WHERE status='accepted'"
        count_params = []
        if search:
            count_query += " AND (text LIKE ? OR direction LIKE ?)"
            count_params.extend([f"%{search}%", f"%{search}%"])
        
        count_cursor = await db.execute(count_query, count_params)
        total_count = (await count_cursor.fetchone())[0]

    leads = []
    for r in rows:
        leads.append({
            "id": r["id"],
            "hash": (r["hash"] or "")[:12],
            "direction": r["direction"],
            "contact": r["contact_link"],
            "text": r["text"],
            "response": r["response"] or "Ожидает",
            "last_seen": r["last_seen"],
            "tier": r["tier"],
            "priority": r["priority"],
        })
    return {"leads": leads, "total": total_count, "limit": limit, "offset": offset}

# ─────────────────────────────────────────────
# RESET QUEUE — сброс зависших лидов
# ─────────────────────────────────────────────

@app.post("/api/vacancies/reset-queue")
async def reset_stuck_queue():
    """Сбросить зависшие лиды (notified + текст в response) → NULL."""
    db_path = settings.VACANCY_DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("""
            UPDATE vacancies SET response = NULL
            WHERE status='accepted' AND (
                response = 'notified'
                OR (response IS NOT NULL AND response != ''
                    AND response NOT IN ('sent','failed','skipped_duplicate','no_contact_skip','SKIPPED'))
            )
        """)
        await db.commit()
        count = cursor.rowcount

    return {"reset_count": count, "message": f"Сброшено {count} лидов в очередь"}

# ─────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────

@app.get("/api/logs/tail")
async def tail_log(
    log: str = Query("alexey", enum=["alexey", "gwen", "parser", "joiner"]),
    n: int = Query(100, le=500)
):
    """Последние N строк выбранного лога."""
    log_path = LOG_FILES.get(log)
    if not log_path or not log_path.exists():
        return {"lines": [], "error": f"Лог {log} не найден: {log_path}"}

    try:
        result = subprocess.run(
            ["tail", "-n", str(n), str(log_path)],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.splitlines()
    except Exception as e:
        return {"lines": [], "error": str(e)}

    return {"log": log, "lines": lines, "count": len(lines)}

# ─────────────────────────────────────────────
# CONTROLS
# ─────────────────────────────────────────────

@app.post("/api/controls/restart")
async def restart_service(service: str = Query("alexey", enum=["alexey"])):
    """Перезапустить сервис (nohup)."""
    project_root = str(PROJECT_ROOT)
    venv_python = str(PROJECT_ROOT / "venv" / "bin" / "python3")

    service_map = {
        "alexey": {
            "pattern": "systems/alexey/main.py",
            "script": f"systems/alexey/main.py",
            "log": f"{project_root}/logs/alexey.log",
            "pid": f"{project_root}/pids/alexey.pid",
        }
    }
    svc = service_map.get(service)
    if not svc:
        raise HTTPException(status_code=400, detail="Неизвестный сервис")

    try:
        # Kill existing process
        subprocess.run(
            ["pkill", "-f", svc["pattern"]],
            capture_output=True, text=True, timeout=5
        )
        import time
        time.sleep(1)

        # Start new process detached
        env = os.environ.copy()
        env["PYTHONPATH"] = project_root
        with open(svc["log"], "a") as logf:
            proc = subprocess.Popen(
                [venv_python, f"{project_root}/{svc['script']}"],
                stdout=logf, stderr=logf,
                env=env, cwd=project_root,
                start_new_session=True
            )
        # Save PID
        Path(svc["pid"]).write_text(str(proc.pid))

        return {
            "success": True,
            "pid": proc.pid,
            "message": f"Перезапущен (PID {proc.pid})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/controls/update-restart")
async def update_and_restart_all():
    """Git pull + перезапустить Alexey + перезапустить этот сервис."""
    project_root = str(PROJECT_ROOT)
    venv_python = str(PROJECT_ROOT / "venv" / "bin" / "python3")

    script = f"""#!/bin/bash
sleep 2
cd {project_root}
git pull origin main 2>&1
export PYTHONPATH={project_root}
pkill -f "systems/alexey/main.py" 2>/dev/null || true
sleep 1
nohup {venv_python} {project_root}/systems/alexey/main.py >> {project_root}/logs/alexey.log 2>&1 &
echo $! > {project_root}/pids/alexey.pid
sleep 1
pkill -f "systems/miniapp/api.py" 2>/dev/null || true
sleep 1
nohup {venv_python} {project_root}/systems/miniapp/api.py >> {project_root}/logs/miniapp.log 2>&1 &
echo $! > {project_root}/pids/miniapp.pid
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(script)
        script_path = f.name
    os.chmod(script_path, 0o755)
    subprocess.Popen(
        ["bash", script_path],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return {"success": True, "message": "Update+restart запущен, сервисы поднимутся через ~5 сек"}

@app.get("/api/server/info")
async def get_server_info():
    """Базовая информация о сервере."""
    try:
        uptime = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        uptime = "н/д"

    try:
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=3).stdout
        disk_lines = disk.strip().splitlines()
        disk_info = disk_lines[1] if len(disk_lines) > 1 else "н/д"
    except Exception:
        disk_info = "н/д"

    try:
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=3).stdout
        mem_lines = mem.strip().splitlines()
        mem_info = mem_lines[1] if len(mem_lines) > 1 else "н/д"
    except Exception:
        mem_info = "н/д"

    return {
        "uptime": uptime,
        "disk": disk_info,
        "memory": mem_info,
        "server_ip": "31.128.37.161",
        "project_path": "/opt/harmonic-trifid/Harmonic-Trifid_Evgen",
        "server_time_utc": datetime.utcnow().isoformat(),
    }

# ─────────────────────────────────────────────
# LEGACY — оставляем совместимость
# ─────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    """Общая статистика (legacy miniapp)."""
    db_path = settings.VACANCY_DB_PATH
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM vacancies")
        total_leads = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM vacancies WHERE tier = 'HOT'")
        hot_leads = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM vacancies WHERE last_seen > datetime('now', '-1 day')"
        )
        leads_24h = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM vacancies WHERE response='sent'")
        outreach_sent = (await cursor.fetchone())[0]

    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "leads_24h": leads_24h,
        "outreach_sent": outreach_sent,
        "reply_rate": 0.0,
    }

# ─────────────────────────────────────────────
# Static files & SPA
# ─────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_path = static_dir / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>Dashboard not found</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
