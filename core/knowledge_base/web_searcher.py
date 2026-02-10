import asyncio
from typing import List, Dict
from duckduckgo_search import DDGS
from core.utils.logger import logger

class WebSearcher:
    """
    Class for searching external case studies and market examples.
    """
    def __init__(self):
        self.ddgs = DDGS()

    async def search_cases(self, niche: str, service: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Search for cases in a specific niche and service limited to 2024-2025.
        """
        query = f"кейс {service} {niche} результаты 2024 2025"
        logger.info(f"Searching web for: {query}")
        
        try:
            # Running in a thread pool as ddgs might be blocking or not fully async-native in some versions
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self._sync_search, query, limit)
            return results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    def _sync_search(self, query: str, limit: int) -> List[Dict[str, str]]:
        search_results = self.ddgs.text(query, max_results=limit)
        cases = []
        for r in search_results:
            cases.append({
                "title": r.get("title", "Без названия"),
                "description": r.get("body", ""),
                "url": r.get("href", "")
            })
        return cases

# Singleton instance
web_searcher = WebSearcher()
