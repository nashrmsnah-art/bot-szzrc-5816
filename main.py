import os, asyncio, json, datetime
from telethon import TelegramClient, events, Button, functions, types
from telethon.tl.types import UpdateBotChatInviteRequester, PeerChannel, KeyboardButtonCallback, ReplyInlineMarkup, KeyboardButtonRow

API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEV_ID = 154919127
DEV_USERNAME = "Devazf"
DB_CHANNEL = -1002797179464 # حط ايدي قناة الداتا هنا

DB_MSG_ID = None

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
        "settings": {
            "global_timeout": 10,
            "default_verify_msg": "مرحباً {name}\n\nاضغط الزر عشان نقبلك في {group}",
            "default_success_msg": "تم قبولك في {group} بنجاح ✅",
            "default_button": "تحقق انك لست روبوت"
        }
    }

DB = get_default_db()
bot = None

async def load_db():
    global DB, DB_MSG_ID
    try:
        async for msg in bot.iter_messages(DB_CHANNEL, limit=10):
            if msg.text and msg.text.startswith("DB_V20:"):
                DB_MSG_ID = msg.id
                db_str = msg.text.replace("DB_V20:", "", 1)
                DB = json.loads(db_str)
                print("✅ V20.2 DB Loaded")
                return
        msg = await bot.send_message(DB_CHANNEL, "DB_V20:" + json.dumps(get_default_db(), ensure_ascii=False))
        DB_MSG_ID = msg.id
        print("✅ V20.2 DB Created")
    except Exception as e:
        print(f"❌ DB Error: {e}")

async def save_db():
    global DB_MSG_ID
    try:
        db_str = "DB_V20:" + json.dumps(DB, ensure_ascii=False)
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

def set_state(user_id, state):
    DB["states"][str(user_id)] = state

def get_state(user_id):
    return DB["states"].get(str(user_id))

def clear_state(user_id):
    if str(user_id) in DB["states"]:
        del DB["states"][str(user_id)]

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

