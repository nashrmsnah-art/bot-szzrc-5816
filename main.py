from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityCustomEmoji

API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = '8652252025:AAHAwv5yJwlBO072El-71_SvIXhqM3m9NNc'

client = TelegramClient('session', API_ID, API_HASH)

@client.on(events.NewMessage)
async def handler(event):
    if event.message.entities:
        for ent in event.message.entities:
            if isinstance(ent, MessageEntityCustomEmoji):
                await event.reply(f"`{ent.document_id}`")
                print(f"Document ID: {ent.document_id}")

client.start(bot_token=BOT_TOKEN)
print("ابعت الايموجي للبوت دلوقتي...")
client.run_until_disconnected()
