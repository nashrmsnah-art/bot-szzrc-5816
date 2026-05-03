import os, asyncio, json, datetime
from telethon import TelegramClient, events, Button, functions
from telethon.tl.types import (
    UpdateBotChatInviteRequester, PeerChannel, MessageEntityCustomEmoji,
    KeyboardButtonCallback, ReplyInlineMarkup, KeyboardButtonRow
)

API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEV_ID = 154919127
DEV_USERNAME = "Devazf"
DB_CHANNEL = -1003868650424 # غيرها لقناة فاضية عندك

DB_MSG_ID = None

# ايديهات الايموجي البريميوم
EMOJI_SHIELD = 5111936883915490730 # 🛡️
EMOJI_FROG = 5111976779866703826 # 🐸
EMOJI_CHECK = 5111793865799501619 # ✅
EMOJI_SEARCH = 5111936883915490730 # 🔍

def get_default_db():
    return {
        "groups": {},
        "pending": {},
        "blacklist": [],
        "whitelist": [],
        "admins": [DEV_ID],
        "stats": {"approved": 0, "rejected": 0, "auto_rejected": 0},
        "group_stats": {},
        "logs": [],
        "states": {},
        "verified_phones": {},
        "settings": {
            "global_timeout": 10,
            "default_verify_msg": "لإتمام عملية التحقق يرجى مشاركة رقم هاتفك:",
            "default_success_msg": "تم التحقق بنجاح ✅\nاهلاً بك في {group}",
            "default_button": "مشاركة جهة الاتصال"
        }
    }

DB = get_default_db()
bot = None

async def load_db():
    global DB, DB_MSG_ID
    try:
        async for msg in bot.iter_messages(DB_CHANNEL, limit=10):
            if msg.text and msg.text.startswith("DB_V21:"):
                DB_MSG_ID = msg.id
                db_str = msg.text.replace("DB_V21:", "", 1)
                DB = json.loads(db_str)
                print("✅ V20.3 DB Loaded")
                return
        msg = await bot.send_message(DB_CHANNEL, "DB_V21:" + json.dumps(get_default_db(), ensure_ascii=False))
        DB_MSG_ID = msg.id
        print("✅ V20.3 DB Created")
    except Exception as e:
        print(f"❌ DB Error: {e}")

async def save_db():
    global DB_MSG_ID
    try:
        db_str = "DB_V21:" + json.dumps(DB, ensure_ascii=False)
        if DB_MSG_ID:
            await bot.edit_message(DB_CHANNEL, DB_MSG_ID, db_str)
        else:
            msg = await bot.send_message(DB_CHANNEL, db_str)
            DB_MSG_ID = msg.id
        return True
    except Exception as e:
        print(f"❌ Save Error: {e}")
        return False

def is_admin(user_id):
    return user_id in DB["admins"]

def get_group_config(gid):
    g = DB["groups"].get(gid, {})
    return {
        "name": g.get("name", "Unknown"),
        "enabled": g.get("enabled", True),
        "verify_msg": g.get("verify_msg", DB["settings"]["default_verify_msg"]),
        "success_msg": g.get("success_msg", DB["settings"]["default_success_msg"]),
        "button_text": g.get("button_text", DB["settings"]["default_button"]),
        "timeout": g.get("timeout", DB["settings"]["global_timeout"])
    }

def add_log(user_id, group_id, action):
    log = {
        "user_id": user_id,
        "group_id": group_id,
        "action": action,
        "time": datetime.datetime.now().isoformat()
    }
    DB["logs"].insert(0, log)
    if len(DB["logs"]) > 500:
        DB["logs"] = DB["logs"][:500]

async def check_timeouts():
    while True:
        await asyncio.sleep(60)
        now = datetime.datetime.now()
        to_remove = []
        for uid, data in DB["pending"].items():
            gid = data["group_id"]
            cfg = get_group_config(gid)
            timeout = cfg["timeout"]
            if timeout == 0: continue
            req_time = datetime.datetime.fromisoformat(data["time"])
            if (now - req_time).total_seconds() > timeout * 60:
                try:
                    await bot(functions.messages.HideChatJoinRequestRequest(
                        peer=int(gid), user_id=int(uid), approved=False
                    ))
                    DB["stats"]["auto_rejected"] += 1
                    if gid not in DB["group_stats"]:
                        DB["group_stats"][gid] = {"approved": 0, "rejected": 0}
                    DB["group_stats"][gid]["rejected"] += 1
                    add_log(int(uid), gid, "auto_rejected_timeout")
                    to_remove.append(uid)
                except: pass
        for uid in to_remove:
            if uid in DB["pending"]:
                del DB["pending"][uid]
        if to_remove:
            await save_db()

