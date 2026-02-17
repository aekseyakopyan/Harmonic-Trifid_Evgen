#!/usr/bin/env python3
"""Тест RL Agent."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from systems.alexey.alexey_engine_rl import alexey_rl
from systems.alexey.rl_agent import rl_agent

async def test_rl():
    print("🤖 Тестирование RL Agent\n")
    
    test_lead = {
        'id': 999999,
        'text': 'Ищу SEO-специалиста для продвижения сайта. Бюджет 30к, срочно.',
        'priority': 75,
        'budget': 30000,
        'category': 'SEO',
        'tier': 'HOT'
    }
    
    print("1️⃣ Генерация отклика...")
    result = await alexey_rl.generate_outreach_with_rl(test_lead)
    
    print(f"\nСтратегия: {result['strategy_id']}")
    print(f"Outreach ID: {result['outreach_id']}")
    print(f"\nСообщение:\n{result['message']}\n")
    
    print("2️⃣ Симуляция: клиент ответил через 30 минут...")
    await alexey_rl.record_client_reply(
        outreach_id=result['outreach_id'],
        reply_received=True,
        reply_time_seconds=1800
    )
    
    print("3️⃣ Симуляция: сделка закрыта на 35k...")
    await alexey_rl.record_deal_closed(
        outreach_id=result['outreach_id'],
        conversation_length=7,
        deal_closed=True,
        deal_amount=35000
    )
    
    print("\n4️⃣ Отчет о производительности:\n")
    report = await rl_agent.get_performance_report()
    
    print(f"Всего попыток: {report['total_attempts']}")
    print(f"Лучшая стратегия: {report['best_strategy']}\n")
    
    for strategy_id, metrics in report['strategies'].items():
        print(f"{strategy_id}:")
        print(f"  Попыток: {metrics['total_attempts']}")
        print(f"  Success rate: {metrics['success_rate']:.1%}")
        print(f"  Avg reward: {metrics['avg_reward']:.3f}")
        print(f"  Confidence: {metrics['confidence']:.3f}\n")

if __name__ == "__main__":
    asyncio.run(test_rl())
