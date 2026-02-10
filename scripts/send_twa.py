import os
import sys
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

TOKEN = os.getenv("SUPERVISOR_BOT_TOKEN")
CHAT_ID = os.getenv("SUPERVISOR_CHAT_ID")
API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

def send_webapp_button():
    if not TOKEN or not CHAT_ID:
        print("❌ Ошибка: В .env не найден SUPERVISOR_BOT_TOKEN или SUPERVISOR_CHAT_ID")
        return

    # Get URL from user input
    if len(sys.argv) > 1:
        webapp_url = sys.argv[1]
    else:
        print("\n🔵 Введите HTTPS ссылку на веб-апп (например, из ngrok):")
        print("   Пример: https://a1b2-c3d4.ngrok-free.app/twa")
        webapp_url = input("🔗 URL: ").strip()

    if not webapp_url.startswith("https://"):
        print("⚠️ Внимание: Telegram требует HTTPS! Ссылка должна начинаться с https://")
        return

    # Payload with Inline Keyboard
    payload = {
        "chat_id": CHAT_ID,
        "text": (
            "<b>🎛 Панель управления (Local Dashboard)</b>\n\n"
            "Нажмите кнопку ниже, чтобы открыть интерфейс управления лидами и парсером.\n"
            "<i>Работает через TWA (Telegram Web App)</i>"
        ),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "📱 Открыть Dashboard", "web_app": {"url": webapp_url}}
            ]]
        }
    }

    print(f"🚀 Отправляю кнопку на {CHAT_ID}...")
    try:
        response = requests.post(API_URL, json=payload)
        data = response.json()
        
        if data.get("ok"):
            print("✅ Сообщение успешно отправлено! Проверьте личку с ботом.")
        else:
            print(f"❌ Ошибка Telegram API: {data.get('description')}")
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

if __name__ == "__main__":
    send_webapp_button()