async def setup_bot():
    global bot
    bot = TelegramClient('join_v21', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    await load_db()
    asyncio.create_task(check_timeouts())

    # ===== /start مع زرار بريميوم شغال =====
    @bot.on(events.NewMessage(pattern='/start'))
    async def start_cmd(event):
        if not is_admin(event.sender_id):
            # الرسالة فيها ايموجي بريميوم
            text = "أهلاً بك في بوت القبول."
            entities = [MessageEntityCustomEmoji(15, 1, EMOJI_FROG)]

            # الزرار البريميوم بالـ Raw API
            btn_text = "المطور " # مسافة في الاخر مهمة
            btn_entities = [MessageEntityCustomEmoji(6, 1, EMOJI_FROG)] # offset=6 بعد كلمة المطور

            markup = ReplyInlineMarkup([
                KeyboardButtonRow([
                    KeyboardButtonCallback(
                        text=btn_text,
                        data=b"dev_btn",
                        text_entities=btn_entities
                    )
                ])
            ])

            await bot.send_message(event.chat_id, text, entities=entities, buttons=markup)
            return

        # لوحة تحكم الادمن
        btns = [
            [Button.inline("اضافة جروب", b"add_g"), Button.inline("الجروبات", b"list_g")],
            [Button.inline("القائمة السوداء", b"blacklist"), Button.inline("القائمة البيضاء", b"whitelist")],
            [Button.inline("الاحصائيات", b"stats"), Button.inline("السجلات", b"logs")],
            [Button.inline("الادمنز", b"admins"), Button.inline("الاعدادات", b"settings")]
        ]
        await event.reply(
            f"**بوت V20.3 - لوحة التحكم**\n\n"
            f"الجروبات: {len(DB['groups'])}\n"
            f"مقبول: {DB['stats']['approved']}\n"
            f"مرفوض: {DB['stats']['rejected']}\n"
            f"مرفوض تلقائي: {DB['stats']['auto_rejected']}\n"
            f"ارقام محققة: {len(DB['verified_phones'])}",
            buttons=btns
        )

    # لما يدوس على زرار المطور البريميوم
    @bot.on(events.CallbackQuery(data=b"dev_btn"))
    async def dev_button(event):
        await event.answer(url=f"https://t.me/{DEV_USERNAME}")

    # ===== /help =====
    @bot.on(events.NewMessage(pattern='/help'))
    async def help_cmd(event):
        text = "هذا البوت للتحقق من المستخدمين قبل قبولهم."
        entities = [MessageEntityCustomEmoji(47, 1, EMOJI_FROG)]
        await event.reply(text, entities=entities)

    # ===== /verify يدوي =====
    @bot.on(events.NewMessage(pattern='/verify'))
    async def verify_cmd(event):
        text = "لإتمام عملية التحقق يرجى مشاركة رقم هاتفك:"
        entities = [MessageEntityCustomEmoji(46, 1, EMOJI_SHIELD)]
        await bot.send_message(
            event.chat_id,
            text,
            entities=entities,
            buttons=[[Button.request_phone("مشاركة جهة الاتصال")]]
        )

    # ===== استقبال رقم الهاتف =====
    @bot.on(events.NewMessage)
    async def handle_contact(event):
        if event.contact:
            user_id = str(event.sender_id)
            phone = event.contact.phone_number

            if user_id not in DB["pending"]:
                return await event.reply("مفيش طلب تحقق نشط ليك. قدم طلب انضمام للجروب الأول")

            data = DB["pending"][user_id]
            group_id = data["group_id"]
            DB["verified_phones"][user_id] = phone

            try:
                await bot(functions.messages.HideChatJoinRequestRequest(
                    peer=int(group_id), user_id=int(user_id), approved=True
                ))

                del DB["pending"][user_id]
                DB["stats"]["approved"] += 1
                if group_id not in DB["group_stats"]:
                    DB["group_stats"][group_id] = {"approved": 0, "rejected": 0}
                DB["group_stats"][group_id]["approved"] += 1
                add_log(int(user_id), group_id, "approved_phone")
                await save_db()

                cfg = get_group_config(group_id)
                text = cfg["success_msg"].format(group=cfg["name"])
                entities = [MessageEntityCustomEmoji(16, 1, EMOJI_CHECK)]
                await bot.send_message(event.chat_id, text, entities=entities)

            except Exception as e:
                await event.reply(f"خطأ في القبول: {e}")

    # ===== طلبات الانضمام التلقائي =====
    @bot.on(events.Raw)
    async def join_handler(event):
        if isinstance(event, UpdateBotChatInviteRequester):
            chat_id = event.peer.channel_id if isinstance(event.peer, PeerChannel) else event.peer.chat_id
            user_id = event.user_id
            chat_id_str = str(-1000000000000 - chat_id) if chat_id > 0 else str(chat_id)

            if chat_id_str not in DB["groups"]:
                return

            g = DB["groups"][chat_id_str]
            if not g["enabled"]:
                return

            if str(user_id) in DB["verified_phones"]:
                try:
                    await bot(functions.messages.HideChatJoinRequestRequest(
                        peer=int(chat_id_str), user_id=user_id, approved=True
                    ))
                    DB["stats"]["approved"] += 1
                    add_log(user_id, chat_id_str, "auto_verified")
                    await save_db()
                    return
                except: pass

            DB["pending"][str(user_id)] = {
                "group_id": chat_id_str,
                "chat_id": event.invite.chat_id,
                "time": datetime.datetime.now().isoformat()
            }
            await save_db()

            try:
                user = await bot.get_entity(user_id)
                chat = await bot.get_entity(int(chat_id_str))
                user_name = user.first_name
                group_name = chat.title
            except:
                user_name = "صديقي"
                group_name = g["name"]

            text = f"أهلاً {user_name}\n\nقبل قبولك في مجموعة {group_name} يجب التحقق من أنك مستخدم حقيقي.\n\nيرجى مشاركة رقم هاتفك عبر الزر أدناه."

            try:
                await bot.send_message(
                    user_id,
                    text,
                    buttons=[[Button.request_phone("مشاركة جهة الاتصال")]]
                )
            except:
                try:
                    mention = f"[{user_name}](tg://user?id={user_id})"
                    bot_username = (await bot.get_me()).username
                    await bot.send_message(
                        int(chat_id_str),
                        f"👋 {mention}\n\nابعت /verify في الخاص عشان تتحقق",
                    )
                except: pass

    # ===== اوامر الادمن =====
    @bot.on(events.CallbackQuery(data=b"add_g"))
    async def add_g(event):
        if not is_admin(event.sender_id):
            return await event.answer("للمشرفين فقط", alert=True)
        DB["states"][str(event.sender_id)] = "add_group"
        await save_db()
        await event.edit("ابعت ايدي الجروب او اعمل Forward لرسالة منه")

    @bot.on(events.NewMessage)
    async def handle_states(event):
        uid = str(event.sender_id)
        if uid not in DB["states"] or event.contact:
            return

        state = DB["states"][uid]

        if state == "add_group":
            gid = None
            name = "Unknown"
            try:
                if event.forward:
                    gid = str(event.forward.chat_id)
                    chat = await bot.get_entity(event.forward.chat_id)
                    name = chat.title
                else:
                    gid = event.text.strip()
                    chat = await bot.get_entity(int(gid))
                    name = chat.title

                DB["groups"][gid] = {
                    "name": name,
                    "enabled": True,
                    "verify_msg": DB["settings"]["default_verify_msg"],
                    "success_msg": DB["settings"]["default_success_msg"],
                    "button_text": DB["settings"]["default_button"],
                    "timeout": DB["settings"]["global_timeout"]
                }
                del DB["states"][uid]
                await save_db()
                await event.reply(f"✅ تم اضافة الجروب: {name}\nالايدي: `{gid}`")
            except Exception as e:
                await event.reply(f"❌ خطأ: {e}\nاتأكد ان البوت ادمن في الجروب")

    @bot.on(events.CallbackQuery(data=b"list_g"))
    async def list_g(event):
        if not is_admin(event.sender_id):
            return await event.answer("للمشرفين فقط", alert=True)

        if not DB["groups"]:
            return await event.edit("مفيش جروبات", buttons=[[Button.inline("رجوع", b"back")]])

        text = "**الجروبات المضافة:**\n\n"
        btns = []
        for gid, g in DB["groups"].items():
            status = "✅" if g["enabled"] else "❌"
            text += f"{status} {g['name']}\n`{gid}`\n\n"
            btns.append([Button.inline(f"ادارة {g['name'][:15]}", f"manage_{gid}".encode())])

        btns.append([Button.inline("رجوع", b"back")])
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(data=b"back"))
    async def back_main(event):
        await start_cmd(event)

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود")
        return
    await setup_bot()
    print("✅ V20.3 Bot Running - Premium Emoji + Phone Verify")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
