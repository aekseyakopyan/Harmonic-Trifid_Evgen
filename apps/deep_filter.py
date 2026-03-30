import asyncio
import sqlite3
import os
import sys
import json
import re

# Add project root to path
sys.path.append(os.getcwd())

from core.ai_engine.llm_client import LLMClient
from core.utils.logger import logger

# System prompt for batch classification
SYSTEM_PROMPT = """
Ты — эксперт-аналитик по маркетингу. Твоя задача: классифицировать список сообщений из Telegram.

КАТЕГОРИИ:
1. BUYER — кто-то ищет специалиста, подрядчика, задает вопрос по услуге, просит рекомендации.
2. SELLER — кто-то предлагает свои услуги, кейсы, обучение, приглашает в канал, спам от специалистов.
3. IRRELEVANT — мусор, новости, общение ни о чем.

Формат входных данных: JSON список объектов {"id": number, "text": string}.
ФОРМАТ ОТВЕТА: Только JSON список объектов {"id": number, "result": "BUYER" | "SELLER" | "IRRELEVANT"}.
Никакого лишнего текста в ответе, только чистый JSON.
"""

BATCH_SIZE = 120

async def filter_leads_batch(limit=None):
    db_path = "data/db/all_historical_leads.db"
    if not os.path.exists(db_path):
        print(f"❌ База {db_path} не найдена.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Migration: Add columns if not exist
    try:
        cursor.execute("ALTER TABLE all_historical_leads ADD COLUMN llm_reason TEXT;")
        cursor.execute("ALTER TABLE all_historical_leads ADD COLUMN llm_marker TEXT;")
    except sqlite3.OperationalError:
        pass # Already exists
    
    # Load only non-processed leads
    cursor.execute("SELECT id, text FROM all_historical_leads WHERE llm_status IS NULL LIMIT 2000") # Process in chunks
    
    leads = cursor.fetchall()
    
    if not leads:
        print("✅ Нет новых лидов для фильтрации.")
        return

    print(f"🚀 Начинаю пакетную LLM-фильтрацию {len(leads)} лидов через DeepSeek (пакеты по {BATCH_SIZE})...")
    llm_client = LLMClient()
    
    processed_this_session = 0
    total_leads = 4466 # approximate
    
    # Process in batches
    for i in range(0, len(leads), BATCH_SIZE):
        batch = leads[i:i+BATCH_SIZE]
        batch_data = [{"id": l[0], "text": l[1][:400].replace("\n", " ")} for l in batch]
        
        try:
            prompt = f"Разобрать следующие сообщения:\n{json.dumps(batch_data, ensure_ascii=False)}"
            response = await llm_client.generate_response(prompt=prompt, system_prompt=SYSTEM_PROMPT)
            
            if not response:
                print(f"⚠️ Пустой ответ от ИИ для пакета {i//BATCH_SIZE + 1}")
                continue

            # Heavy-duty JSON extraction
            json_str = response.strip()
            # Remove Markdown code blocks
            json_str = re.sub(r'```json\s*|\s*```', '', json_str)
            json_str = re.sub(r'```\s*|\s*```', '', json_str)
            
            # Find the list start and end
            start_idx = json_str.find('[')
            end_idx = json_str.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]
            
            try:
                results = json.loads(json_str)
            except json.JSONDecodeError as je:
                # If JSON fails, try a desperate regex approach for each item
                print(f"⚠️ Ошибка парсинга JSON, пытаюсь восстановить данные через Regex...")
                results = []
                # Handle cases like {id: 123, result: BUYER, reason: ..., marker: ...}
                # Reason and marker might be omitted by LLM if it gets lazy
                matches = re.finditer(r'\{[^{}]*"?id"?:\s*(\d+)[^{}]*"?result"?:\s*"?(\w+)"?(?:[^{}]*"?reason"?:\s*"?(.*?)"?)?(?:[^{}]*"?marker"?:\s*"?(.*?)"?)?[^{}]*\}', json_str, re.IGNORECASE)
                for m in matches:
                    results.append({
                        "id": int(m.group(1)), 
                        "result": m.group(2).upper(),
                        "reason": m.group(3) if m.lastindex >= 3 and m.group(3) else "",
                        "marker": m.group(4) if m.lastindex >= 4 and m.group(4) else ""
                    })
                
                if not results:
                    print(f"❌ Не удалось спасти пакет {i//BATCH_SIZE + 1}. Ответ был: {response[:300]}...")
                    raise je

            ids_to_delete = []
            ids_to_mark_buyer = []
            updates = []

            for res in results:
                r_id = res.get("id")
                status = str(res.get("result", "")).upper()
                reason = res.get("reason", "")
                marker = res.get("marker", "")
                
                if "SELLER" in status or "IRRELEVANT" in status:
                    ids_to_delete.append(r_id)
                elif "BUYER" in status:
                    ids_to_mark_buyer.append(r_id)
                
                updates.append((status, reason, marker, r_id))

            # Update DB with reasoning
            for update in updates:
                cursor.execute("UPDATE all_historical_leads SET llm_status=?, llm_reason=?, llm_marker=? WHERE id=?", update)

            # Log deleted for analysis
            if ids_to_delete:
                with open("logs/deleted_leads_for_analysis.log", "a", encoding="utf-8") as df:
                    for d_id in ids_to_delete:
                        # Find the text, reason, marker
                        for res in results:
                            if res.get("id") == d_id:
                                # Find text in batch
                                text = next((l[1] for l in batch if l[0] == d_id), "N/A")
                                df.write(f"--- ID: {d_id} | Reason: {res.get('reason')} | Marker: {res.get('marker')} ---\n{text}\n")
                
                placeholders = ','.join('?' * len(ids_to_delete))
                cursor.execute(f"DELETE FROM all_historical_leads WHERE id IN ({placeholders})", ids_to_delete)
            
            conn.commit()

            processed_this_session += len(batch)
            progress = (processed_this_session / len(leads)) * 100
            print(f"[{progress:.2f}%] | Пакет {i//BATCH_SIZE + 1} обработан (Удалено: {len(ids_to_delete)}, Оставлено: {len(ids_to_mark_buyer)})")

        except Exception as e:
            print(f"❌ Ошибка на пакете {i//BATCH_SIZE + 1}: {e}")
            await asyncio.sleep(5)
            
    print(f"🏁 Фильтрация завершена. Успешно обработано {processed_this_session} записей.")
    conn.close()

if __name__ == "__main__":
    asyncio.run(filter_leads_batch())
