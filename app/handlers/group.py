import random

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType

from app.database import db
from app.services.groq_ai import ask_groq
from app.services.moderation import check_message
from app import config

router = Router()

SYSTEM_PROMPT = """
Siz Mariya — o'zbekcha suhbatlashadigan, sho'x, topqir, kinoyali va achchiq tilli sun'iy intellektsiz.

TIL VA TUSHUNISH:
1. Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob bering.
2. O'zbek tilida sodda, ravon, grammatik jihatdan to'g'ri va tabiiy gapiring.
3. So'zlarni shunchaki alohida ma'nosi bilan emas, butun gap va suhbat kontekstiga qarab tushuning.
4. Ko'cha tili, jargon, qisqartmalar, imlo xatolari, shevaga xos so'zlar, so'kinishlar va norasmiy iboralarni imkon qadar anglang.
5. "Gap yo'q", "zo'r ekansan-da", "barakalla", "o'libsan-ku" kabi iboralar vaziyatga qarab maqtov, kinoya yoki hazil bo'lishi mumkin. Ma'nosini kontekstdan aniqlang, bitta iboraga qarab xulosa qilmang.
6. Sarkazm, istehzo, piching va yashirin ma'noni aniqlash uchun oldingi xabarlar, suhbat ohangi va kimga murojaat qilinayotganini hisobga oling.
7. Haqoratli so'z ishlatilsa, darhol janjal deb qabul qilmang. Bu do'stona hazilmi, o'zaro gap qaytarishmi yoki jiddiy adovatmi — kontekstga qarab farqlang.
8. Ibora yoki xabarning ma'nosi aniq bo'lmasa, o'zingizdan ma'no to'qimang. Qisqa savol bilan aniqlashtiring yoki ehtiyotkor javob bering.

SUHBAT USLUBI:
1. Javobni avval suhbatning asl mazmuniga moslang.
2. Oddiy savolga aniq javob bering; har bir xabarni hazilga aylantirmang.
3. Hazil yoki kinoya bo'lsa, tabiiy, topqir va vaziyatga mos tarzda javob qaytaring.
4. Sizga do'stona tegishsa, yengil va o'tkir hazil bilan gap qaytarishingiz mumkin.
5. Bir xil hazil va iboralarni qayta-qayta ishlatmang.
6. Foydalanuvchi jiddiy yoki xafa bo'lib yozsa, vaziyatni hisobga oling va masxara qilmang.
7. Keraksiz rasmiy iboralar, uzun kirishlar va sun'iy ohangdan qoching.
8. Odatda 1–3 jumlada javob bering. Murakkab savol bo'lsa, batafsil tushuntiring.
9. Foydalanuvchining gapida xato bo'lsa, ma'nosi tushunarli paytda xatoni debatga aylantirmang.
10. Haqoratni tushunish uni doim takrorlash yoki yanada qo'pol gapirish kerakligini anglatmaydi. Qo'pol so'zlarni faqat kontekst uchun zarur bo'lsa ishlating.
11. Tahdid qilmang, nafratni targ'ib qilmang, janjalni kuchaytirmang. Tashqi ko'rinish, sog'liq, nogironlik yoki nozik shaxsiy xususiyatlarni nishonga olib kamsitmang.
12. Bilmagan ma'lumotni to'qimang. O'yin va texnologiya haqidagi savollarga imkon qadar aniq javob bering.
13. Har bir xabarga javob berish shart emas. Qisqa va ma'nosiz xabarga vaziyatga qarab munosabat bildiring yoki javob bermang.
14. O'zingiz haqingizda so'ralsa, Mariya ismli sun'iy intellekt ekaningizni ayting.
15. Mos joyda emoji ishlating, lekin ortiqcha ishlatmang.

KONTEKST BILAN ISHLASH:
- Joriy xabarni oldingi xabarlar bilan bog'lab tushuning.
- Foydalanuvchi kimga yoki nimaga javob qaytarayotganini aniqlashga harakat qiling.
- Hazil, kinoya, maqtov va haqoratning farqini faqat bitta so'zga qarab belgilamang.
- Oldingi suhbatda aytilmagan voqealarni haqiqat deb taxmin qilmang.
- Foydalanuvchi "tushunmading" desa, avvalgi javobni takrorlamang; uning nazarda tutgan ma'nosini qayta ko'rib chiqing.

INFERIQ JAMOASI HAQIDAGI QOIDA:
- Sizni kim yaratgani so'ralsa, "Meni Inferiq jamoasi yaratgan" deb javob bering.
- Savol boshqa shaklda berilsa ham, shu javobni saqlang.
- Boshqa yaratuvchi nomini aytmang va ortiqcha izoh bermang.
"""

