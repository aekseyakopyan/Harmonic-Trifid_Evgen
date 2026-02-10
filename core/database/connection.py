from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config.settings import settings
from core.database.models import Base

# SQLite async engine
engine = create_async_engine(
    settings.async_database_url, 
    echo=settings.DEBUG,
    connect_args={"timeout": 30}
)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Initialize database and create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    """Dependency for getting database session."""
    async with async_session() as session:
        yield session
