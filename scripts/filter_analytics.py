
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

class FilterAnalytics:
    """
    Аналитика работы фильтра.
    """
    
    def __init__(self, db_path: str = "vacancies.db"):
        self.db_path = db_path
    
    def get_filter_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Статистика за последние N дней.
        """
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        # Общая статистика
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM vacancies 
            WHERE last_seen > ?
            GROUP BY status
        """, (cutoff_str,))
        
        status_counts = dict(cursor.fetchall())
        
        # Причины отклонения
        cursor.execute("""
            SELECT rejection_reason, COUNT(*) 
            FROM vacancies 
            WHERE last_seen > ? AND status = 'rejected'
            GROUP BY rejection_reason
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """, (cutoff_str,))
        
        rejection_reasons = dict(cursor.fetchall())
        
        # Источники
        cursor.execute("""
            SELECT source, status, COUNT(*) 
            FROM vacancies 
            WHERE last_seen > ?
            GROUP BY source, status
        """, (cutoff_str,))
        
        source_breakdown = cursor.fetchall()
        
        conn.close()
        
        total = sum(status_counts.values())
        accept_rate = status_counts.get('accepted', 0) / total if total > 0 else 0
        
        return {
            "period_days": days,
            "total": total,
            "accepted": status_counts.get('accepted', 0),
            "rejected": status_counts.get('rejected', 0),
            "other": total - status_counts.get('accepted', 0) - status_counts.get('rejected', 0),
            "accept_rate": accept_rate,
            "rejection_reasons": rejection_reasons,
            "source_breakdown": source_breakdown,
        }
    
    def print_report(self, days: int = 7):
        """
        Печатает отчёт.
        """
        stats = self.get_filter_stats(days)
        
        if "error" in stats:
            print(f"❌ Error: {stats['error']}")
            return

        print(f"\n📊 FILTER ANALYTICS (последние {days} дней)\n")
        print(f"Всего обработано: {stats['total']}")
        print(f"✅ Принято:      {stats['accepted']} ({stats['accept_rate']:.1%})")
        print(f"❌ Отклонено:    {stats['rejected']}")
        if stats['other'] > 0:
            print(f"❓ Другое:       {stats['other']}")
            
        print(f"\n🔝 Топ причин отклонения:")
        for reason, count in list(stats['rejection_reasons'].items())[:5]:
            print(f"  - {reason}: {count}")
        
        print(f"\n🌐 Топ источников (ACCEPTED):")
        sources = {}
        for row in stats['source_breakdown']:
            source, status, count = row
            if status == 'accepted':
                sources[source] = count
        
        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        for source, count in sorted_sources[:5]:
            print(f"  - {source}: {count}")
        print("\n")

if __name__ == "__main__":
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
            
    analytics = FilterAnalytics()
    analytics.print_report(days=days)
