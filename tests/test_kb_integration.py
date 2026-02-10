import asyncio
import os
import sys

# Добавляем корень проекта в путь
sys.path.append(os.getcwd())

from core.knowledge_base.retriever import KnowledgeRetriever
from core.database.connection import async_session

async def test_search():
    print("--- ТЕСТ ПОИСКА ПО БАЗЕ ЗНАНИЙ (MARKDOWN) ---")
    
    async with async_session() as session:
        retriever = KnowledgeRetriever(session)
        
        # Тест 1: Поиск по принципам (B2B)
        query_1 = "B2B продажи в Telegram"
        print(f"\nПоиск по запросу: '{query_1}'")
        results_1 = await retriever.search_markdown_kb(query_1)
        for r in results_1:
            print(f"- Найдено в: {r['source']} (Score: {r['score']})")
            print(f"  Сниппет: {r['content'][:150]}...")

        # Тест 2: Поиск по работе с ценой
        query_2 = "Как отвечать на вопрос сколько стоит"
        print(f"\nПоиск по запросу: '{query_2}'")
        results_2 = await retriever.search_markdown_kb(query_2)
        for r in results_2:
            print(f"- Найдено в: {r['source']} (Score: {r['score']})")
            
        # Тест 3: Поиск по мягким CTA
        query_3 = "мягкий CTA и дожим"
        print(f"\nПоиск по запросу: '{query_3}'")
        results_3 = await retriever.search_markdown_kb(query_3)
        for r in results_3:
            print(f"- Найдено в: {r['source']} (Score: {r['score']})")

    print("\n--- ТЕСТ ЗАВЕРШЕН ---")

if __name__ == "__main__":
    asyncio.run(test_search())
