# Get Krypton alerts on your phone (Telegram, free, ~5 minutes)

Telegram lets programs send you messages through a "bot". You create the bot yourself
in the Telegram app; Krypton then uses it to message only you.

## 1. Create your bot
1. In Telegram, search for **@BotFather** (blue tick) and open a chat.
2. Send `/newbot`, pick a name (e.g. *My Krypton*) and a username ending in `bot`.
3. BotFather replies with a **token** (looks like `123456789:ABC-...`). Keep it private.

## 2. Find your chat ID
1. Open a chat with your new bot and send it any message (e.g. "hi").
2. In a browser, open (replace `<TOKEN>` with your token):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find `"chat":{"id":` followed by a number. That number is your **chat ID**.

## 3. Save both on this PC
In PowerShell (paste your own values):

```powershell
setx TELEGRAM_BOT_TOKEN "your-token-here"
setx TELEGRAM_CHAT_ID "your-chat-id-here"
```

Close and reopen the terminal, then restart Krypton and the alert watcher.
In the 🔔 Alerts tab, make sure "Telegram messages to my phone" is switched on.
