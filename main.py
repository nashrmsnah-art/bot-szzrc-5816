import os, asyncio, aiohttp, datetime, io, re
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageEntityCustomEmoji, KeyboardButtonCallback, ReplyInlineMarkup, KeyboardButtonRow
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import style
from dotenv import load_dotenv

DEV_ID = 154919127
DEV_USERNAME = "Devazf"
MY_WALLET = "UQAiD3sTRHpH97N9Tg8RSydsl7DL-iLR_GB9RLNkXaRL0Pao"

# ايموجي بريميوم
EMOJI_TON = 5465167687347457679
EMOJI_DOLLAR = 5465275063733820542
EMOJI_CHART = 5341837545323734099
EMOJI_LINK = 5348400065337151036
EMOJI_FROG = 5384636646954847260
EMOJI_PHONE = 5341509066345594447
EMOJI_CARD = 5377490785235135237
EMOJI_FIRE = 5465466366967323446
EMOJI_BELL = 5463101668289519385
EMOJI_WALLET = 5461121042872574248
EMOJI_USERS = 5469986292290887040
EMOJI_NUMBERS = 5467860858070661953
EMOJI_ROCKET = 5461139466883749824

RATES = {"USD_EGP": 48.6, "USD_IQD": 1310, "USD_ASIA": 1320, "USD_ZAIN": 1325, "USD_MASTER": 1340}

cache = {
    "ton_usd": 0,
    "last_update": 0,
    "chart_7d": [],
    "chart_24h": [],
    "stats": {"ton": 0, "usd": 0, "asia": 0, "zain": 0, "master": 0, "egp": 0, "iqd": 0},
    "alerts": {},
}

DEMO_USERS = ["@pornvideos_xxxvideos_sexvideoss", "@catman @kino @wealth @openai", "@soccer @basketball @ethe @bitc", "@token @weber @xxxx @musk", "@cryptos @leak @v2rayfree", "@proxyfree @mtprotofree @jenner", "@holly"]
DEMO_NUMBERS = ["+88801731085", "+88803652507", "+88806435141", "+88803215796", "+88805071929", "+88803246960", "+88803953260", "+88809436252", "+88802135196", "+88805050707", "+88805050707", "+88805050707", "+88802010652", "+8888066", "+88802431065", "+88805201314"]

style.use('dark_background')

async def update_rates_auto():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
                async with session.get(url, timeout=5) as r:
                    data = await r.json()
                    cache["ton_usd"] = float(data["price"])
                    cache["last_update"] = asyncio.get_event_loop().time()

                url = "https://api.exchangerate-api.com/v4/latest/USD"
                async with session.get(url, timeout=5) as r:
                    data = await r.json()
                    RATES["USD_EGP"] = round(data["rates"]["EGP"], 2)
                    RATES["USD_IQD"] = round(data["rates"]["IQD"], 0)

                url = "https://api.binance.com/api/v3/klines?symbol=TONUSDT&interval=1h&limit=24"
                async with session.get(url, timeout=5) as r:
                    data = await r.json()
                    cache["chart_24h"] = [(datetime.datetime.fromtimestamp(x[0]/1000), float(x[4])) for x in data]

                url = "https://api.binance.com/api/v3/klines?symbol=TONUSDT&interval=4h&limit=42"
                async with session.get(url, timeout=5) as r:
                    data = await r.json()
                    cache["chart_7d"] = [(datetime.datetime.fromtimestamp(x[0]/1000), float(x[4])) for x in data]

                print(f"✅ V120 Updated: TON={cache['ton_usd']}")
        except Exception as e:
            print(f"❌ Update Error: {e}")
        await asyncio.sleep(60)

async def check_alerts():
    while True:
        if cache["ton_usd"] == 0:
            await asyncio.sleep(30)
            continue
        to_remove = []
        for user_id, alert in cache["alerts"].items():
            price = alert["price"]
            alert_type = alert["type"]
            current = cache["ton_usd"]
            if (alert_type == "above" and current >= price) or (alert_type == "below" and current <= price):
                try:
                    await bot.send_message(
                        int(user_id),
                        f"🔔 **تنبيه سعر TON** 🔔\n\n"
                        f"السعر وصل {format_price(current)}$\n"
                        f"انت طلبت تنبيه عند {format_price(price)}$\n\n"
                        f"{'🚀 السعر طلع!' if alert_type == 'above' else '📉 السعر نزل!'}",
                        buttons=main_buttons()
                    )
                    to_remove.append(user_id)
                except: pass
        for uid in to_remove:
            del cache["alerts"][uid]
        await asyncio.sleep(30)

