import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from systems.parser.outreach_generator import outreach_generator
from core.utils.logger import logger

async def test_heuristic():
    test_messages = [
        "Есть ли у кого-то рекомендации? Можно ли найти в этом месте тех спецы с опытом в тхх заготовках? И вопрос - никому случайно не нужен сертифицированный таргетолог?)",
        "Все еще ищешь среди мусора способ заработать? Представляем проект Morja - биржа с микрозадачами. Отзыв авито 300р",
        "Приветствую!) Меня зовут Артем, занимаюсь улучшением показателей рекламы на Авито. 1. Освобождаю Ваше время...",
        "Нужен спец по продвижению на Авито, бюджет 50к",
        "Ищу спеца по SEO для интернет-магазина",
        "Предлагаю услуги по созданию сайтов на Тильде",
        "Пишите в ЛС, настрою Директ дешево"
    ]

    print("--- TESTING HEURISTIC FILTER ---")
    for msg in test_messages:
        is_lead = await outreach_generator._ai_sanity_check(msg)
        status = "✅ LEAD" if is_lead else "❌ SPAM/SELLER"
        print(f"[{status}] {msg[:60]}...")

if __name__ == "__main__":
    asyncio.run(test_heuristic())