def build_button_markup(user_id, group_id):
    cfg = get_group_config(group_id)
    btn = KeyboardButtonCallback(text=cfg["button_text"], data=f"v_{user_id}_{group_id}".encode())
    return ReplyInlineMarkup([KeyboardButtonRow([btn])])

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
    bot = TelegramClient('join_v20', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    await load_db()
    asyncio.create_task(check_timeouts())

    @bot.on(events.NewMessage(pattern='/start'))
    async def start_cmd(event):
        if not is_admin(event.sender_id):
            total = DB['stats']['approved']
            btns = [[Button.url("ضيف البوت لجروبك", f"https://t.me/{(await bot.get_me()).username}?startgroup=true")],
                    [Button.url("المبرمج", f"https://t.me/{DEV_USERNAME}")]]
            await event.reply(
                f"**بوت الموافقة التلقائية V20.2**\n\n"
                f"البوت بيقبل طلبات الانضمام تلقائياً بعد التحقق\n\n"
                f"تم قبول: {total} عضو\n\n"
                f"مجاناً 100%",
                buttons=btns
            )
            return

        btns = [
            [Button.inline("اضافة جروب", b"add_g"), Button.inline("الجروبات", b"list_g")],
            [Button.inline("القائمة السوداء", b"blacklist"), Button.inline("القائمة البيضاء", b"whitelist")],
            [Button.inline("الاحصائيات", b"stats"), Button.inline("السجلات", b"logs")],
            [Button.inline("الادمنز", b"admins"), Button.inline("الاعدادات", b"settings")],
            [Button.url("المبرمج", f"https://t.me/{DEV_USERNAME}")]
        ]
        await event.reply(
            f"**بوت V20.2 - لوحة التحكم**\n\n"
            f"الجروبات: {len(DB['groups'])}\n"
            f"مقبول: {DB['stats']['approved']}\n"
            f"مرفوض: {DB['stats']['rejected']}\n"
            f"مرفوض تلقائي: {DB['stats']['auto_rejected']}\n"
            f"قائمة سوداء: {len(DB['blacklist'])}\n"
            f"قائمة بيضاء: {len(DB['whitelist'])}\n\n"
            f"**الحفظ في قناة خاصة - مضمون**",
            buttons=btns
        )

    @bot.on(events.NewMessage(pattern=r'/start verify_(\d+)_(-?\d+)'))
    async def start_verify(event):
        parts = event.pattern_match.groups()
        user_id = int(parts[0])
        group_id = parts[1]

        if event.sender_id!= user_id:
            return await event.reply("الرابط ده مش ليك")

        if str(user_id) not in DB["pending"]:
            return await event.reply("الطلب انتهى او اتقبل خلاص")

        cfg = get_group_config(group_id)
        markup = build_button_markup(user_id, group_id)

        await event.reply(
            cfg["verify_msg"].format(name=event.sender.first_name, group=cfg["name"]),
            buttons=markup
        )

    @bot.on(events.CallbackQuery(data=b"add_g"))
    async def add_g(event):
        if not is_admin(event.sender_id):
            return await event.answer("للمشرفين فقط", alert=True)
        set_state(event.sender_id, "wait_gid")
        await save_db()
        await event.edit(
            "**اضافة جروب**\n\n"
            "1. ضيف البوت ادمن في الجروب\n"
            "2. اديله صلاحية Add Members\n"
            "3. ابعت ايدي الجروب او اليوزر\n\n"
            "او اعمل Forward لرسالة من الجروب",
            buttons=[[Button.inline("رجوع", b"back")]]
        )

    @bot.on(events.CallbackQuery(data=b"list_g"))
    async def list_g(event):
        if not is_admin(event.sender_id): return
        if not DB["groups"]:
            return await event.edit("مفيش جروبات", buttons=[[Button.inline("رجوع", b"back")]])

        text = "**الجروبات المفعلة:**\n\n"
        btns = []
        for gid, data in DB["groups"].items():
            status = "مفعل" if data["enabled"] else "معطل"
            gstats = DB["group_stats"].get(gid, {"approved": 0, "rejected": 0})
            text += f"**{data['name']}**\n"
            text += f"`{gid}` | {status}\n"
            text += f"مقبول: {gstats['approved']} | مرفوض: {gstats['rejected']}\n\n"
            btns.append([Button.inline(f"{data['name'][:25]}", f"mg_{gid}".encode())])

        btns.append([Button.inline("رجوع", b"back")])
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"mg_"))
    async def manage_g(event):
        if not is_admin(event.sender_id): return
        gid = event.data.decode().split("_", 1)[1]
        if gid not in DB["groups"]:
            return await event.answer("الجروب مش موجود", alert=True)

        g = DB["groups"][gid]
        cfg = get_group_config(gid)
        gstats = DB["group_stats"].get(gid, {"approved": 0, "rejected": 0})

        text = f"**{g['name']}**\n\n"
        text += f"الحالة: {'مفعل' if g['enabled'] else 'معطل'}\n"
        text += f"المؤقت: {cfg['timeout']} دقيقة\n"
        text += f"مقبول: {gstats['approved']}\n"
        text += f"مرفوض: {gstats['rejected']}\n\n"
        text += f"**رسالة التحقق:**\n{cfg['verify_msg'][:100]}...\n\n"
        text += f"**زر التحقق:** {cfg['button_text']}"

        btns = [
            [Button.inline("تفعيل/ايقاف", f"tg_{gid}".encode())],
            [Button.inline("تعديل الرسالة", f"em_{gid}".encode())],
            [Button.inline("تعديل الزر", f"eb_{gid}".encode())],
            [Button.inline("تعديل المؤقت", f"et_{gid}".encode())],
            [Button.inline("حذف الجروب", f"dg_{gid}".encode())],
            [Button.inline("رجوع", b"list_g")]
        ]
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"tg_"))
    async def toggle_g(event):
        if not is_admin(event.sender_id): return
        gid = event.data.decode().split("_", 1)[1]
        if gid in DB["groups"]:
            DB["groups"][gid]["enabled"] = not DB["groups"][gid]["enabled"]
            await save_db()
            await event.answer("تم التغيير", alert=True)
            await manage_g(event)

    @bot.on(events.CallbackQuery(pattern=b"em_"))
    async def edit_msg(event):
        if not is_admin(event.sender_id): return
        gid = event.data.decode().split("_", 1)[1]
        set_state(event.sender_id, f"wait_msg_{gid}")
        await save_db()
        await event.edit(
            "**تعديل رسالة التحقق**\n\n"
            "ابعت الرسالة الجديدة\n\n"
            "المتغيرات: {name} {group}",
            buttons=[[Button.inline("رجوع", f"mg_{gid}".encode())]]
        )

    @bot.on(events.CallbackQuery(pattern=b"eb_"))
    async def edit_btn(event):
        if not is_admin(event.sender_id): return
        gid = event.data.decode().split("_", 1)[1]
        set_state(event.sender_id, f"wait_btn_{gid}")
        await save_db()
        await event.edit(
            "**تعديل نص الزر**\n\nابعت النص الجديد",
            buttons=[[Button.inline("رجوع", f"mg_{gid}".encode())]]
        )

    @bot.on(events.CallbackQuery(pattern=b"et_"))
    async def edit_timeout(event):
        if not is_admin(event.sender_id): return
        gid = event.data.decode().split("_", 1)[1]
        set_state(event.sender_id, f"wait_timeout_{gid}")
        await save_db()
        await event.edit(
            "**تعديل المؤقت**\n\n"
            "ابعت عدد الدقايق\n"
            "اللي ميتحققش خلالهم يترفض تلقائي\n\n"
            "0 = بدون مؤقت",
            buttons=[[Button.inline("رجوع", f"mg_{gid}".encode())]]
        )

    @bot.on(events.CallbackQuery(pattern=b"dg_"))
    async def del_g(event):
        if not is_admin(event.sender_id): return
        gid = event.data.decode().split("_", 1)[1]
        if gid in DB["groups"]:
            del DB["groups"][gid]
            await save_db()
            await event.answer("تم الحذف", alert=True)
            await list_g(event)

    @bot.on(events.CallbackQuery(data=b"blacklist"))
    async def blacklist(event):
        if not is_admin(event.sender_id): return
        text = f"**القائمة السوداء**\n\nالعدد: {len(DB['blacklist'])}\n\n"
        if DB['blacklist']:
            text += "الايديهات:\n"
            for uid in DB['blacklist'][:20]:
                text += f"`{uid}`\n"
        btns = [
            [Button.inline("اضافة", b"add_black"), Button.inline("حذف", b"del_black")],
            [Button.inline("رجوع", b"back")]
        ]
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(data=b"add_black"))
    async def add_black(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_black_add")
        await save_db()
        await event.edit("ابعت ايدي الشخص للحظر", buttons=[[Button.inline("رجوع", b"blacklist")]])

    @bot.on(events.CallbackQuery(data=b"del_black"))
    async def del_black(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_black_del")
        await save_db()
        await event.edit("ابعت ايدي الشخص للحذف من الحظر", buttons=[[Button.inline("رجوع", b"blacklist")]])

    @bot.on(events.CallbackQuery(data=b"whitelist"))
    async def whitelist(event):
        if not is_admin(event.sender_id): return
        text = f"**القائمة البيضاء**\n\nالعدد: {len(DB['whitelist'])}\n\n"
        text += "اللي في القائمة بيتقبل تلقائي بدون تحقق\n\n"
        if DB['whitelist']:
            text += "الايديهات:\n"
            for uid in DB['whitelist'][:20]:
                text += f"`{uid}`\n"
        btns = [
            [Button.inline("اضافة", b"add_white"), Button.inline("حذف", b"del_white")],
            [Button.inline("رجوع", b"back")]
        ]
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(data=b"add_white"))
    async def add_white(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_white_add")
        await save_db()
        await event.edit("ابعت ايدي الشخص للقبول التلقائي", buttons=[[Button.inline("رجوع", b"whitelist")]])

    @bot.on(events.CallbackQuery(data=b"del_white"))
    async def del_white(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_white_del")
        await save_db()
        await event.edit("ابعت ايدي الشخص للحذف", buttons=[[Button.inline("رجوع", b"whitelist")]])

    @bot.on(events.CallbackQuery(data=b"stats"))
    async def stats(event):
        if not is_admin(event.sender_id): return
        s = DB['stats']
        total = s['approved'] + s['rejected'] + s['auto_rejected']
        rate = (s['approved'] / total * 100) if total > 0 else 0

        text = f"**احصائيات البوت V20.2**\n\n"
        text += f"الاجمالي: {total}\n"
        text += f"مقبول: {s['approved']}\n"
        text += f"مرفوض: {s['rejected']}\n"
        text += f"مرفوض تلقائي: {s['auto_rejected']}\n"
        text += f"نسبة القبول: {rate:.1f}%\n\n"
        text += f"الجروبات: {len(DB['groups'])}\n"
        text += f"الادمنز: {len(DB['admins'])}\n"
        text += f"القائمة السوداء: {len(DB['blacklist'])}\n"
        text += f"القائمة البيضاء: {len(DB['whitelist'])}"

        await event.edit(text, buttons=[[Button.inline("رجوع", b"back")]])

    @bot.on(events.CallbackQuery(data=b"logs"))
    async def logs(event):
        if not is_admin(event.sender_id): return
        text = "**اخر 20 سجل**\n\n"
        for log in DB["logs"][:20]:
            action = {"approved": "قبول", "rejected": "رفض", "auto_rejected_timeout": "رفض تلقائي", "whitelist": "قائمة بيضاء", "blacklist": "قائمة سوداء", "auto_approved": "قبول تلقائي"}.get(log["action"], log["action"])
            time = datetime.datetime.fromisoformat(log["time"]).strftime("%m/%d %H:%M")
            text += f"{time} | {action}\n"
            text += f"User: `{log['user_id']}` | Group: `{log['group_id']}`\n\n"

        await event.edit(text[:4000], buttons=[[Button.inline("رجوع", b"back")]])

    @bot.on(events.CallbackQuery(data=b"admins"))
    async def admins(event):
        if event.sender_id!= DEV_ID:
            return await event.answer("للمطور فقط", alert=True)
        text = f"**الادمنز**\n\nالعدد: {len(DB['admins'])}\n\n"
        for uid in DB['admins']:
            text += f"`{uid}`\n"
        btns = [
            [Button.inline("اضافة ادمن", b"add_admin"), Button.inline("حذف ادمن", b"del_admin")],
            [Button.inline("رجوع", b"back")]
        ]
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(data=b"add_admin"))
    async def add_admin(event):
        if event.sender_id!= DEV_ID: return
        set_state(event.sender_id, "wait_admin_add")
        await save_db()
        await event.edit("ابعت ايدي الادمن الجديد", buttons=[[Button.inline("رجوع", b"admins")]])

    @bot.on(events.CallbackQuery(data=b"del_admin"))
    async def del_admin(event):
        if event.sender_id!= DEV_ID: return
        set_state(event.sender_id, "wait_admin_del")
        await save_db()
        await event.edit("ابعت ايدي الادمن للحذف", buttons=[[Button.inline("رجوع", b"admins")]])

    @bot.on(events.CallbackQuery(data=b"settings"))
    async def settings(event):
        if not is_admin(event.sender_id): return
        s = DB["settings"]
        text = f"**الاعدادات العامة**\n\n"
        text += f"المؤقت العام: {s['global_timeout']} دقيقة\n\n"
        text += f"**الرسالة الافتراضية:**\n{s['default_verify_msg'][:100]}...\n\n"
        text += f"**الزر الافتراضي:** {s['default_button']}"

        btns = [
            [Button.inline("تعديل المؤقت العام", b"edit_global_timeout")],
            [Button.inline("تعديل الرسالة الافتراضية", b"edit_default_msg")],
            [Button.inline("تعديل الزر الافتراضي", b"edit_default_btn")],
            [Button.inline("رجوع", b"back")]
        ]
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(data=b"edit_global_timeout"))
    async def edit_global_timeout(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_global_timeout")
        await save_db()
        await event.edit("ابعت عدد الدقايق للمؤقت العام", buttons=[[Button.inline("رجوع", b"settings")]])

    @bot.on(events.CallbackQuery(data=b"edit_default_msg"))
    async def edit_default_msg(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_default_msg")
        await save_db()
        await event.edit("ابعت الرسالة الافتراضية الجديدة\n\nالمتغيرات: {name} {group}", buttons=[[Button.inline("رجوع", b"settings")]])

    @bot.on(events.CallbackQuery(data=b"edit_default_btn"))
    async def edit_default_btn(event):
        if not is_admin(event.sender_id): return
        set_state(event.sender_id, "wait_default_btn")
        await save_db()
        await event.edit("ابعت نص الزر الافتراضي الجديد", buttons=[[Button.inline("رجوع", b"settings")]])

    @bot.on(events.CallbackQuery(data=b"back"))
    async def back(event):
        await start_cmd(event)

    @bot.on(events.Raw)
    async def join_handler(event):
        if isinstance(event, UpdateBotChatInviteRequester):
            print(f"✅ طلب انضمام جديد!")
            chat_id = event.peer.channel_id if isinstance(event.peer, PeerChannel) else event.peer.chat_id
            user_id = event.user_id
            chat_id_str = str(-1000000000000 - chat_id) if chat_id > 0 else str(chat_id)

            if chat_id_str not in DB["groups"]:
                print("❌ الجروب مش في الداتا")
                return

            g = DB["groups"][chat_id_str]
            if not g["enabled"]:
                print("❌ الجروب معطل")
                return

            # قائمة سوداء
            if user_id in DB["blacklist"]:
                try:
                    await bot(functions.messages.HideChatJoinRequestRequest(
                        peer=int(chat_id_str), user_id=user_id, approved=False
                    ))
                    DB["stats"]["rejected"] += 1
                    if chat_id_str not in DB["group_stats"]:
                        DB["group_stats"][chat_id_str] = {"approved": 0, "rejected": 0}
                    DB["group_stats"][chat_id_str]["rejected"] += 1
                    add_log(user_id, chat_id_str, "blacklist")
                    await save_db()
                except: pass
                return

            # قائمة بيضاء
            if user_id in DB["whitelist"]:
                try:
                    await bot(functions.messages.HideChatJoinRequestRequest(
                        peer=int(chat_id_str), user_id=user_id, approved=True
                    ))
                    DB["stats"]["approved"] += 1
                    if chat_id_str not in DB["group_stats"]:
                        DB["group_stats"][chat_id_str] = {"approved": 0, "rejected": 0}
                    DB["group_stats"][chat_id_str]["approved"] += 1
                    add_log(user_id, chat_id_str, "whitelist")
                    await save_db()
                except: pass
                return

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

            cfg = get_group_config(chat_id_str)
            msg = cfg["verify_msg"].format(name=user_name, group=group_name)
            markup = build_button_markup(user_id, chat_id_str)

            try:
                await bot.send_message(user_id, msg, buttons=markup)
                print(f"✅ تم ارسال التحقق خاص لـ {user_id}")
            except Exception as e:
                print(f"❌ فشل الخاص: {e} - هبعت في الجروب")
                try:
                    mention = f"[{user_name}](tg://user?id={user_id})"
                    bot_username = (await bot.get_me()).username
                    deep_link = f"https://t.me/{bot_username}?start=verify_{user_id}_{chat_id_str}"

                    await bot.send_message(
                        int(chat_id_str),
                        f"👋 {mention}\n\n"
                        f"اضغط الزر تحت عشان نتحقق منك ونقبلك في الجروب\n"
                        f"⏰ عندك {cfg['timeout']} دقيقة",
                        buttons=[[Button.url("🔐 بدء التحقق", deep_link)]],
                        parse_mode='md'
                    )
                    print(f"✅ تم ارسال التحقق في الجروب لـ {user_id}")
                except Exception as e2:
                    print(f"❌ فشل الارسال في الجروب: {e2}")

    @bot.on(events.CallbackQuery(pattern=b"v_"))
    async def verify(event):
        try:
            parts = event.data.decode().split("_")
            user_id = int(parts[1])
            group_id = parts[2]

            if event.sender_id!= user_id:
                return await event.answer("الزر ده مش ليك", alert=True)

            if str(user_id) not in DB["pending"]:
                return await event.answer("الطلب انتهى", alert=True)

            await bot(functions.messages.HideChatJoinRequestRequest(
                peer=int(group_id), user_id=user_id, approved=True
            ))

            del DB["pending"][str(user_id)]
            DB["stats"]["approved"] += 1
            if group_id not in DB["group_stats"]:
                DB["group_stats"][group_id] = {"approved": 0, "rejected": 0}
            DB["group_stats"][group_id]["approved"] += 1
            add_log(user_id, group_id, "approved")
            await save_db()

            cfg = get_group_config(group_id)
            await event.edit(
                cfg["success_msg"].format(group=cfg["name"]),
                buttons=[[Button.url("المبرمج", f"https://t.me/{DEV_USERNAME}")]]
            )
        except Exception as e:
            await event.answer(f"خطأ: {str(e)}", alert=True)

    @bot.on(events.NewMessage)
    async def handle_input(event):
        if not is_admin(event.sender_id): return
        state = get_state(event.sender_id)
        if not state: return

        if state == "wait_gid":
            clear_state(event.sender_id)
            try:
                text = event.text.strip()
                if text.startswith('https://t.me/'):
                    username = text.split('/')[-1].replace('+', '')
                    entity = await bot.get_entity(username)
                    gid = str(entity.id)
                    name = entity.title
                elif text.startswith('@'):
                    entity = await bot.get_entity(text)
                    gid = str(entity.id)
                    name = entity.title
                else:
                    gid = text
                    entity = await bot.get_entity(int(gid))
                    name = entity.title

                DB["groups"][gid] = {"name": name, "enabled": True}
                if gid not in DB["group_stats"]:
                    DB["group_stats"][gid] = {"approved": 0, "rejected": 0}
                saved = await save_db()
                status = "تم الحفظ" if saved else "فشل الحفظ"
                await event.reply(f"{status}\n\nتم اضافة: {name}\n`{gid}`")
            except ValueError:
                await event.reply(
                    "فشل الاضافة\n\n"
                    "لازم:\n"
                    "1. تضيف البوت ادمن في الجروب الاول\n"
                    "2. او تعمل Forward لرسالة من الجروب\n"
                    "3. او تستخدم @username"
                )
            except Exception as e:
                await event.reply(f"فشل: {e}")

        elif state.startswith("wait_msg_"):
            gid = state.split("_", 2)[2]
            clear_state(event.sender_id)
            if gid in DB["groups"]:
                DB["groups"][gid]["verify_msg"] = event.text
                await save_db()
                await event.reply("تم حفظ رسالة التحقق")

        elif state.startswith("wait_btn_"):
            gid = state.split("_", 2)[2]
            clear_state(event.sender_id)
            if gid in DB["groups"]:
                DB["groups"][gid]["button_text"] = event.text
                await save_db()
                await event.reply("تم حفظ نص الزر")

        elif state.startswith("wait_timeout_"):
            gid = state.split("_", 2)[2]
            clear_state(event.sender_id)
            try:
                timeout = int(event.text)
                if gid in DB["groups"]:
                    DB["groups"][gid]["timeout"] = timeout
                    await save_db()
                    await event.reply(f"تم ضبط المؤقت: {timeout} دقيقة")
            except:
                await event.reply("ارسل رقم صحيح")

        elif state == "wait_black_add":
            clear_state(event.sender_id)
            try:
                uid = int(event.text)
                if uid not in DB["blacklist"]:
                    DB["blacklist"].append(uid)
                    await save_db()
                    await event.reply(f"تم الحظر: `{uid}`")
            except:
                await event.reply("ايدي غير صحيح")

        elif state == "wait_black_del":
            clear_state(event.sender_id)
            try:
                uid = int(event.text)
                if uid in DB["blacklist"]:
                    DB["blacklist"].remove(uid)
                    await save_db()
                    await event.reply(f"تم الحذف: `{uid}`")
            except:
                await event.reply("ايدي غير صحيح")

        elif state == "wait_white_add":
            clear_state(event.sender_id)
            try:
                uid = int(event.text)
                if uid not in DB["whitelist"]:
                    DB["whitelist"].append(uid)
                    await save_db()
                    await event.reply(f"تم الاضافة: `{uid}`")
            except:
                await event.reply("ايدي غير صحيح")

        elif state == "wait_white_del":
            clear_state(event.sender_id)
            try:
                uid = int(event.text)
                if uid in DB["whitelist"]:
                    DB["whitelist"].remove(uid)
                    await save_db()
                    await event.reply(f"تم الحذف: `{uid}`")
            except:
                await event.reply("ايدي غير صحيح")

        elif state == "wait_admin_add":
            clear_state(event.sender_id)
            try:
                uid = int(event.text)
                if uid not in DB["admins"]:
                    DB["admins"].append(uid)
                    await save_db()
                    await event.reply(f"تم اضافة ادمن: `{uid}`")
            except:
                await event.reply("ايدي غير صحيح")

        elif state == "wait_admin_del":
            clear_state(event.sender_id)
            try:
                uid = int(event.text)
                if uid in DB["admins"] and uid!= DEV_ID:
                    DB["admins"].remove(uid)
                    await save_db()
                    await event.reply(f"تم الحذف: `{uid}`")
            except:
                await event.reply("ايدي غير صحيح")

        elif state == "wait_global_timeout":
            clear_state(event.sender_id)
            try:
                timeout = int(event.text)
                DB["settings"]["global_timeout"] = timeout
                await save_db()
                await event.reply(f"تم ضبط المؤقت العام: {timeout} دقيقة")
            except:
                await event.reply("ارسل رقم صحيح")

        elif state == "wait_default_msg":
            clear_state(event.sender_id)
            DB["settings"]["default_verify_msg"] = event.text
            await save_db()
            await event.reply("تم حفظ الرسالة الافتراضية")

        elif state == "wait_default_btn":
            clear_state(event.sender_id)
            DB["settings"]["default_button"] = event.text
            await save_db()
            await event.reply("تم حفظ الزر الافتراضي")

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود")
        return
    await setup_bot()
    print("✅ V20.2 Bot Running")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
