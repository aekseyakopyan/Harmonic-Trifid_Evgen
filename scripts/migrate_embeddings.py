#!/usr/bin/env python3
import sys, asyncio
sys.path.insert(0, ".")
from systems.parser.duplicate_detector import get_duplicate_detector
from systems.parser.vacancy_db import VacancyDatabase
from datetime import datetime, timedelta

async def migrate():
    db = VacancyDatabase()
    detector = get_duplicate_detector(db_manager=db)
    
    print("🔄 Checking for leads without embeddings...")
    
    total_processed = 0
    batch_size = 100  # Process in smaller chunks to show progress
    
    while True:
        # Get leads specifically missing embeddings
        leads_to_process = await asyncio.to_thread(db.get_leads_without_embeddings, batch_size)
        
        if not leads_to_process:
            if total_processed == 0:
                print("✅ No leads need migration (all have embeddings).")
            else:
                print(f"✅ Migration complete. Total processed: {total_processed}")
            break

        print(f"🔄 Processing batch of {len(leads_to_process)} leads...")
        processed = await detector.precompute_embeddings_batch(leads_to_process, batch_size=batch_size)
        total_processed += processed
        print(f"   Batch complete. Total so far: {total_processed}")

if __name__ == "__main__":
    asyncio.run(migrate())
