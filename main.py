import os, asyncio, json, datetime
from telethon import TelegramClient, events, Button, functions, types
from telethon.tl.types import UpdateBotChatInviteRequester, PeerChannel, MessageEntityCustomEmoji, KeyboardButtonCallback, ReplyInlineMarkup, KeyboardButtonRow

API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEV_ID = 154919127
DEV_USERNAME = "Devazf"

DB_FILE = "join_requests.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {
        "groups": {},
        "pending": {},
        "stats": {"approved": 0, "rejected": 0},
        "verify_msg": "مرحباً {name} 👋\n\nاضغط على الزر عشان نتحقق انك لست روبوت ونقبلك في {group} ✅",
        "verify_msg_entities": [],
        "success_msg": "✅ **تم التحقق بنجاح**\n\nتم قبولك في {group}\nتقدر تدخل دلوقتي 🎉\n\n💎 بوت مجاني من @Devazf",
        "success_msg_entities": [],
        "button_text": "✅ تحقق انك لست روبوت",
        "button_entities": []
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(DB, f, indent=2, ensure_ascii=False)

DB = load_db()
bot = None

def build_button_markup(user_id, group_id):
    """بناء زر مع دعم ايموجي بريميوم"""
    button_text = DB["button_text"]
    button_entities = []
    for e in DB.get("button_entities", []):
        if e.get('_') == 'MessageEntityCustomEmoji':
            button_entities.append(types.MessageEntityCustomEmoji(e['offset'], e['length'], e['document_id']))

    btn = KeyboardButtonCallback(
        text=button_text,
        data=f"verify_{user_id}_{group_id}".encode(),
        text_entities=button_entities if button_entities else None
    )
    return ReplyInlineMarkup([KeyboardButtonRow([btn])])