async def get_wallet_balance(wallet_address):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://tonapi.io/v2/accounts/{wallet_address}"
            async with session.get(url, timeout=10) as r:
                if r.status == 200:
                    data = await r.json()
                    return int(data["balance"]) / 1e9
    except: pass
    return 0

def format_price(amount):
    if amount >= 1:
        return f"{amount:,.2f}"
    else:
        return f"{amount:.4f}"

def main_buttons():
    fragment_text = "Fragment "
    fragment_entities = [MessageEntityCustomEmoji(9, 1, EMOJI_LINK)]
    dev_text = "المبرمج "
    dev_entities = [MessageEntityCustomEmoji(7, 1, EMOJI_FROG)]
    return ReplyInlineMarkup([
        KeyboardButtonRow([
            KeyboardButtonCallback(text=fragment_text, data=b"fragment", text_entities=fragment_entities),
            KeyboardButtonCallback(text=dev_text, data=b"dev", text_entities=dev_entities)
        ]),
        KeyboardButtonRow([
            Button.inline("📊 شارت 7 ايام", b"chart7d"),
            Button.inline("📈 شارت 24س", b"chart24h"),
            Button.inline("🔔 تنبيه", b"alert")
        ]),
        KeyboardButtonRow([
            Button.inline("💎 المحفظة", b"wallet"),
            Button.inline("🔄 تحديث", b"refresh")
        ])
    ])

def generate_chart(days=7):
    data = cache["chart_7d"] if days == 7 else cache["chart_24h"]
    title = "TON/USDT - 7 Days" if days == 7 else "TON/USDT - 24 Hours"
    if not data: return None
    times, prices = zip(*data)
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='#0e0e0e')
    ax.set_facecolor('#1a1a1a')
    ax.plot(times, prices, color='#00d4ff', linewidth=2.5)
    ax.fill_between(times, prices, alpha=0.3, color='#00d4ff')
    ax.set_title(title, color='white', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Time', color='#888', fontsize=12)
    ax.set_ylabel('Price (USDT)', color='#888', fontsize=12)
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.tick_params(colors='#888')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d' if days == 7 else '%H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='#0e0e0e', dpi=100)
    buf.seek(0)
    plt.close()
    return buf

async def format_tonkit(wallet_address, balance_ton, username="игрок"):
    usd_value = balance_ton * cache["ton_usd"]
    text = f"< TonKit >\n"
    text += f"{username}\n"
    text += f"@{DEV_USERNAME}\n\n"
    text += f"🔗 Wallet :\n{wallet_address}\n"
    text += f"━━━━━━━━━━━«»━━━━━━━━━━━\n"
    text += f"💎 Balance : {format_price(balance_ton)} TON ≈ {format_price(usd_value)}$\n"
    text += f"━━━━━━━━━━━«»━━━━━━━━━━━\n"
    text += f"👥 Users ({len(DEMO_USERS)}) :\n"
    for u in DEMO_USERS:
        text += f"{u}\n"
    text += f"━━━━━━━━━━━«»━━━━━━━━━━━\n"
    text += f"⏰ In Auction (0) :\n~ No auctions ⛔️.\n"
    text += f"━━━━━━━━━━━«»━━━━━━━━━━━\n"
    text += f"☎️ Numbers ({len(DEMO_NUMBERS)}) :\n"
    for i in range(0, len(DEMO_NUMBERS), 2):
        if i+1 < len(DEMO_NUMBERS):
            text += f"{DEMO_NUMBERS[i]} | {DEMO_NUMBERS[i+1]} |\n"
        else:
            text += f"{DEMO_NUMBERS[i]} |\n"
    entities = [
        MessageEntityCustomEmoji(text.find("Wallet"), 1, EMOJI_WALLET),
        MessageEntityCustomEmoji(text.find("Balance"), 1, EMOJI_TON),
        MessageEntityCustomEmoji(text.find("Users"), 1, EMOJI_USERS),
        MessageEntityCustomEmoji(text.find("Numbers"), 1, EMOJI_NUMBERS),
    ]
    return text, entities

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    text = "💎 **بوت TonKit V120** 💎\n\n"
    text += "🚀 **الأوامر:**\n"
    text += "• ابعت عنوان محفظة TON\n"
    text += "• /wallet - محفظتي\n"
    text += "• تون - سعر TON\n"
    text += "• دولار - سعر الدولار\n"
    text += "• اسيا - سعر 100$ اسياسيل\n"
    text += "• زين - سعر 100$ زين كاش\n"
    text += "• ماستر - سعر 100$ ماستر\n"
    text += "• /all - كل الاسعار\n\n"
    text += "🧮 **الحاسبة:**\n"
    text += "100 تون | 5000 جنيه\n\n"
    text += "📊 **المميزات:**\n"
    text += "• /alert 5.5 - تنبيه سعر\n"
    text += "• تحديث تلقائي كل دقيقة\n"
    text += "• شارت PNG حقيقي"
    entities = [MessageEntityCustomEmoji(0, 1, EMOJI_TON), MessageEntityCustomEmoji(17, 1, EMOJI_ROCKET)]
    await event.reply(text, entities=entities, buttons=main_buttons())

