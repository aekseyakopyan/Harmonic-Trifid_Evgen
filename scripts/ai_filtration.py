import asyncio
import sqlite3
import os
import sys
import json
import re
from typing import List, Dict

# Добавляем корень проекта в путь, чтобы импортировать LLMClient
sys.path.append(os.getcwd())

from core.ai_engine.llm_client import llm_client
from core.config.settings import settings
from core.utils.logger import logger

DB_PATH = "data/db/history_buyer_leads.db"
TABLE_NAME = "history_leads"
BATCH_SIZE = 15 # Уменьшаем батч для более точных ответов с причинами

SYSTEM_PROMPT = """
Ты — эксперт по фильтрации лидов для маркетингового агентства. Твоя задача — проанализировать сообщения и определить, являются ли они целевыми запросами (ЗАКАЗЧИКИ) или мусором (СПАМ/ПРОДАВЦЫ).

НАШИ ЦЕЛЕВЫЕ НИШИ (Status 1):
1. SEO (Сео, продвижение сайтов, поисковая оптимизация, аудит сайта).
2. Контекстная реклама (Яндекс Директ, Google Ads, контекстолог, лидогенерация из поиска).
3. Авито (Авитологи, продвижение на Авито, маспостинг).
4. Разработка сайтов (Тильда, Landing Page, создание сайтов под ключ).

КРИТЕРИИ ЛИДА (ai_status = 1):
1. ЗАПРОС на покупку/услугу (Buyers) — "нужен SEO", "ищу спеца по Директу", "кто сделает сайт?", "нужен аудит".
2. Текст содержит запрос специалиста из наших целевых ниш.

КРИТЕРИИ СПАМА (ai_status = 2):
1. ПРЕДЛОЖЕНИЕ услуг (Sellers) — "сделаю", "создам", "настрою", "я ассистент", "ищем работу", "возьму проект".
2. НЕРАБОЧИЕ задачи — SMM, таргетологи, дизайнеры, художники, копирайтеры (если не SEO), монтажеры видео, Reels, Shorts.
3. РЕКЛАМА — приглашения на вебинары, курсы, обучение, ссылки на каналы.
4. МУСОР — сообщения с избытком эмодзи, "привет всем", бессмысленные фразы, запросы на АСУТП или клонирование голоса.

Твой ответ должен быть СТРОГИМ JSON-объектом:
{
  "results": [
    {"id": ID, "status": 1 или 2, "reason": "краткая причина на русском"}
  ]
}
"""

async def filter_batch(batch):
    prompt = "Проанализируй эти сообщения. Укажи статус (1 - лид, 2 - спам) и краткую причину для кажного ID:\n\n"
    for item in batch:
        prompt += f"ID: {item[0]} | Текст: {item[1]}\n"
    
    # Принудительно используем локальную модель (Ollama), не отправляем в OpenRouter
    response = await llm_client._generate_ollama(settings.OLLAMA_MODEL, prompt, SYSTEM_PROMPT)
    if not response:
        return []
    
    try:
        # Ищем JSON в ответе
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return data.get("results", [])
    except Exception as e:
        logger.error(f"Ошибка парсинга ответа AI: {e}\nОтвет: {response}")
        return []

async def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ База {DB_PATH} не найдена.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем лиды, которые еще не обработаны (ai_status = 0)
    cursor.execute(f"SELECT id, text FROM {TABLE_NAME} WHERE ai_status = 0")
    leads = cursor.fetchall()
    total_leads = len(leads)
    print(f"📊 Осталось лидов на проверку: {total_leads}")

    if total_leads == 0:
        print("✅ Все лиды уже обработаны.")
        return

    for i in range(0, total_leads, BATCH_SIZE):
        batch = leads[i:i+BATCH_SIZE]
        print(f"⏳ Обработка батча {i//BATCH_SIZE + 1}/{(total_leads + BATCH_SIZE - 1)//BATCH_SIZE}...")
        
        results = await filter_batch(batch)
        
        if results:
            current_batch_ids = [item[0] for item in batch]
            for res in results:
                lead_id = res.get("id")
                status = res.get("status")
                reason = res.get("reason", "")
                
                if lead_id in current_batch_ids and status in [1, 2]:
                    cursor.execute(
                        f"UPDATE {TABLE_NAME} SET ai_status = ?, ai_reason = ? WHERE id = ?",
                        (status, reason, lead_id)
                    )
            
            # Помечаем те, что AI пропустил в этом батче, как обработанные (status-unknown или skip)
            # чтобы не зацикливаться. Но лучше просто коммитить.
            conn.commit()
            
            processed_in_batch = sum(1 for res in results if res.get("id") in current_batch_ids)
            print(f"  ✅ Обработано в батче: {processed_in_batch}/{len(batch)}")
        
        await asyncio.sleep(0.5)

    conn.close()
    print(f"🏁 ИИ-фильтрация завершена.")

if __name__ == "__main__":
    asyncio.run(main())
