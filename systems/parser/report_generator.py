import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List
from core.utils.logger import logger


class ReportGenerator:
    """Генератор ежедневных и недельных отчетов по парсингу вакансий."""
    
    def __init__(self, db_path: str = "vacancies.db"):
        self.db_path = db_path
        self.reports_dir = "reports"
        os.makedirs(f"{self.reports_dir}/daily", exist_ok=True)
        os.makedirs(f"{self.reports_dir}/weekly", exist_ok=True)
    
    def generate_daily_report(self, date: str = None) -> Dict:
        """
        Генерирует ежедневный отчет за указанную дату.
        
        Args:
            date: Дата в формате YYYY-MM-DD. Если None, используется сегодня.
        
        Returns:
            Dict с метриками и путем к файлу отчета.
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"📊 Генерация ежедневного отчета за {date}...")
        
        # Получаем данные из БД
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Начало и конец дня
        start_time = f"{date} 00:00:00"
        end_time = f"{date} 23:59:59"
        
        # Всего сообщений
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM vacancies 
            WHERE last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        total_messages = cursor.fetchone()['total']
        
        # Одобренные
        cursor.execute("""
            SELECT COUNT(*) as accepted 
            FROM vacancies 
            WHERE status = 'accepted' AND last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        accepted = cursor.fetchone()['accepted']
        
        # Отклоненные
        cursor.execute("""
            SELECT COUNT(*) as rejected 
            FROM vacancies 
            WHERE status = 'rejected' AND last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        rejected = cursor.fetchone()['rejected']
        
        # Отправленные отклики
        cursor.execute("""
            SELECT COUNT(*) as sent 
            FROM vacancies 
            WHERE response IS NOT NULL AND response != 'notified' 
            AND last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        sent_responses = cursor.fetchone()['sent']
        
        # Топ источников (чаты)
        cursor.execute("""
            SELECT source, COUNT(*) as count 
            FROM vacancies 
            WHERE last_seen >= ? AND last_seen <= ?
            GROUP BY source 
            ORDER BY count DESC 
            LIMIT 5
        """, (start_time, end_time))
        top_sources = cursor.fetchall()
        
        conn.close()
        
        # Формируем отчет
        metrics = {
            "date": date,
            "total_messages": total_messages,
            "accepted": accepted,
            "rejected": rejected,
            "sent_responses": sent_responses,
            "acceptance_rate": round((accepted / total_messages * 100) if total_messages > 0 else 0, 2),
            "response_rate": round((sent_responses / accepted * 100) if accepted > 0 else 0, 2),
            "top_sources": [{"source": row['source'], "count": row['count']} for row in top_sources]
        }
        
        # Сохраняем в файл
        report_path = f"{self.reports_dir}/daily/{date}.md"
        self._save_daily_report(metrics, report_path)
        
        logger.info(f"✅ Отчет сохранен: {report_path}")
        return {"status": "success", "metrics": metrics, "path": report_path}
    
    def _save_daily_report(self, metrics: Dict, path: str):
        """Сохраняет ежедневный отчет в Markdown."""
        content = f"""# 📊 Ежедневный отчет парсера — {metrics['date']}

## 📈 Общая статистика

- **Всего сообщений обработано**: {metrics['total_messages']}
- **✅ Одобрено вакансий**: {metrics['accepted']} ({metrics['acceptance_rate']}%)
- **❌ Отклонено (спам/нерелевантное)**: {metrics['rejected']}
- **🚀 Отправлено откликов**: {metrics['sent_responses']} ({metrics['response_rate']}% от одобренных)

## 🏆 Топ-5 источников

"""
        for i, source in enumerate(metrics['top_sources'], 1):
            content += f"{i}. **{source['source']}** — {source['count']} сообщений\n"
        
        content += f"\n---\n*Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def generate_weekly_report(self, end_date: str = None) -> Dict:
        """
        Генерирует недельный отчет (последние 7 дней от end_date).
        
        Args:
            end_date: Конечная дата в формате YYYY-MM-DD. Если None, используется сегодня.
        
        Returns:
            Dict с метриками и путем к файлу отчета.
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        end = datetime.strptime(end_date, '%Y-%m-%d')
        start = end - timedelta(days=6)
        start_date = start.strftime('%Y-%m-%d')
        
        logger.info(f"📊 Генерация недельного отчета: {start_date} — {end_date}...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        start_time = f"{start_date} 00:00:00"
        end_time = f"{end_date} 23:59:59"
        
        # Общая статистика за неделю
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM vacancies 
            WHERE last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        total_messages = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT COUNT(*) as accepted 
            FROM vacancies 
            WHERE status = 'accepted' AND last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        accepted = cursor.fetchone()['accepted']
        
        cursor.execute("""
            SELECT COUNT(*) as rejected 
            FROM vacancies 
            WHERE status = 'rejected' AND last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        rejected = cursor.fetchone()['rejected']
        
        cursor.execute("""
            SELECT COUNT(*) as sent 
            FROM vacancies 
            WHERE response IS NOT NULL AND response != 'notified' 
            AND last_seen >= ? AND last_seen <= ?
        """, (start_time, end_time))
        sent_responses = cursor.fetchone()['sent']
        
        # Разбивка по дням
        daily_breakdown = []
        for i in range(7):
            day = start + timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            day_start = f"{day_str} 00:00:00"
            day_end = f"{day_str} 23:59:59"
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM vacancies 
                WHERE last_seen >= ? AND last_seen <= ?
            """, (day_start, day_end))
            
            row = cursor.fetchone()
            daily_breakdown.append({
                "date": day_str,
                "total": row['total'] or 0,
                "accepted": row['accepted'] or 0,
                "rejected": row['rejected'] or 0
            })
        
        conn.close()
        
        metrics = {
            "period": f"{start_date} — {end_date}",
            "total_messages": total_messages,
            "accepted": accepted,
            "rejected": rejected,
            "sent_responses": sent_responses,
            "acceptance_rate": round((accepted / total_messages * 100) if total_messages > 0 else 0, 2),
            "response_rate": round((sent_responses / accepted * 100) if accepted > 0 else 0, 2),
            "daily_breakdown": daily_breakdown,
            "avg_per_day": round(total_messages / 7, 1)
        }
        
        # Сохраняем в файл
        report_path = f"{self.reports_dir}/weekly/{start_date}_to_{end_date}.md"
        self._save_weekly_report(metrics, report_path)
        
        logger.info(f"✅ Недельный отчет сохранен: {report_path}")
        return {"status": "success", "metrics": metrics, "path": report_path}
    
    def _save_weekly_report(self, metrics: Dict, path: str):
        """Сохраняет недельный отчет в Markdown."""
        content = f"""# 📊 Недельный отчет парсера — {metrics['period']}

## 📈 Общая статистика за неделю

- **Всего сообщений обработано**: {metrics['total_messages']}
- **Среднее в день**: {metrics['avg_per_day']}
- **✅ Одобрено вакансий**: {metrics['accepted']} ({metrics['acceptance_rate']}%)
- **❌ Отклонено**: {metrics['rejected']}
- **🚀 Отправлено откликов**: {metrics['sent_responses']} ({metrics['response_rate']}% от одобренных)

## 📅 Разбивка по дням

| Дата | Всего | Одобрено | Отклонено |
|------|-------|----------|-----------|
"""
        for day in metrics['daily_breakdown']:
            content += f"| {day['date']} | {day['total']} | {day['accepted']} | {day['rejected']} |\n"
        
        content += f"\n---\n*Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


# Singleton instance
report_generator = ReportGenerator()
