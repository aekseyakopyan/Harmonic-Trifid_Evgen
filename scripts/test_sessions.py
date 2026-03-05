import asyncio
import os
from pyrogram import Client
from core.config.settings import settings

async def test_session(name, session_string=None):
    print(f"\n--- Testing: {name} ---")
    try:
        if session_string:
            app = Client(
                name="test_session",
                api_id=settings.TELEGRAM_API_ID,
                api_hash=settings.TELEGRAM_API_HASH,
                session_string=session_string,
                in_memory=True
            )
        else:
            # name here is the path to .session file
            app = Client(
                name=name,
                api_id=settings.TELEGRAM_API_ID,
                api_hash=settings.TELEGRAM_API_HASH,
                workdir="."
            )
        
        async with app:
            me = await app.get_me()
            print(f"✅ SUCCESS: Authorized as {me.first_name}")
            return True
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

async def main():
    # 1. Test strings
    strings = [
        "data/sessions/session_string_final.txt",
        "data/sessions/session_string_debug.txt",
        "data/sessions/session_string.txt"
    ]
    for s_path in strings:
        if os.path.exists(s_path):
            with open(s_path, "r") as f:
                s_str = f.read().strip()
                if s_str:
                    await test_session(s_path, s_str)

    # 2. Test files
    files = [
        "data/sessions/userbot_session",
        "data/sessions/parser_session",
        "data/sessions/joiner_session"
    ]
    for f_path in files:
        if os.path.exists(f_path + ".session"):
            await test_session(f_path)

if __name__ == "__main__":
    asyncio.run(main())
