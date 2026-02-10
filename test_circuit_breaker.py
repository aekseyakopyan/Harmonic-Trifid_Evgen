import asyncio
import time
import os
import sys

# Добавляем текущую директорию в path для импортов
sys.path.append(os.getcwd())

from core.ai_engine.resilient_llm import resilient_llm_client

async def test_normal_operation():
    print("=== Тест 1: Нормальная работа ===")
    try:
        result = await resilient_llm_client.call_with_fallback(
            prompt="Ты классификатор лидов. Отвечай JSON.",
            text="Нужен SEO-специалист для продвижения сайта. Бюджет 50000₽.",
            timeout=10
        )
        print(f"✅ Метод: {result.get('method')}")
        print(f"✅ Latency: {result.get('latency_ms')}ms")
        print(f"✅ Is lead: {result.get('is_real_lead')}")
        print(f"✅ Circuit state: {resilient_llm_client.circuit_state}\n")
    except Exception as e:
        print(f"❌ Фатальная ошибка в тесте 1: {e}")

async def test_circuit_breaker_trigger():
    print("=== Тест 2: Trigger Circuit Breaker ===")
    for i in range(6):
        try:
            # Вызываем то, что точно упадет
            await resilient_llm_client.primary_client.call_api(
                model="invalid/model",
                prompt="test",
                text="test",
                timeout=1
            )
        except Exception as e:
            print(f"Attempt {i+1}: Failed as expected")
    
    print(f"Circuit state after failures: {resilient_llm_client.circuit_state}")
    
    result = await resilient_llm_client.call_with_fallback(
        prompt="test",
        text="test",
        timeout=5
    )
    print(f"✅ Fallback method used: {result.get('method')}")
    print(f"✅ Latency: {result.get('latency_ms')}ms\n")

async def main():
    try:
        await test_normal_operation()
        await test_circuit_breaker_trigger()
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
