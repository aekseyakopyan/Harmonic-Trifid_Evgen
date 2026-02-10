#!/usr/bin/env python3
import sys, asyncio
sys.path.insert(0, ".")
from systems.parser.duplicate_detector import get_duplicate_detector
from systems.parser.vacancy_db import VacancyDatabase
from datetime import datetime, timedelta

async def migrate():
    db = VacancyDatabase()
    detector = get_duplicate_detector(db_manager=db)
    
    cutoff = datetime.now() - timedelta(days=30)
    leads = await asyncio.to_thread(db.get_leads_since, cutoff)
    
    # Filter leads that don't have embeddings yet (optimization)
    leads_to_process = [l for l in leads if not l.embedding]
    
    if not leads_to_process:
        print("✅ No leads need migration (all have embeddings).")
        return

    print(f"🔄 Starting migration for {len(leads_to_process)} leads...")
    processed = await detector.precompute_embeddings_batch(leads_to_process, batch_size=32)
    print(f"✅ Migration complete. Processed: {processed}/{len(leads_to_process)}")

if __name__ == "__main__":
    asyncio.run(migrate())
