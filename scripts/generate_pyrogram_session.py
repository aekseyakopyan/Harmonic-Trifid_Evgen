"""
generate_pyrogram_session.py — Генерация Pyrogram StringSession.

Запустите этот скрипт ОДИН РАЗ для авторизации:
  python3 generate_pyrogram_session.py

Введете номер телефона и SMS-код. Скрипт сохранит session string в:
  data/sessions/alexey_pyrogram.txt

После этого перезапустите систему через ./start_all.sh
"""
import asyncio
import os
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")


async def main():
    print("=" * 50)
    print("Генератор Pyrogram StringSession")
    print("=" * 50)
    print(f"API_ID: {API_ID}")
    print(f"API_HASH: {API_HASH[:8]}...")
    print()

    # Временный клиент для получения session string
    app = Client(
        name="temp_auth",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True
    )

    async with app:
        session_string = await app.export_session_string()
        me = await app.get_me()
        print(f"\n✅ Авторизован как: {me.first_name} (@{me.username})")
        print(f"   ID: {me.id}")

    # Сохраняем session string
    os.makedirs("data/sessions", exist_ok=True)
    session_path = "data/sessions/alexey_pyrogram.txt"
    with open(session_path, "w") as f:
        f.write(session_string)

    print(f"\n💾 Session string сохранена в: {session_path}")
    print("\n🚀 Теперь можно перезапустить систему: ./stop_all.sh && ./start_all.sh")
    print("   Повторная авторизация больше не потребуется!")


if __name__ == "__main__":
    asyncio.run(main())
