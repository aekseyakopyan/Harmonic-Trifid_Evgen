---
description: How to setup and verify the Telegram Web App Dashboard
---

# TWA Dashboard Setup Guide

This guide explains how to launch and connect your Telegram Web App dashboard.

### 1. Start the Local Server
Run the dashboard server (if not already running):
```bash
./run_dashboard.sh
```
This starts the backend on `http://localhost:8000`.

### 2. Create HTTPS Tunnel (Required by Telegram)
Telegram only allows Web Apps over HTTPS. Use `ngrok` to create a secure tunnel to your local server.

In a **new terminal window**:
```bash
ngrok http 8000
```
Copy the `https://...` URL from the output (e.g., `https://a1b2-c3d4.ngrok-free.app`).

### 3. Send Web App Button to Yourself
Use the helper script to send a button that opens the dashboard directly in Telegram.

In a terminal:
```bash
# Replace with your actual ngrok URL
python3 scripts/send_twa.py https://YOUR-NGROK-URL.ngrok-free.app/twa
```

### 4. Verify in Telegram
1. Open your chat with the bot (`@YOUR_BOT_USERNAME`).
2. You should see a message with a button "📱 Открыть Dashboard".
3. Click it. The dashboard should open inside Telegram.

### 5. (Optional) Make Button Permanent via BotFather
To add a permanent "Menu" button to your bot:
1. Open [@BotFather](https://t.me/BotFather).
2. Send `/mybots` -> Select your bot.
3. Go to **Bot Settings** -> **Menu Button** -> **Configure Menu Button**.
4. Send the URL: `https://YOUR-NGROK-URL.ngrok-free.app/twa`
5. Enter title: `Dashboard`

Now users will always see the button next to the input field.
