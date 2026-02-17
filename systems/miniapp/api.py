"""
FastAPI backend для Telegram Mini App.
Предоставляет API для управления лидами и RL статистикой.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import aiosqlite
from datetime import datetime, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config.settings import settings
from systems.alexey.rl_agent import rl_agent

app = FastAPI(title="Harmonic Trifid Mini App API")

# CORS для Telegram
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DealUpdateRequest(BaseModel):
    outreach_id: int
    deal_closed: bool
    conversation_length: int
    deal_amount: Optional[float] = None

class FeedbackRequest(BaseModel):
    outreach_id: int
    client_replied: bool
    reply_time_seconds: Optional[int] = None

@app.get("/api/stats")
async def get_stats():
    """Общая статистика системы."""
    async with aiosqlite.connect(settings.VACANCY_DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM vacancies")
        total_leads = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM vacancies WHERE tier = 'HOT'")
        hot_leads = (await cursor.fetchone())[0]
        
        yesterday = (datetime.now() - timedelta(days=1)).timestamp()
        cursor = await db.execute(
            "SELECT COUNT(*) FROM vacancies WHERE timestamp > ?", (yesterday,)
        )
        leads_24h = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM outreach_attempts")
        outreach_sent = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM outreach_attempts WHERE client_replied = 1"
        )
        replies = (await cursor.fetchone())[0]
        reply_rate = (replies / max(outreach_sent, 1)) * 100
    
    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "leads_24h": leads_24h,
        "outreach_sent": outreach_sent,
        "reply_rate": round(reply_rate, 1)
    }

@app.get("/api/leads/hot")
async def get_hot_leads(limit: int = 20):
    """Получить HOT-лиды."""
    async with aiosqlite.connect(settings.VACANCY_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, text, priority, tier, timestamp
            FROM vacancies
            WHERE tier = 'HOT'
            ORDER BY priority DESC, timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        
        leads = []
        for row in rows:
            text = row['text'] or ""
            leads.append({
                "id": row['id'],
                "text": text[:200] + "..." if len(text) > 200 else text,
                "priority": row['priority'] or 0,
                "tier": row['tier']
            })
    
    return {"leads": leads}

@app.post("/api/outreach/generate")
async def generate_outreach(lead_id: int):
    """Сгенерировать отклик для лида."""
    from systems.alexey.alexey_engine_rl import alexey_rl
    
    async with aiosqlite.connect(settings.VACANCY_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM vacancies WHERE id = ?", (lead_id,))
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        lead_data = dict(row)
    
    result = await alexey_rl.generate_outreach_with_rl(lead_data)
    return result

@app.post("/api/feedback/reply")
async def record_reply(feedback: FeedbackRequest):
    """Зафиксировать ответ клиента."""
    await rl_agent.update_feedback(
        outreach_id=feedback.outreach_id,
        client_replied=feedback.client_replied,
        reply_time_seconds=feedback.reply_time_seconds
    )
    return {"status": "ok"}

@app.post("/api/feedback/deal")
async def record_deal(deal: DealUpdateRequest):
    """Зафиксировать результат сделки."""
    await rl_agent.update_feedback(
        outreach_id=deal.outreach_id,
        client_replied=True,
        conversation_length=deal.conversation_length,
        deal_closed=deal.deal_closed,
        deal_amount=deal.deal_amount
    )
    return {"status": "ok"}

@app.get("/api/rl/performance")
async def get_rl_performance():
    """Отчет о производительности RL стратегий."""
    report = await rl_agent.get_performance_report()
    return report

# Static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Главная страница Mini App."""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>Mini App Frontend - создается...</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
