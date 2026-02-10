import asyncio
import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ai_engine.prompt_builder import prompt_builder
from core.ai_engine.llm_client import llm_client

async def test_personality():
    print("--- Тестирование новой личности Алексея ---")
    
    test_cases = [
        {
            "user_name": "Тимофей",
            "query": "Привет! Расскажи, чем занимаешься?",
            "expected": "Должен поприветствовать по имени и кратко рассказать о себе."
        },
        {
            "user_name": "Тимофей",
            "query": "Слушай, а как приготовить вкусный борщ?",
            "expected": "Должен признать незнание темы и перевести разговор на маркетинг."
        },
        {
            "user_name": "Алексей",
            "query": "Нужен SEO аудит сайта. Сколько стоит?",
            "expected": "Должен поприветствовать, дать вилку цен и задать уточняющий вопрос."
        }
    ]
    
    for case in test_cases:
        print(f"\n[ТЕСТ] Пользователь: {case['user_name']}, Запрос: '{case['query']}'")
        
        # Строим промпт
        system_prompt = prompt_builder.build_system_prompt()
        user_prompt = prompt_builder.build_user_prompt(
            query=case['query'],
            user_name=case['user_name'],
            cases=[],
            history_text=""
        )
        
        print(f"Промпт содержит имя: {'ДА' if case['user_name'] in user_prompt else 'НЕТ'}")
        
        # Генерируем ответ
        print("Генерация ответа ИИ...")
        response = await llm_client.generate_response(user_prompt, system_prompt)
        
        print("-" * 50)
        print(f"ОТВЕТ АЛЕКСЕЯ:\n{response}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_personality())
