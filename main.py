import os, asyncio, json, datetime
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import HideChatJoinRequestRequest, ApproveChatJoinRequestRequest
from telethon.tl.types import UpdateBotChatInviteRequester, PeerChannel, MessageEntityCustomEmoji

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
                f"🤖 **بوت الموافقة التلقائية V2.1**\n\n"
                f"👑 **لوحة الادمن**\n\n"
                f"الجروبات المفعلة: {len(DB['groups'])}\n"
                f"تم قبول: {DB['stats']['approved']}\n"
                f"تم رفض: {DB['stats']['rejected']}\n\n"
                f"**المميزات:**\n"
                f"✅ دعم ايموجي بريميوم في الرسائل والازرار\n"
                f"✅ رسائل مخصصة بالكامل\n"
                f"✅ تحقق تلقائي\n\n"
                f"**طريقة التشغيل:**\n"
                f"1. ضيف البوت ادمن في الجروب\n"
                f"2. فعل صلاحية 'اضافة اعضاء'\n"
                f"3. فعل الجروب من هنا",
                buttons=btns
            )
        else:
            btns = [[Button.url("💬 مراسلة المبرمج", f"https://t.me/{DEV_USERNAME}")]]
            await event.reply(
                f"🤖 **بوت الموافقة التلقائية**\n\n"
                f"البوت ده بيقبل طلبات الانضمام تلقائياً بعد التحقق انك لست روبوت ✅\n\n"
                f"**مجاناً 100%** للجميع 💎\n\n"
                f"لو عندك جروب وعايز تضيف البوت تواصل مع المبرمج 👇",
                buttons=btns
            )

    @bot.on(events.CallbackQuery(data=b"add_group"))
    async def add_group(event):
        if event.sender_id!= DEV_ID: return
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
        if event.sender_id!= DEV_ID: return
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
        if event.sender_id!= DEV_ID: return
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
        if event.sender_id!= DEV_ID: return
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
            "• متغيرات: {name} {group}",
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
            "• متغيرات: {name} {group}\n\n"
            "**مثال:**\n"
            "مرحباً {name} 👋\n\n"
            "اضغط الزر عشان تنضم لـ {group} 💎",
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
            "• متغير: {group}\n\n"
            "**الافتراضي:**\n"
            "✅ **تم التحقق بنجاح**\n\n"
            "تم قبولك في {group}\n"
            "تقدر تدخل دلوقتي 🎉",
            buttons=[[Button.inline("🔙", b"settings")]]
        )
        bot.wait_success_msg = True

    @bot.on(events.CallbackQuery(data=b"edit_btn"))
    async def edit_btn(event):
        if event.sender_id!= DEV_ID: return
        await event.edit(
            "🔤 **تعديل نص الزر**\n\n"
            "ابعت النص الجديد للزر\n\n"
            "**يدعم:**\n"
            "• ايموجي بريميوم 💎\n"
            "• ايموجي عادي\n\n"
            "**الافتراضي:**\n"
            "`✅ تحقق انك لست روبوت`\n\n"
            "**مثال مع بريميوم:**\n"
            "اضغط عشان تنضم 💎",
            buttons=[[Button.inline("🔙", b"settings")]]
        )
        bot.wait_btn = True

    @bot.on(events.CallbackQuery(data=b"preview_msgs"))
    async def preview_msgs(event):
        if event.sender_id!= DEV_ID: return
        
        await event.edit("👁️ **معاينة الرسائل**\n\nجاري الارسال...")
        
        # معاينة رسالة التحقق
        verify_entities = [MessageEntityCustomEmoji.from_dict(e) if e.get('_') == 'MessageEntityCustomEmoji' else e for e in DB.get("verify_msg_entities", [])]
        verify_text = DB["verify_msg"].format(name="محمد", group="جروب تجريبي")
        
        # معاينة رسالة النجاح
        success_entities = [MessageEntityCustomEmoji.from_dict(e) if e.get('_') == 'MessageEntityCustomEmoji' else e for e in DB.get("success_msg_entities", [])]
        success_text = DB["success_msg"].format(group="جروب تجريبي")
        
        # معاينة الزر
        button_entities = [MessageEntityCustomEmoji.from_dict(e) if e.get('_') == 'MessageEntityCustomEmoji' else e for e in DB.get("button_entities", [])]
        button_text = DB["button_text"]
        
        try:
            await bot.send_message(event.chat_id, f"**1️⃣ رسالة التحقق:**\n\n{verify_text}", entities=verify_entities)
            await bot.send_message(event.chat_id, f"**2️⃣ رسالة النجاح:**\n\n{success_text}", entities=success_entities)
            await bot.send_message(event.chat_id, f"**3️⃣ الزر:**\n\nنص الزر: {button_text}", entities=button_entities, buttons=[[Button.inline(button_text, b"test_btn", entities=button_entities)]])
        except Exception as e:
            await bot.send_message(event.chat_id, f"❌ خطأ في المعاينة: {e}")
        
        await event.edit("✅ تم ارسال المعاينة", buttons=[[Button.inline("🔙", b"settings")]])

    @bot.on(events.CallbackQuery(data=b"back_admin"))
    async def back_admin(event):
        if event.sender_id!= DEV_ID: return
        await start_cmd(event)

    # التقاط طلبات الانضمام
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
            
            # رسالة التحقق مع entities
            msg = DB["verify_msg"].format(name=user_name, group=group_name)
            entities = [MessageEntityCustomEmoji.from_dict(e) if e.get('_') == 'MessageEntityCustomEmoji' else e for e in DB.get("verify_msg_entities", [])]
            
            # الزر مع entities
            button_entities = [MessageEntityCustomEmoji.from_dict(e) if e.get('_') == 'MessageEntityCustomEmoji' else e for e in DB.get("button_entities", [])]
            btns = [[Button.inline(DB["button_text"], f"verify_{user_id}_{chat_id_str}".encode(), entities=button_entities)]]
            
            try:
                await bot.send_message(user_id, msg, buttons=btns, entities=entities)
            except:
                await bot(HideChatJoinRequestRequest(peer=int(chat_id_str), user_id=user_id))
                DB["stats"]["rejected"] += 1
                save_db()

    # زر التحقق
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
            
            await bot(ApproveChatJoinRequestRequest(peer=int(group_id), user_id=user_id))
            
            del DB["pending"][str(user_id)]
            DB["stats"]["approved"] += 1
            save_db()
            
            group_name = DB["groups"][group_id]["name"]
            
            # رسالة النجاح مع entities
            success_text = DB["success_msg"].format(group=group_name)
            success_entities = [MessageEntityCustomEmoji.from_dict(e) if e.get('_') == 'MessageEntityCustomEmoji' else e for e in DB.get("success_msg_entities", [])]
            
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
            await event.reply("✅ تم تعديل رسالة التحقق\n\nجرب /start وشوف المعاينة 👁️")

        elif hasattr(bot, 'wait_success_msg') and bot.wait_success_msg:
            bot.wait_success_msg = False
            DB["success_msg"] = event.message.text
            DB["success_msg_entities"] = [e.to_dict() for e in event.message.entities or []]
            save_db()
            await event.reply("✅ تم تعديل رسالة النجاح\n\nجرب /start وشوف المعاينة 👁️")

        elif hasattr(bot, 'wait_btn') and bot.wait_btn:
            bot.wait_btn = False
            DB["button_text"] = event.message.text
            DB["button_entities"] = [e.to_dict() for e in event.message.entities or []]
            save_db()
            await event.reply(f"✅ تم تعديل نص الزر لـ:\n`{event.message.text}`\n\nجرب /start وشوف المعاينة 👁️")

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود")
        return
    await setup_bot()
    print("✅ بوت الموافقة التلقائية شغال")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
