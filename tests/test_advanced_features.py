
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from systems.parser.lead_filter_advanced import filter_lead_advanced

async def test_all():
    test_cases = [
        {
            "text": "Нужен специалист по SEO для продвижения интернет-магазина. Бюджет 50000 руб. Срочно!",
            "source": "Разработка и IT - Kwork фриланс заказы",
            "direction": "SEO"
        },
        {
            "text": "Привет! Я таргетолог, настрою вам рекламу. Пишите в ЛС.",
            "source": "ФРИЛАНС | ВАКАНСИИ INSTAGRAM",
            "direction": "таргетированная реклама"
        },
        {
            "text": "Нужен спец по авито, бюджет 5к",
            "source": "Таргет | Арбитраж | Вакансии",
            "direction": "авито"
        }
    ]

    print("--- TESTING ADVANCED FILTER ---")
    for case in test_cases:
        print(f"\nProcessing: {case['text'][:50]}...")
        result = await filter_lead_advanced(case['text'], case['source'], case['direction'], use_llm_for_uncertain=False)
        
        status = "✅ LEAD" if result['is_lead'] else "❌ REJECT"
        print(f"Result: {status} | Stage: {result['stage']} | Reason: {result['reason']}")
        
        if result['is_lead']:
            print(f"Priority: {result['priority']} ({result['tier']})")
            print(f"Factors: {result['priority_factors']}")
            if 'entities' in result:
                print(f"Budget: {result['entities']['budget']}")
                print(f"Contacts: {result['entities']['contact']['has_contact']}")

if __name__ == "__main__":
    asyncio.run(test_all())