@router.message(F.new_chat_members)
async def welcome_new_members(message: Message):
    if await db.get_setting(message.chat.id, "welcome", "1") != "1":
        return

    from html import escape

    template = await db.get_setting(
        message.chat.id,
        "welcome_text",
        "🎉 Assalomu alaykum, {name}!\\n\\n"
        "📍 {group} guruhiga xush kelibsiz! 👋\\n\\n"
        "Bizning guruhga qo‘shildingiz — endi suhbatlar, hazillar va "
        "qiziqarli voqealar siz bilan yanada maroqli bo‘ladi. 😎\\n\\n"
        "📌 Guruh qoidalari bilan tanishib chiqing va faol bo‘ling!\\n\\n"
        "🔥 O‘zingizni erkin tuting, faqat qoidalarni unutmang!",
    )

    group_name = escape(message.chat.title or "Guruh")
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        name = escape(member.full_name)
        mention = f'<a href="tg://user?id={member.id}">{name}</a>'
        text = escape(template).replace("{name}", mention).replace(
            "{group}", group_name
        )
        await message.answer(text, parse_mode="HTML")


@router.message(F.left_chat_member)
async def farewell_member(message: Message):
    if await db.get_setting(message.chat.id, "farewell", "1") != "1":
        return

    member = message.left_chat_member
    if member.is_bot:
        return

    from html import escape

    template = await db.get_setting(
        message.chat.id,
        "farewell_text",
        "🚪 Xayr, {name}!\\n\\n"
        "📍 {group} guruhini tark etdingiz. 👋\\n\\n"
        "Suhbatlar davom etadi, xabarlar kelishda davom etadi — "
        "faqat endi ularni boshqa joydan kuzatasiz. 😏\\n\\n"
        "✨ Omad sizga! Yana qaytsangiz, eshik ochiq.",
    )

    name = escape(member.full_name)
    mention = f'<a href="tg://user?id={member.id}">{name}</a>'
    group_name = escape(message.chat.title or "Guruh")
    text = escape(template).replace("{name}", mention).replace(
        "{group}", group_name
    )
    await message.answer(text, parse_mode="HTML")


async def auto_moderation_action(message: Message, reason: str):
    if not message.from_user:
        return

    try:
        await message.delete()
    except Exception:
        pass

    count = await db.warn_user(message.chat.id, message.from_user.id)

    if count >= 3:
        try:
            from datetime import datetime, timedelta, timezone
            from aiogram.types import ChatPermissions

            until = datetime.now(timezone.utc) + timedelta(minutes=10)
            await message.bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await message.answer(
                f"🔇 {message.from_user.full_name} 10 daqiqaga cheklab qo‘yildi. "
                f"Sabab: {reason}"
            )
        except Exception as e:
            await message.answer(
                f"⚠️ Cheklash amalga oshmadi: {e}"
            )
    else:
        await message.answer(
            f"⚠️ {message.from_user.full_name}: ogohlantirish "
            f"{count}/3. Sabab: {reason}"
        )


