"""
auth_pyrogram.py — Автоматизированная авторизация Pyrogram с номером из .env.
Читает код из stdin (позволяет передать через pipe).
"""
import asyncio
import os
import sys
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")


async def main():
    print(f"Авторизация Pyrogram для: {PHONE}")
    
    app = Client(
        name="temp_auth",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE,
        in_memory=True
    )

    await app.connect()
    
    sent_code = await app.send_code(PHONE)
    print(f"📱 КОД ОТПРАВЛЕН на {PHONE}")
    print("Введите код из Telegram: ", end="", flush=True)
    
    code = input().strip()
    
    try:
        await app.sign_in(PHONE, sent_code.phone_code_hash, code)
    except Exception as e:
        if "PASSWORD" in str(e).upper() or "two" in str(e).lower():
            print("Введите пароль 2FA: ", end="", flush=True)
            password = input().strip()
            await app.check_password(password)
        else:
            raise

    session_string = await app.export_session_string()
    me = await app.get_me()
    print(f"\n✅ Авторизован: {me.first_name} (@{me.username}) ID={me.id}")

    await app.disconnect()

    os.makedirs("data/sessions", exist_ok=True)
    with open("data/sessions/alexey_pyrogram.txt", "w") as f:
        f.write(session_string)
    print("💾 Session сохранена в data/sessions/alexey_pyrogram.txt")


if __name__ == "__main__":
    asyncio.run(main())
