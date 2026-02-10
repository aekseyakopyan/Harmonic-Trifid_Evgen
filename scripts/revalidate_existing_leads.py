
import asyncio
import sqlite3
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from systems.parser.lead_filter_advanced import filter_lead_advanced

async def revalidate_database(db_path: str = "vacancies.db", limit: int = None):
    """
    Перепрогоняет всю базу через новый фильтр.
    """
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Выбираем все accepted (чтобы перепроверить)
    query = "SELECT hash, text, source, direction FROM vacancies WHERE status = 'accepted'"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"🔄 Revalidating {len(rows)} accepted leads...")
    
    updated = 0
    rejected = 0
    
    for row in rows:
        hash_id, text, source, direction = row
        
        # Check if source or direction are None to avoid errors
        source = source or ""
        direction = direction or ""
        
        result = await filter_lead_advanced(text, source, direction, use_llm_for_uncertain=True)
        
        if not result["is_lead"]:
            # Отклоняем
            cursor.execute("""
                UPDATE vacancies 
                SET status = 'rejected', 
                    rejection_reason = ? 
                WHERE hash = ?
            """, (f"ADVANCED_FILTER: {result['reason']}", hash_id))
            rejected += 1
            print(f"❌ REJECT: {hash_id[:8]} - {result['reason']}")
        else:
            updated += 1
            print(f"✅ KEEP: {hash_id[:8]} - confidence={result['confidence']}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Done! Keep: {updated}, Rejected: {rejected}")

if __name__ == "__main__":
    limit = 100 # Default limit for safety
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
            
    asyncio.run(revalidate_database(limit=limit))