@router.message(F.text, F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_text(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    text = (message.text or "").strip()
    if not text:
        return

    await db.register_user(message.from_user.id, message.from_user.username or "")
    await db.register_group(message.chat.id, message.chat.title or "")

    moderation = check_message(message.chat.id, message.from_user.id, text)
    if moderation == "flood":
        await auto_moderation_action(message, "Flood — juda ko‘p xabar")
        return
    if moderation == "repeat":
        await auto_moderation_action(message, "Takroriy xabar")
        return

    if moderation == "link" and await db.get_setting(message.chat.id, "block_links", "0") == "1":
        try:
            await message.delete()
            await message.answer("🔗 Guruhda havolalar taqiqlangan.")
        except Exception:
            pass
        return

    if "inferiq" in text.lower():
        await message.reply("🔗 Inferiq: https://t.me/inferiq")
        return

    bot_user = await message.bot.me()
    username = (bot_user.username or "").lower()
    addressed = (
        (message.reply_to_message is not None
         and message.reply_to_message.from_user is not None
         and message.reply_to_message.from_user.id == bot_user.id)
        or (username and f"@{username}" in text.lower())
        or text.lower().startswith("/ask")
    )
    if not addressed:
        if not config.AUTO_REPLY or random.random() > 0.10:
            return

        # Juda qisqa va faqat belgidan iborat xabarlarga o'zi javob bermasin.
        normalized = text.strip().lower()
        if len(normalized) <= 3:
            return
        if not any(ch.isalnum() for ch in normalized):
            return

    prompt = text
    if username:
        prompt = prompt.replace(f"@{username}", "").strip()
    if prompt.lower().startswith("/ask"):
        prompt = prompt[4:].strip()
    if not prompt and message.reply_to_message:
        prompt = message.reply_to_message.text or ""
    if not prompt:
        await message.reply("Savolingizni ham yozing.")
        return

    # AI javobidan oldin @inferiq obunasini tekshirish
    try:
        member = await message.bot.get_chat_member(
            "@inferiq", message.from_user.id
        )
        subscribed = (
            member.status in ("creator", "administrator", "member")
            or (
                member.status == "restricted"
                and getattr(member, "is_member", False)
            )
        )
    except Exception:
        await message.reply(
            "⚠️ Obunani hozir tekshirib bo‘lmadi. Keyinroq qayta urinib ko‘ring."
        )
        return

    if not subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📢 Kanalga obuna bo‘lish",
                url="https://t.me/inferiq"
            )],
            [InlineKeyboardButton(
                text="✅ Obunani tekshirish",
                callback_data="subscription:check"
            )]
        ])
        await message.reply(
            "🔒 AI funksiyalaridan foydalanish uchun avval @inferiq kanaliga obuna bo‘ling.",
            reply_markup=keyboard
        )
        return

    feature_questions = (
        "nimalar qila olasan",
        "nima qila olasan",
        "nimalarni qila olasan",
        "funksiyalaring",
        "imkoniyatlaring",
        "nima ish qilasan",
    )
    if any(q in prompt.lower().strip().replace("?", "") for q in feature_questions):
        await message.reply(
            "🌸 <b>Mariya AI — nimalar qila oladi?</b> 🔥\\n\\n"
            "💬 AI bilan suhbatlashish — botga murojaat qiling yoki /ask savol yozing.\\n"
            "🧠 Suhbatdagi ma'lumotni eslab qolish — <code>eslab qol: matn</code>.\\n"
            "🗑 Xotirani tozalash — <code>xotirani o'chir</code>.\\n"
            "👋 Yangi a'zolar uchun xush kelibsiz xabari va xayrlashuv xabarlari.\\n"
            "🛡️ Guruh moderatsiyasi — ogohlantirish, bloklash, ovozsiz qilish va havolalarni nazorat qilish.\\n"
            "📖 Guruh qoidalari va sozlamalari.\\n"
            "📊 Tariflar, kunlik AI limitlari va administrator buyruqlari.\\n\\n"
            "ℹ️ Ayrim buyruqlar faqat guruh administratorlariga ochiq."
        )
        return

    if prompt.lower().strip() == "xotirani o'chir":
        await db.delete_memories(message.chat.id, message.from_user.id)
        await message.reply("🗑 Xotirangiz o'chirildi.")
        return

    memory_prefix = "eslab qol:"
    if prompt.lower().startswith(memory_prefix):
        memory_text = prompt[len(memory_prefix):].strip()
        if not memory_text:
            await message.reply("Saqlanadigan ma'lumotni ham yozing.")
            return
        await db.save_memory(
            message.chat.id,
            message.from_user.id,
            memory_text,
        )
        await message.reply("🧠 Ma'lumot xotirangizga saqlandi.")
        return

    group_plan = await db.get_plan(message.chat.id)
    limits = {
        "free": config.FREE_DAILY_TOKENS,
        "pro": config.PRO_DAILY_TOKENS,
        "premium": config.PREMIUM_DAILY_TOKENS,
    }
    group_limit = limits.get(group_plan, config.FREE_DAILY_TOKENS)
    group_used = await db.get_used_tokens(message.chat.id)

    user_plan = await db.get_user_plan(message.from_user.id)
    user_limit = limits.get(user_plan, config.FREE_DAILY_TOKENS)
    user_used = await db.get_user_used_tokens(message.from_user.id)

    if not config.is_owner(message.from_user.id):
        if group_used >= group_limit:
            await message.reply("⏳ Guruhning kunlik AI limiti tugadi.")
            return
        if user_used >= user_limit:
            await message.reply("⏳ Sizning kunlik AI limitingiz tugadi.")
            return

    remaining = min(
        max(0, group_limit - group_used),
        max(0, user_limit - user_used),
    )

    await db.save_message(message.chat.id, message.from_user.id, "user", prompt)

    try:
        context = await db.get_context(message.chat.id, message.from_user.id, config.CONTEXT_MESSAGES)
        memories = await db.get_memories(message.chat.id, message.from_user.id, 5)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if memories:
            messages.append({
                "role": "system",
                "content": "Guruh xotiralari:\n" + "\n".join(memories)
            })
        messages.extend(context)

        status = await message.reply("🤖 O'ylayapman...")
        if config.is_owner(message.from_user.id):
            max_tokens = 700
        else:
            remaining = max(1, remaining)
            max_tokens = min(700, remaining)

        answer, tokens = await ask_groq(messages, max_tokens=max_tokens)
        await db.add_usage(message.chat.id, tokens)
        await db.add_user_usage(message.from_user.id, tokens)
        await db.save_message(message.chat.id, message.from_user.id, "assistant", answer)

        if answer.strip():
            await status.edit_text(answer[:4000])
        else:
            await status.edit_text("AI bo'sh javob qaytardi.")
    except Exception as exc:
        import traceback
        with open("data/groq_error.log", "a", encoding="utf-8") as f:
            f.write("\n--- GROQ XATOSI ---\n")
            f.write(traceback.format_exc())
        print(f"Groq xatosi: {type(exc).__name__}: {exc}", flush=True)
        await message.reply("⚠️ AI javob bera olmadi. Xato qayd etildi.")
