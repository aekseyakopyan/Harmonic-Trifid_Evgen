
import sqlite3
import aiohttp
import os
from typing import Dict, Any

class LeadWorkflow:
    """
    Автоматические действия с лидами.
    """
    
    @staticmethod
    async def auto_process_lead(lead_data: Dict[str, Any], db_path: str = "vacancies.db"):
        """
        Автоматическая обработка лида в зависимости от tier.
        """
        tier = lead_data.get("tier", "COLD")
        priority = lead_data.get("priority", 50)
        hash_id = lead_data.get("hash")
        
        if tier == "HOT" and priority >= 80:
            # Горячий лид — генерируем отклик немедленно
            await LeadWorkflow.generate_draft_immediately(hash_id, lead_data)
            await LeadWorkflow.send_notification(lead_data, "🔥 HOT LEAD!")
        
        elif tier == "WARM":
            # Тёплый — уведомляем, но не генерируем лид сразу (или по вашему выбору)
            await LeadWorkflow.send_notification(lead_data, "⚠️ WARM LEAD")
    
    @staticmethod
    async def generate_draft_immediately(hash_id: str, lead_data: Dict[str, Any]):
        """
        Генерирует черновик отклика для горячего лида.
        """
        try:
            from systems.parser.outreach_generator import outreach_generator
            
            text = lead_data["text"]
            direction = lead_data["direction"]
            
            draft = await outreach_generator.generate_draft(text, direction, is_old=False)
            if draft:
                outreach_generator.save_draft(hash_id, draft)
                print(f"✅ Draft generated for HOT lead: {hash_id[:8]}")
        except Exception as e:
            print(f"Error generating immediate draft: {e}")
    
    @staticmethod
    async def send_notification(lead_data: Dict[str, Any], message: str):
        """
        Отправляет уведомление в Telegram (заглушка/пример).
        """
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_ADMIN_ID")
        
        if not bot_token or not chat_id:
            # print(f"Notification (no config): {message} - {lead_data['hash'][:8]}")
            return
            
        text_preview = lead_data["text"][:200]
        priority = lead_data.get("priority", 0)
        
        notification_text = f"<b>{message}</b>\n\n🎯 Приоритет: {priority}\n📝 Текст: {text_preview}...\n\nНаправление: {lead_data.get('direction')}\nИсточник: {lead_data.get('source')}"
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={
                    "chat_id": chat_id,
                    "text": notification_text,
                    "parse_mode": "HTML"
                }) as resp:
                    if resp.status != 200:
                        print(f"Failed to send TG notification: {await resp.text()}")
        except Exception as e:
            print(f"Error sending TG notification: {e}")