@bot.on(events.NewMessage(pattern=r'(?i)^(UQ|EQ|kQ|0Q)[A-Za-z0-9_-]{46}$'))
async def wallet_check(event):
    wallet = event.text.strip()
    msg = await event.reply("⏳ جاري جلب البيانات...")
    balance = await get_wallet_balance(wallet)
    text, entities = await format_tonkit(wallet, balance)
    await msg.delete()
    await bot.send_message(event.chat_id, text, entities=entities, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^/wallet$'))
async def my_wallet(event):
    msg = await event.reply("⏳ جاري جلب بيانات محفظتك...")
    balance = await get_wallet_balance(MY_WALLET)
    text, entities = await format_tonkit(MY_WALLET, balance, "игрок")
    await msg.delete()
    await bot.send_message(event.chat_id, text, entities=entities, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(تون|ton)$'))
async def ton_price(event):
    cache["stats"]["ton"] += 1
    ton_usd = cache["ton_usd"]
    r = RATES
    change_24h = 0
    if len(cache["chart_24h"]) > 1:
        change_24h = ((ton_usd - cache["chart_24h"][0][1]) / cache["chart_24h"][0][1]) * 100
    text = f"💎 **TON/USDT** {'🟢' if change_24h >= 0 else '🔴'} {change_24h:+.2f}%\n\n"
    text += f"**1 TON = {format_price(ton_usd)}$**\n"
    text += f"├ {format_price(ton_usd * r['USD_EGP'])} جنيه\n"
    text += f"├ {format_price(ton_usd * r['USD_IQD'])} دينار\n"
    text += f"├ {format_price(ton_usd * r['USD_ASIA'])} اسياسيل\n"
    text += f"├ {format_price(ton_usd * r['USD_ZAIN'])} زين كاش\n"
    text += f"└ {format_price(ton_usd * r['USD_MASTER'])} ماستر\n\n"
    text += f"⏰ تحديث تلقائي كل دقيقة"
    entities = [MessageEntityCustomEmoji(0, 1, EMOJI_TON)]
    await event.reply(text, entities=entities, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(دولار|usd)$'))
async def usd_price(event):
    cache["stats"]["usd"] += 1
    r = RATES
    text = f"💵 **الدولار الأمريكي**\n\n"
    text += f"**1$ =**\n"
    text += f"├ {format_price(r['USD_EGP'])} جنيه مصري\n"
    text += f"├ {format_price(r['USD_IQD'])} دينار عراقي\n"
    text += f"├ {format_price(r['USD_ASIA'])} اسياسيل\n"
    text += f"├ {format_price(r['USD_ZAIN'])} زين كاش\n"
    text += f"└ {format_price(r['USD_MASTER'])} ماستر"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(اسيا|اسياسيل|asia)$'))
async def asia_price(event):
    cache["stats"]["asia"] += 1
    ton_usd = cache["ton_usd"]
    r = RATES
    text = f"📱 **100$ اسياسيل**\n\n"
    text += f"**100$ اسيا =**\n"
    text += f"├ {format_price(100 * r['USD_IQD'])} دينار\n"
    text += f"├ {format_price(100 * r['USD_EGP'])} جنيه\n"
    text += f"├ {format_price(100 / ton_usd)} TON\n"
    text += f"└ {format_price(100 * r['USD_ASIA'] / r['USD_ZAIN'])} دولار زين\n\n"
    text += f"1$ اسيا = {format_price(r['USD_ASIA'])} دينار"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(زين|zain)$'))
async def zain_price(event):
    cache["stats"]["zain"] += 1
    ton_usd = cache["ton_usd"]
    r = RATES
    text = f"📱 **100$ زين كاش**\n\n"
    text += f"**100$ زين =**\n"
    text += f"├ {format_price(100 * r['USD_IQD'])} دينار\n"
    text += f"├ {format_price(100 * r['USD_EGP'])} جنيه\n"
    text += f"├ {format_price(100 / ton_usd)} TON\n"
    text += f"└ {format_price(100 * r['USD_ZAIN'] / r['USD_ASIA'])} دولار اسيا\n\n"
    text += f"1$ زين = {format_price(r['USD_ZAIN'])} دينار"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(ماستر|master)$'))
async def master_price(event):
    cache["stats"]["master"] += 1
    ton_usd = cache["ton_usd"]
    r = RATES
    text = f"💳 **100$ ماستر كارد**\n\n"
    text += f"**100$ ماستر =**\n"
    text += f"├ {format_price(100 * r['USD_IQD'])} دينار\n"
    text += f"├ {format_price(100 * r['USD_EGP'])} جنيه\n"
    text += f"├ {format_price(100 / ton_usd)} TON\n"
    text += f"└ {format_price(100 * r['USD_MASTER'] / r['USD_ASIA'])} دولار اسيا\n\n"
    text += f"1$ ماستر = {format_price(r['USD_MASTER'])} دينار"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(جنيه|egp)$'))
async def egp_price(event):
    cache["stats"]["egp"] += 1
    ton_usd = cache["ton_usd"]
    r = RATES
    text = f"🇪🇬 **100$ بالجنيه**\n\n"
    text += f"100$ = {format_price(100 * r['USD_EGP'])} جنيه\n"
    text += f"100$ = {format_price(100 * r['USD_IQD'])} دينار\n"
    text += f"100$ = {format_price(100 / ton_usd)} TON\n"
    text += f"1$ = {format_price(r['USD_EGP'])} جنيه"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^(دينار|iqd)$'))
async def iqd_price(event):
    cache["stats"]["iqd"] += 1
    ton_usd = cache["ton_usd"]
    r = RATES
    text = f"🇮🇶 **100$ بالدينار**\n\n"
    text += f"100$ = {format_price(100 * r['USD_IQD'])} دينار\n"
    text += f"100$ = {format_price(100 * r['USD_EGP'])} جنيه\n"
    text += f"100$ = {format_price(100 / ton_usd)} TON\n"
    text += f"1$ = {format_price(r['USD_IQD'])} دينار"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern='(?i)^/all$'))
async def all_prices(event):
    ton_usd = cache["ton_usd"]
    r = RATES
    change_24h = 0
    if len(cache["chart_24h"]) > 1:
        change_24h = ((ton_usd - cache["chart_24h"][0][1]) / cache["chart_24h"][0][1]) * 100
    text = f"🔥 **كل الأسعار V120** 🔥\n\n"
    text += f"💎 **TON = {format_price(ton_usd)}$** {'🟢' if change_24h >= 0 else '🔴'} {change_24h:+.2f}%\n"
    text += f"├ {format_price(ton_usd * r['USD_EGP'])} جنيه\n"
    text += f"├ {format_price(ton_usd * r['USD_IQD'])} دينار\n"
    text += f"└ {format_price(ton_usd * r['USD_ASIA'])} اسياسيل\n\n"
    text += f"💵 **1 دولار**\n"
    text += f"├ {format_price(r['USD_EGP'])} جنيه\n"
    text += f"├ {format_price(r['USD_IQD'])} دينار\n"
    text += f"├ {format_price(r['USD_ASIA'])} اسياسيل\n"
    text += f"├ {format_price(r['USD_ZAIN'])} زين\n"
    text += f"└ {format_price(r['USD_MASTER'])} ماستر"
    entities = [MessageEntityCustomEmoji(0, 1, EMOJI_FIRE)]
    await event.reply(text, entities=entities, buttons=main_buttons())

@bot.on(events.NewMessage(pattern=r'(?i)^(\d+\.?\d*)\s*(تون|دولار|اسيا|زين|ماستر|جنيه|دينار|ton|usd|egp|iqd)$'))
async def calculator(event):
    amount = float(event.pattern_match.group(1))
    currency = event.pattern_match.group(2).lower()
    ton_usd = cache["ton_usd"]
    r = RATES
    if currency in ['تون', 'ton']:
        usd = amount * ton_usd
    elif currency in ['دولار', 'usd']:
        usd = amount
    elif currency in ['جنيه', 'egp']:
        usd = amount / r['USD_EGP']
    elif currency in ['دينار', 'iqd']:
        usd = amount / r['USD_IQD']
    elif currency in ['اسيا']:
        usd = amount
    elif currency in ['زين']:
        usd = amount * r['USD_ZAIN'] / r['USD_IQD']
    elif currency in ['ماستر']:
        usd = amount * r['USD_MASTER'] / r['USD_IQD']
    else:
        return
    text = f"🧮 **الحاسبة**\n\n"
    text += f"**{format_price(amount)} {currency.upper()} =**\n\n"
    text += f"💵 {format_price(usd)} دولار\n"
    text += f"💎 {format_price(usd / ton_usd)} TON\n"
    text += f"🇪🇬 {format_price(usd * r['USD_EGP'])} جنيه\n"
    text += f"🇮🇶 {format_price(usd * r['USD_IQD'])} دينار\n"
    text += f"📱 {format_price(usd * r['USD_IQD'] / r['USD_ASIA'])} دولار اسيا"
    await event.reply(text, buttons=main_buttons())

@bot.on(events.NewMessage(pattern=r'/alert\s+(\d+\.?\d*)'))
async def set_alert(event):
    price = float(event.pattern_match.group(1))
    user_id = str(event.sender_id)
    current = cache["ton_usd"]
    alert_type = "above" if price > current else "below"
    cache["alerts"][user_id] = {"price": price, "type": alert_type}
    text = f"🔔 **تم ضبط التنبيه**\n\n"
    text += f"هنبهك لما TON يوصل **{format_price(price)}$**\n"
    text += f"السعر الحالي: {format_price(current)}$\n\n"
    text += f"{'🚀 تنبيه صعود' if alert_type == 'above' else '📉 تنبيه هبوط'}"
    entities = [MessageEntityCustomEmoji(0, 1, EMOJI_BELL)]
    await event.reply(text, entities=entities, buttons=main_buttons())

@bot.on(events.CallbackQuery(data=b"fragment"))
async def fragment_btn(event):
    await event.answer(url="https://fragment.com")

@bot.on(events.CallbackQuery(data=b"dev"))
async def dev_btn(event):
    await event.answer(url=f"https://t.me/{DEV_USERNAME}")

@bot.on(events.CallbackQuery(data=b"refresh"))
async def refresh_btn(event):
    cache["last_update"] = 0
    await event.answer("جاري التحديث...", alert=False)
    await ton_price(event)

@bot.on(events.CallbackQuery(data=b"chart7d"))
async def chart7d_btn(event):
    await event.answer("جاري رسم الشارت...", alert=False)
    buf = generate_chart(7)
    if buf:
        await bot.send_file(event.chat_id, buf, caption="📈 **شارت TON - 7 ايام**\n\n⏰ تحديث تلقائي", buttons=main_buttons())
    else:
        await event.answer("الشارت لسه بيحمل", alert=True)

@bot.on(events.CallbackQuery(data=b"chart24h"))
async def chart24h_btn(event):
    await event.answer("جاري رسم الشارت...", alert=False)
    buf = generate_chart(1)
    if buf:
        await bot.send_file(event.chat_id, buf, caption="📈 **شارت TON - 24 ساعة**\n\n⏰ تحديث تلقائي", buttons=main_buttons())
    else:
        await event.answer("الشارت لسه بيحمل", alert=True)

@bot.on(events.CallbackQuery(data=b"alert"))
async def alert_btn(event):
    await event.edit(
        "🔔 **ضبط تنبيه سعر**\n\n"
        "ابعت الأمر كده:\n"
        "/alert 5.5\n\n"
        "هنبهك لما TON يوصل 5.5 دولار\n"
        "شغال حتى لو البوت مقفول",
        buttons=main_buttons()
    )

@bot.on(events.CallbackQuery(data=b"wallet"))
async def wallet_btn(event):
    await my_wallet(event)

@bot.on(events.NewMessage(pattern='/update'))
async def update_rates(event):
    if event.sender_id!= DEV_ID:
        return await event.reply("الأمر للمطور فقط", buttons=main_buttons())
    await event.reply(
        "ابعت الاسعار الجديدة:\n\n"
        "USD_EGP 48.6\nUSD_IQD 1310\nUSD_ASIA 1320\nUSD_ZAIN 1325\nUSD_MASTER 1340",
        buttons=main_buttons()
    )

@bot.on(events.NewMessage)
async def handle_update(event):
    if event.sender_id!= DEV_ID or not event.text.startswith("USD_"):
        return
    try:
        for line in event.text.split('\n'):
            key, val = line.split()
            RATES[key] = float(val)
        await event.reply(f"✅ تم تحديث الاسعار", buttons=main_buttons())
    except: pass

async def main():
    load_dotenv()
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    global bot
    bot = TelegramClient('tonkit_v120', API_ID, API_HASH)

    await bot.start(bot_token=BOT_TOKEN)
    asyncio.create_task(update_rates_auto())
    asyncio.create_task(check_alerts())
    print("✅ TonKit V120 Running - Wallet + Charts + Alerts")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
