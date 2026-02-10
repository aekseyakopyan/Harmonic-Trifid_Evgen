import json
import asyncio
import os
import sys
import re

# Add project root to path
sys.path.append(os.getcwd())

from core.ai_engine.llm_client import llm_client

async def filter_leads():
    json_path = "vacancies_2026-02-09_monitor.json"
    if not os.path.exists(json_path):
        print(f"File {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Re-filtering everything (both relevant and first 100 irrelevant)
    all_messages = []
    all_messages.extend(data.get("relevant_vacancies", []))
    all_messages.extend(data.get("irrelevant_messages", [])[:100])
    
    print(f"Analyzing {len(all_messages)} messages with EXTREME STRICT filter...")
    
    true_leads = []
    
    for msg in all_messages:
        text = msg.get("full_text") or msg.get("text")
        if not text: continue
        
        prompt = f"""
Проанализируй текст сообщения из Telegram-чата. Это должен быть ЗАПРОС НА ВЫПОЛНЕНИЕ РАБОТЫ от реального клиента.

is_real_lead = true (КВАЛИФИЦИРОВАННЫЙ):
1. ЗАКАЗЧИК: "нужен", "ищу спеца", "есть задача", "кто сделает?".
2. Ниша: Маркетинг, SEO, Директ, Авито, сайты.

is_real_lead = false (БРАК):
- ПРЕДЛОЖЕНИЕ УСЛУГ (Автор сам исполнитель): "я спец", "настрою", "портфолио", "кейсы", "предлагаю услуги".
- ЗАДАНИЯ ЗА КОПЕЙКИ: "написать отзыв", "оставить оценку".
- СПАМ/РЕКЛАМА/КУРСЫ.

Текст сообщения:
---
{text}
---

Ответь строго в формате JSON:
{{
  "is_real_lead": true,
  "role": "CLIENT",
  "reason": "краткое пояснение"
}}
"""
        response = await llm_client.generate_response(prompt, "Ты — экспертный фильтр лидов. Отвечай только валидным JSON.")
        
        # Clean up
        response = response.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                is_valid = data.get("is_real_lead", False)
                role = data.get("role")
                reason = data.get("reason")
                
                print(f"[{'✅' if is_valid else '❌'}] Role: {role} | Reason: {reason} | Text: {text[:50]}...")
                
                if is_valid and role == "CLIENT":
                    msg['alexey_role'] = role
                    msg['alexey_reason'] = reason
                    true_leads.append(msg)
            except Exception as e:
                print(f"⚠️ Error decoding JSON: {e}")
        else:
            print(f"⚠️ Failed to parse AI response for: {text[:50]}...")

    output_path = "vetted_leads_alexey.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(true_leads, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone! Found {len(true_leads)} qualified leads. Saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(filter_leads())
