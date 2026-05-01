import os
import json
from telethon import TelegramClient, events, Button

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7b'
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7031840237
DEVELOPER_USERNAME = 'szzrc'
DEVELOPER_LINK = f'https://t.me/{DEVELOPER_USERNAME}'
REQUIRED_CHANNELS = ['hgdfghjiu']
DB_FILE = 'database.json'
BACKUP_FILE = 'sessions_backup.json'
SUB_PRICE = 3
MAX_ACCOUNTS = 1
FREE_TRIAL_DAYS = 1

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# حط باقي كود البوت بتاعك هنا كامل...

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply('البوت شغال ✅')

bot.run_until_disconnected()
