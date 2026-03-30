from fastapi import APIRouter, HTTPException
from db.connection import get_db
from models.prompt import PromptCreate, PromptUpdate

router = APIRouter()


DEFAULT_PROMPTS = [
    {
        "name": "Первичный аутрич",
        "stage": "outreach",
        "content": """Ты — Алексей, специалист по интернет-маркетингу.

Тебе нужно написать первое сообщение потенциальному клиенту, который ищет специалиста по {specialization}.

Правила:
- Будь кратким (2-3 предложения)
- Покажи, что читал их запрос
- Упомяни конкретный релевантный кейс
- Предложи созвон или уточняющий вопрос
- Не используй шаблонные фразы ("рад помочь", "обращайтесь")

Запрос клиента: {vacancy_text}
Кейс: {case_data}"""
    },
    {
        "name": "Follow-up #1",
        "stage": "outreach",
        "content": """Напиши мягкий follow-up через 2 дня после первого сообщения.

Клиент: {full_name}
Ниша: {niche}
Предыдущее сообщение: {last_message}

Правила:
- Одно короткое предложение
- Без давления
- Добавь новую ценность (вопрос или мысль по теме)"""
    },
    {
        "name": "Квалификация лида",
        "stage": "dialog",
        "content": """Ты ведёшь диалог с потенциальным клиентом.

Твоя цель: выяснить 3 вещи:
1. Есть ли конкретная задача (что именно нужно сделать)
2. Есть ли бюджет (хотя бы порядок)
3. Есть ли срочность (когда нужен результат)

Контекст диалога: {dialog_history}

Напиши следующее сообщение, которое естественно уточнит один из этих пунктов."""
    },
    {
        "name": "LLM фильтр вакансий",
        "stage": "filter",
        "content": """Определи, является ли это сообщение реальной заявкой на услуги (заказчик ищет исполнителя) или нет.

Сообщение: {text}
Эвристический скор: {score}

Ответь JSON:
{
  "is_real_lead": true/false,
  "confidence": 0.0-1.0,
  "reason": "краткое объяснение"
}

НЕ является лидом если: исполнитель предлагает услуги, агентство ищет сотрудника, спам/скам."""
    },
]


@router.get("/")
async def list_prompts():
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM prompts ORDER BY stage, name")
        if not rows:
            # Создаём дефолтные промпты при первом запросе
            for p in DEFAULT_PROMPTS:
                await db.execute(
                    "INSERT INTO prompts(name,stage,content,version,is_active,created_at) VALUES(?,?,?,1,1,datetime('now'))",
                    [p["name"], p["stage"], p["content"]],
                )
            await db.commit()
            rows = await db.execute_fetchall("SELECT * FROM prompts ORDER BY stage, name")
    return [dict(r) for r in rows]


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM prompts WHERE id=?", [prompt_id])
    if not rows:
        raise HTTPException(404, "Prompt not found")
    return dict(rows[0])


@router.post("/")
async def create_prompt(prompt: PromptCreate):
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO prompts(name,stage,content,version,is_active,created_at) VALUES(?,?,?,1,1,datetime('now'))",
            [prompt.name, prompt.stage, prompt.content],
        )
        pid = cursor.lastrowid
        await db.execute(
            "INSERT INTO prompt_versions(prompt_id,version,content,created_at) VALUES(?,1,?,datetime('now'))",
            [pid, prompt.content],
        )
        await db.commit()
    return {"id": pid}


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: int, update: PromptUpdate):
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM prompts WHERE id=?", [prompt_id])
        if not rows:
            raise HTTPException(404, "Prompt not found")
        old = dict(rows[0])

        updates = {k: v for k, v in update.model_dump().items() if v is not None}
        if "content" in updates:
            new_version = old["version"] + 1
            updates["version"] = new_version
            await db.execute(
                "INSERT INTO prompt_versions(prompt_id,version,content,created_at) VALUES(?,?,?,datetime('now'))",
                [prompt_id, new_version, updates["content"]],
            )

        if updates:
            set_sql = ", ".join(f"{k} = ?" for k in updates)
            await db.execute(
                f"UPDATE prompts SET {set_sql} WHERE id=?",
                list(updates.values()) + [prompt_id],
            )
            await db.commit()
    return {"ok": True}


@router.post("/{prompt_id}/rollback")
async def rollback_prompt(prompt_id: int, version: int):
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM prompt_versions WHERE prompt_id=? AND version=?",
            [prompt_id, version],
        )
        if not rows:
            raise HTTPException(404, f"Version {version} not found")
        content = rows[0]["content"]
        cur_rows = await db.execute_fetchall("SELECT version FROM prompts WHERE id=?", [prompt_id])
        if not cur_rows:
            raise HTTPException(404, "Prompt not found")
        new_version = cur_rows[0]["version"] + 1
        await db.execute(
            "INSERT INTO prompt_versions(prompt_id,version,content,created_at) VALUES(?,?,?,datetime('now'))",
            [prompt_id, new_version, content],
        )
        await db.execute(
            "UPDATE prompts SET content=?, version=? WHERE id=?",
            [content, new_version, prompt_id],
        )
        await db.commit()
    return {"version": new_version}


@router.get("/{prompt_id}/versions")
async def prompt_versions(prompt_id: int):
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM prompt_versions WHERE prompt_id=? ORDER BY version DESC",
            [prompt_id],
        )
    return [dict(r) for r in rows]
