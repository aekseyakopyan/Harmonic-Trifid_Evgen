import asyncio
from sqlalchemy import select, func
from core.database.connection import async_session
from core.database.models import Lead, MessageLog

async def check_data():
    async with async_session() as session:
        # Check Leads
        result = await session.execute(select(Lead))
        leads = result.scalars().all()
        print(f"Leads found: {len(leads)}")
        for lead in leads:
            print(f" - {lead.id}: {lead.full_name} ({lead.telegram_id})")
            
        # Check Messages
        result = await session.execute(select(MessageLog))
        messages = result.scalars().all()
        print(f"Messages found: {len(messages)}")
        for msg in messages:
            print(f" - [{msg.direction}] {msg.content[:30]}...")

if __name__ == "__main__":
    asyncio.run(check_data())
