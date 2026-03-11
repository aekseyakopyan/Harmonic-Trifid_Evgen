import asyncio
from pyrogram import Client

api_id = 38220736
api_hash = 'dce7af9aed29a4d01de904e801fef321'

with open("data/sessions/alexey_pyrogram.txt", "r") as f:
    session_str = f.read().strip()

app = Client("my_account", api_id=api_id, api_hash=api_hash, session_string=session_str, in_memory=True)

async def main():
    async with app:
        # Search for the message text across all chats
        print("Searching for the message...")
        async for dialog in app.get_dialogs():
            if dialog.chat.title == "Чат Фриланс | Вакансии | Удаленка":
                print(f"Found chat: {dialog.chat.title} (ID: {dialog.chat.id})")
                async for msg in app.search_messages(dialog.chat.id, query="Нужен спец по сбору данных"):
                    print("MSG ID:", msg.id)
                    print("FROM_USER:", msg.from_user)
                    print("SENDER_CHAT:", msg.sender_chat)
                    print("TEXT:", msg.text)
                    print("FWD_FROM:", msg.forward_from)
                    print("---")
                    break
                break

asyncio.run(main())
