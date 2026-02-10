from sqlalchemy.ext.asyncio import AsyncSession
from core.database.connection import async_session

async def get_db():
    """Dependency for getting database session"""
    async with async_session() as session:
        yield session
