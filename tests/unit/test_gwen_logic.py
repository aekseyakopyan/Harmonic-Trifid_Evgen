import asyncio
import os
import sys

# Добавляем корневую директорию в путь
sys.path.append(os.getcwd())

from systems.gwen.gwen_supervisor import gwen_supervisor

async def test():
    print("--- ТЕСТ ГВЕН ---")
    
    # 1. Техническое сообщение (должно быть заблокировано быстрой проверкой)
    print("\n1. Техническое (Error 502):")
    res1 = await gwen_supervisor.check_message("System error: 502 Bad Gateway. Traceback: line 42")
    print(f"Verdict: {res1['verdict']} | Reason: {res1['reason']}")
    
    # 2. Обычное сообщение (должно быть разрешено)
    print("\n2. Обычное (Привет):")
    res2 = await gwen_supervisor.check_message("Привет! Как дела? Все готово к работе.")
    print(f"Verdict: {res2['verdict']} | Reason: {res2['reason']}")
    
    # 3. Сообщение с кодом (должно быть заблокировано)
    print("\n3. С кодом (JSON):")
    res3 = await gwen_supervisor.check_message("Вот твой объект: {'status': 'ok', 'data': [1,2,3]}")
    print(f"Verdict: {res3['verdict']} | Reason: {res3['reason']}")

if __name__ == "__main__":
    asyncio.run(test())