async def setup_bot():
    global bot
    bot = TelegramClient('join_bot', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    @bot.on(events.NewMessage(pattern='/start'))
    async def start_cmd(event):
        is_admin = event.sender_id == DEV_ID

        if is_admin:
            btns = [
                [Button.inline("➕ اضافة جروب/قناة", b"add_group")],
                [Button.inline("📝 الجروبات المفعلة", b"list_groups")],
                [Button.inline("📊 الاحصائيات", b"stats"), Button.inline("⚙️ الاعدادات", b"settings")],
                [Button.url("💬 مراسلة المبرمج", f"https://t.me/{DEV_USERNAME}")]
            ]
            await event.reply(
                f"🤖 **بوت الموافقة التلقائية V2.5**\n\n"
                f"👑 **لوحة المطور**\n\n"
                f"الجروبات المفعلة: {len(DB['groups'])}\n"
                f"تم قبول: {DB['stats']['approved']}\n"
                f"تم رفض: {DB['stats']['rejected']}\n\n"
                f"💎 **يدعم ايموجي بريميوم في الازرار**\n"
                f"**البوت شغال للجميع مجاناً**",
                buttons=btns
            )
        else:
            total_approved = DB['stats']['approved']
            btns = [
                [Button.url("➕ ضيف البوت لجروبك", f"https://t.me/{(await bot.get_me()).username}?startgroup=true")],
                [Button.url("💬 مراسلة المبرمج", f"https://t.me/{DEV_USERNAME}")]
            ]
            await event.reply(
                f"🤖 **بوت الموافقة التلقائية**\n\n"
                f"البوت ده بيقبل طلبات الانضمام تلقائياً بعد التحقق انك لست روبوت ✅\n\n"
                f"📊 **تم قبول {total_approved} عضو لحد دلوقتي**\n\n"
                f"**مجاناً 100%** للجميع 💎\n\n"
                f"عايز تضيف البوت لجروبك؟ دوس على الزر تحت 👇\n"
                f"لازم تكون ادمن وتديله صلاحية 'اضافة اعضاء'",
                buttons=btns
            )

    @bot.on(events.CallbackQuery(data=b"add_group"))
    async def add_group(event):
        if event.sender_id!= DEV_ID:
            return await event.answer("❌ للمطور فقط", alert=True)
        await event.edit(
            "➕ **اضافة جروب/قناة**\n\n"
            "1. ضيف البوت ادمن في الجروب\n"
            "2. اديله صلاحية 'اضافة اعضاء'\n"
            "3. ابعت ايدي الجروب هنا\n\n"
            "مثال: `-1001234567890`\n\n"
            "او ابعت لينك الجروب",
            buttons=[[Button.inline("🔙", b"back_admin")]]
        )
        bot.wait_group_id = True

    @bot.on(events.CallbackQuery(data=b"list_groups"))
    async def list_groups(event):
        if event.sender_id!= DEV_ID:
            return await event.answer("❌ للمطور فقط", alert=True)
        if not DB["groups"]:
            return await event.edit("❌ مفيش جروبات مفعلة", buttons=[[Button.inline("🔙", b"back_admin")]])

        text = "📝 **الجروبات المفعلة:**\n\n"
        btns = []
        for gid, data in DB["groups"].items():
            status = "✅ مفعل" if data["enabled"] else "❌ معطل"
            text += f"• {data['name']}\n`{gid}` | {status}\n\n"
            btns.append([Button.inline(f"{'⏸️ ايقاف' if data['enabled'] else '▶️ تفعيل'} {data['name'][:20]}", f"toggle_{gid}".encode())])

        btns.append([Button.inline("🔙", b"back_admin")])
        await event.edit(text, buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"toggle_"))
    async def toggle_group(event):
        if event.sender_id!= DEV_ID: return
        gid = event.data.decode().split("_")[1]
        if gid in DB["groups"]:
            DB["groups"][gid]["enabled"] = not DB["groups"][gid]["enabled"]
            save_db()
            status = "تم التفعيل ✅" if DB["groups"][gid]["enabled"] else "تم الايقاف ❌"
            await event.answer(status, alert=True)
            await list_groups(event)

    @bot.on(events.CallbackQuery(data=b"stats"))
    async def stats(event):
        if event.sender_id!= DEV_ID:
            return await event.answer("❌ للمطور فقط", alert=True)
        approved = DB['stats']['approved']
        rejected = DB['stats']['rejected']
        total = approved + rejected
        rate = (approved / total * 100) if total > 0 else 0

        txt = f"📊 **احصائيات البوت**\n\n"
        txt += f"✅ تم قبول: {approved}\n"
        txt += f"❌ تم رفض: {rejected}\n"
        txt += f"📈 الاجمالي: {total}\n"
        txt += f"📉 نسبة القبول: {rate:.1f}%\n\n"
        txt += f"👥 الجروبات المفعلة: {len([g for g in DB['groups'].values() if g['enabled']])}"

        await event.edit(txt, buttons=[[Button.inline("🔙", b"back_admin")]])

    @bot.on(events.CallbackQuery(data=b"settings"))
    async def settings(event):
        if event.sender_id!= DEV_ID:
            return await event.answer("❌ للمطور فقط", alert=True)
        btns = [
            [Button.inline("✏️ تعديل رسالة التحقق", b"edit_verify_msg")],
            [Button.inline("✅ تعديل رسالة النجاح", b"edit_success_msg")],
            [Button.inline("🔤 تعديل نص الزر", b"edit_btn")],
            [Button.inline("👁️ معاينة كل الرسائل", b"preview_msgs")],
            [Button.inline("🔙", b"back_admin")]
        ]
        await event.edit(
            "⚙️ **الاعدادات**\n\n"
            "كل الرسايل والازرار تدعم:\n"
            "• ايموجي بريميوم من تيليجرام 💎\n"
            "• تنسيق: بولد/ايتاليك/كود\n"
            "• متغيرات: {name} {group}\n\n"
            "✅ **الايموجي البريميوم هيظهر في الازرار طالما حسابك بريميوم**",
            buttons=btns
        )

    @bot.on(events.CallbackQuery(data=b"edit_verify_msg"))
    async def edit_verify_msg(event):
        if event.sender_id!= DEV_ID: return
        await event.edit(
            "✏️ **تعديل رسالة التحقق**\n\n"
            "ابعت الرسالة الجديدة اللي هتتبعت للمستخدمين\n\n"
            "**يدعم:**\n"
            "• ايموجي بريميوم من تيليجرام 💎\n"
            "• تنسيق: بولد/ايتاليك/كود\n"
            "• متغيرات: {name} {group}",
            buttons=[[Button.inline("🔙", b"settings")]]
        )
        bot.wait_verify_msg = True

    @bot.on(events.CallbackQuery(data=b"edit_success_msg"))
    async def edit_success_msg(event):
        if event.sender_id!= DEV_ID: return
        await event.edit(
            "✅ **تعديل رسالة النجاح**\n\n"
            "ابعت الرسالة اللي هتظهر بعد التحقق\n\n"
            "**يدعم:**\n"
            "• ايموجي بريميوم 💎\n"
            "• تنسيق كامل\n"
            "• متغير: {group}",
            buttons=[[Button.inline("🔙", b"settings")]]
        )
        bot.wait_success_msg = True

    @bot.on(events.CallbackQuery(data=b"edit_btn"))
    async def edit_btn(event):
        if event.sender_id!= DEV_ID: return
        await event.edit(
            "🔤 **تعديل نص الزر**\n\n"
            "ابعت النص الجديد للزر مع الايموجي البريميوم\n\n"
            "**طريقة اضافة ايموجي بريميوم:**\n"
            "1. افتح اي شات عندك فيه ايموجي بريميوم\n"
            "2. دوس مطول على الايموجي → نسخ\n"
            "3. ابعته هنا في الرسالة\n\n"
            "**مثال:**\n"
            "`✅ تحقق انك لست روبوت` + ايموجي بريميوم\n\n"
            "💎 **هيظهر للكل طالما حسابك بريميوم**",
            buttons=[[Button.inline("🔙", b"settings")]]
        )
        bot.wait_btn = True

    @bot.on(events.CallbackQuery(data=b"preview_msgs"))
    async def preview_msgs(event):
        if event.sender_id!= DEV_ID:
            return await event.answer("❌ للمطور فقط", alert=True)

        await event.answer("جاري ارسال المعاينة...", alert=False)

        verify_entities = []
        for e in DB.get("verify_msg_entities", []):
            if e.get('_') == 'MessageEntityCustomEmoji':
                verify_entities.append(types.MessageEntityCustomEmoji(e['offset'], e['length'], e['document_id']))
        verify_text = DB["verify_msg"].format(name="محمد", group="جروب تجريبي")

        success_entities = []
        for e in DB.get("success_msg_entities", []):
            if e.get('_') == 'MessageEntityCustomEmoji':
                success_entities.append(types.MessageEntityCustomEmoji(e['offset'], e['length'], e['document_id']))
        success_text = DB["success_msg"].format(group="جروب تجريبي")

        try:
            await bot.send_message(event.chat_id, f"**1️⃣ رسالة التحقق:**\n\n{verify_text}", entities=verify_entities)
            await bot.send_message(event.chat_id, f"**2️⃣ رسالة النجاح:**\n\n{success_text}", entities=success_entities)

            markup = build_button_markup(12345, "-1001234567890")
            await bot.send_message(event.chat_id, f"**3️⃣ معاينة الزر مع الايموجي البريميوم:**", buttons=markup)
        except Exception as e:
            await bot.send_message(event.chat_id, f"❌ خطأ في المعاينة: {e}")

    @bot.on(events.CallbackQuery(data=b"back_admin"))
    async def back_admin(event):
        if event.sender_id!= DEV_ID: return
        await start_cmd(event)

    @bot.on(events.Raw)
    async def join_request_handler(event):
        if isinstance(event, UpdateBotChatInviteRequester):
            chat_id = event.peer.channel_id if isinstance(event.peer, PeerChannel) else event.peer.chat_id
            user_id = event.user_id
            chat_id_str = str(-1000000000000 - chat_id) if chat_id > 0 else str(chat_id)

            if chat_id_str not in DB["groups"] or not DB["groups"][chat_id_str]["enabled"]:
                return

            group_data = DB["groups"][chat_id_str]

            DB["pending"][str(user_id)] = {
                "group_id": chat_id_str,
                "chat_id": event.invite.chat_id,
                "time": datetime.datetime.now().isoformat()
            }
            save_db()

            try:
                user = await bot.get_entity(user_id)
                chat = await bot.get_entity(int(chat_id_str))
                user_name = user.first_name
                group_name = chat.title
            except:
                user_name = "صديقي"
                group_name = group_data["name"]

            msg = DB["verify_msg"].format(name=user_name, group=group_name)
            entities = []
            for e in DB.get("verify_msg_entities", []):
                if e.get('_') == 'MessageEntityCustomEmoji':
                    entities.append(types.MessageEntityCustomEmoji(e['offset'], e['length'], e['document_id']))

            markup = build_button_markup(user_id, chat_id_str)

            try:
                await bot.send_message(user_id, msg, buttons=markup, entities=entities)
            except:
                try:
                    await bot(functions.messages.HideChatJoinRequestRequest(
                        peer=int(chat_id_str),
                        user_id=user_id,
                        approved=False
                    ))
                    DB["stats"]["rejected"] += 1
                    save_db()
                except: pass

    @bot.on(events.CallbackQuery(pattern=b"verify_"))
    async def verify_user(event):
        try:
            parts = event.data.decode().split("_")
            user_id = int(parts[1])
            group_id = parts[2]

            if event.sender_id!= user_id:
                return await event.answer("❌ الزر ده مش ليك", alert=True)

            if str(user_id) not in DB["pending"]:
                return await event.answer("❌ الطلب ده انتهى", alert=True)

            await bot(functions.messages.HideChatJoinRequestRequest(
                peer=int(group_id),
                user_id=user_id,
                approved=True
            ))

            del DB["pending"][str(user_id)]
            DB["stats"]["approved"] += 1
            save_db()

            group_name = DB["groups"][group_id]["name"]
            success_text = DB["success_msg"].format(group=group_name)
            success_entities = []
            for e in DB.get("success_msg_entities", []):
                if e.get('_') == 'MessageEntityCustomEmoji':
                    success_entities.append(types.MessageEntityCustomEmoji(e['offset'], e['length'], e['document_id']))

            await event.edit(
                success_text,
                entities=success_entities,
                buttons=[[Button.url("💬 مراسلة المبرمج", f"https://t.me/{DEV_USERNAME}")]]
            )

        except Exception as e:
            await event.answer(f"❌ حصل خطأ: {str(e)}", alert=True)

    @bot.on(events.NewMessage)
    async def handle_input(event):
        if event.sender_id!= DEV_ID: return

        if hasattr(bot, 'wait_group_id') and bot.wait_group_id:
            bot.wait_group_id = False
            try:
                text = event.text.strip()
                if text.startswith('https://t.me/'):
                    username = text.split('/')[-1]
                    entity = await bot.get_entity(username)
                    gid = str(entity.id)
                    name = entity.title
                else:
                    gid = text
                    entity = await bot.get_entity(int(gid))
                    name = entity.title

                DB["groups"][gid] = {
                    "name": name,
                    "enabled": True
                }
                save_db()
                await event.reply(f"✅ تم اضافة الجروب:\n\n{name}\n`{gid}`\n\nالبوت جاهز يستقبل طلبات الانضمام 🎉")
            except Exception as e:
                await event.reply(f"❌ فشل الاضافة\n\nتأكد ان:\n1. البوت ادمن في الجروب\n2. عنده صلاحية 'اضافة اعضاء'\n\n{e}")

        elif hasattr(bot, 'wait_verify_msg') and bot.wait_verify_msg:
            bot.wait_verify_msg = False
            DB["verify_msg"] = event.message.text
            DB["verify_msg_entities"] = [e.to_dict() for e in event.message.entities or []]
            save_db()
            await event.reply("✅ تم حفظ رسالة التحقق بنجاح 💎")

        elif hasattr(bot, 'wait_success_msg') and bot.wait_success_msg:
            bot.wait_success_msg = False
            DB["success_msg"] = event.message.text
            DB["success_msg_entities"] = [e.to_dict() for e in event.message.entities or []]
            save_db()
            await event.reply("✅ تم حفظ رسالة النجاح بنجاح 💎")

        elif hasattr(bot, 'wait_btn') and bot.wait_btn:
            bot.wait_btn = False
            DB["button_text"] = event.message.text
            DB["button_entities"] = [e.to_dict() for e in event.message.entities or []]
            save_db()
            await event.reply(
                f"✅ تم حفظ نص الزر مع الايموجي البريميوم 💎\n\n"
                f"النص: {event.message.text}\n\n"
                f"الايموجي هيظهر للكل طالما حسابك بريميوم"
            )

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود")
        return
    await setup_bot()
    print("✅ بوت الموافقة التلقائية V2.5 شغال - ايموجي بريميوم في الازرار")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
