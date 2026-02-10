import asyncio
from core.database.connection import init_db, engine, async_session
from core.database.models import Lead, MessageLog
from datetime import datetime, timedelta

async def seed_data():
    print("🚀 Initializing database...")
    await init_db()
    
    async with async_session() as session:
        # Check if we already have data
        from sqlalchemy import select
        result = await session.execute(select(Lead))
        if result.scalars().first():
            print("✨ Database already has data. Skipping seeding.")
            return

        print("📝 Seeding mock data...")
        
        # Create mock leads
        leads = [
            Lead(
                telegram_id=12345678,
                username="ivan_pro",
                full_name="Иван Петров",
                lead_score=8.5,
                last_interaction=datetime.utcnow() - timedelta(minutes=15)
            ),
            Lead(
                telegram_id=87654321,
                username="sveta_marketing",
                full_name="Светлана Соколова",
                lead_score=5.2,
                last_interaction=datetime.utcnow() - timedelta(hours=2)
            ),
            Lead(
                telegram_id=11223344,
                username="seo_master",
                full_name="Алексей Мастер",
                lead_score=9.1,
                last_interaction=datetime.utcnow() - timedelta(days=2)
            )
        ]
        
        session.add_all(leads)
        await session.commit()
        
        # Reload leads to get IDs
        result = await session.execute(select(Lead))
        db_leads = result.scalars().all()
        
        # Create mock messages
        messages = []
        for lead in db_leads:
            messages.append(MessageLog(
                lead_id=lead.id,
                direction="incoming",
                content=f"Привет! Мне нужны услуги по {['SEO', 'Авито', 'Директу'][lead.id % 3]}",
                created_at=lead.last_interaction - timedelta(minutes=5)
            ))
            messages.append(MessageLog(
                lead_id=lead.id,
                direction="outgoing",
                content="Здравствуйте! Да, мы как раз этим занимаемся. У нас есть отличные кейсы.",
                created_at=lead.last_interaction
            ))
            
        session.add_all(messages)
        await session.commit()
        
    print("✅ Database initialized and seeded with mock data.")

if __name__ == "__main__":
    asyncio.run(seed_data())
