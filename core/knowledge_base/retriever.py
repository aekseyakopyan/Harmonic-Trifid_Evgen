from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.models import Case, Service, FAQ

class KnowledgeRetriever:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_relevant_cases(self, query: str, limit: int = 3) -> List[Case]:
        # Simple text-based search for MVP. 
        # In a real scenario, this would use vector search / embeddings.
        keywords = query.lower().split()
        if not keywords:
            return []

        # Search in title, category, and description
        stmt = select(Case).where(Case.is_active == True)
        
        # Build conditions for each keyword
        conditions = []
        for kw in keywords:
            if len(kw) < 3: continue
            conditions.append(Case.title.ilike(f"%{kw}%"))
            conditions.append(Case.category.ilike(f"%{kw}%"))
            conditions.append(Case.description.ilike(f"%{kw}%"))
        
        if conditions:
            stmt = stmt.where(or_(*conditions))
        
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_service_by_category(self, category: str) -> Optional[Service]:
        stmt = select(Service).where(Service.name.ilike(f"%{category}%"))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def find_faq(self, question: str) -> List[FAQ]:
        keywords = question.lower().split()
        if not keywords:
            return []
            
        stmt = select(FAQ)
        conditions = []
        for kw in keywords:
            if len(kw) < 3: continue
            conditions.append(FAQ.question.ilike(f"%{kw}%"))
        
        if conditions:
            stmt = stmt.where(or_(*conditions))
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_markdown_kb(self, query: str, limit: int = 2) -> List[dict]:
        """Search through .md files in the knowledge base directory."""
        import os
        from core.config.settings import settings
        
        kb_path = os.path.join(settings.BASE_DIR, "core", "knowledge_base")
        results = []
        
        if not os.path.exists(kb_path):
            return []
            
        keywords = [k.lower() for k in query.split() if len(k) > 3]
        if not keywords:
            return []
            
        for filename in os.listdir(kb_path):
            if filename.endswith(".md"):
                file_path = os.path.join(kb_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Simple keyword counting for relevance
                        score = sum(1 for kw in keywords if kw in content.lower())
                        
                        if score > 0:
                            # Extract a snippet around the first match
                            idx = content.lower().find(keywords[0])
                            start = max(0, idx - 200)
                            end = min(len(content), idx + 800)
                            snippet = content[start:end]
                            
                            results.append({
                                "source": filename,
                                "content": snippet,
                                "score": score
                            })
                except Exception:
                    continue
        
        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
