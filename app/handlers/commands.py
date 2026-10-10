from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime, timedelta, timezone
from app.database import db
from app import config
from app.keyboards import main_menu
from app.keyboards.language import language_menu
from app.locales import get_text

router = Router()

async def check_inferiq_subscription(bot, user_id: int):
    try:
        member = await bot.get_chat_member("@inferiq", user_id)
        if member.status in ("creator", "administrator", "member"):
            return True
        if member.status == "restricted" and getattr(member, "is_member", False):
            return True
        return False
    except Exception:
        return None


def subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Kanalga obuna bo‘lish",
            url="https://t.me/inferiq"
        )],
        [InlineKeyboardButton(
            text="✅ Obunani tekshirish",
            callback_data="subscription:check"
        )]
    ])


async def show_subscription_required(message: Message):
    await message.answer(
        "🔒 <b>Botdan foydalanish uchun @inferiq kanaliga obuna bo‘ling.</b>\\n"
        "Obuna bo‘lgach, «✅ Obunani tekshirish» tugmasini bosing.",
        reply_markup=subscription_keyboard()
    )


@router.message(Command("start"))
async def start_command(message: Message):
    if not message.from_user:
        return

    status = await check_inferiq_subscription(
        message.bot, message.from_user.id
    )
    if status is None:
        await message.answer(
            "⚠️ Hozir obunani tekshirib bo‘lmadi. Birozdan keyin /start ni qayta yuboring."
        )
        return
    if not status:
        await show_subscription_required(message)
        return

    await db.register_user(
        message.from_user.id, message.from_user.username or ""
    )
    await message.answer(
        get_text("uz", "choose_language"),
        reply_markup=language_menu()
    )


@router.callback_query(F.data == "subscription:check")
async def check_subscription_callback(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    status = await check_inferiq_subscription(
        callback.bot, callback.from_user.id
    )
    if status is None:
        await callback.answer(
            "Obunani tekshirish vaqtincha ishlamayapti. Qayta urinib ko‘ring.",
            show_alert=True
        )
        return

    if not status:
        await callback.answer(
            "Avval @inferiq kanaliga obuna bo‘ling.",
            show_alert=True
        )
        return

    await db.register_user(
        callback.from_user.id, callback.from_user.username or ""
    )

    if callback.message.chat.type != "private":
        await callback.message.edit_text(
            "✅ Obuna tasdiqlandi. Endi savolingizni qayta yuboring."
        )
        await callback.answer("Obuna tasdiqlandi.")
        return

    await callback.message.edit_text(
        get_text("uz", "choose_language"),
        reply_markup=language_menu()
    )
    await callback.answer("✅ Obuna tasdiqlandi.")


@router.callback_query(F.data.startswith("lang:"))
async def choose_language_callback(callback: CallbackQuery):
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    language = callback.data.split(":", 1)[1]
    if language not in {"uz", "ru", "en", "ar", "ko", "zh"}:
        await callback.answer("Til tanilmadi.")
        return

    await db.set_user_language(callback.from_user.id, language)
    await callback.message.answer(
        get_text(language, "welcome"),
        reply_markup=main_menu(language)
    )
    await callback.answer(get_text(language, "language_saved"))


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📚 Buyruqlar:\n"
        "/ask savol — AI ga savol berish\n"
        "/plan — guruh tarifi\n"
        "/stats — administrator statistikasi"
    )

@router.message(Command("plan"))
async def plan_command(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Bu buyruqni guruhda ishlating.")
        return
    plan = await db.get_plan(message.chat.id)
    used = await db.get_used_tokens(message.chat.id)
    limits = {
        "free": config.FREE_DAILY_TOKENS,
        "pro": config.PRO_DAILY_TOKENS,
        "premium": config.PREMIUM_DAILY_TOKENS,
    }
    limit = limits.get(plan, config.FREE_DAILY_TOKENS)
    await message.answer(
        f"📦 Tarif: {plan.upper()}\n"
        f"📊 Kunlik sarf: {used:,} / {limit:,} token"
    )

@router.message(Command("stats"))
async def stats_command(message: Message):
    if not message.from_user or not config.is_admin(message.from_user.id):
        await message.answer("⛔ Faqat administrator uchun.")
        return
    users, groups = await db.get_stats()
    await message.answer(
        f"📊 Statistika\nFoydalanuvchilar: {users}\nGuruhlar: {groups}"
    )


async def is_group_admin(message: Message) -> bool:
    if not message.from_user or message.chat.type not in ("group", "supergroup"):
        return False
    member = await message.bot.get_chat_member(
        message.chat.id, message.from_user.id
    )
    return member.status in ("administrator", "creator")


@router.message(Command("warn"))
async def warn_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Bu buyruq faqat guruh administratorlari uchun.")
        return

    target = message.reply_to_message
    if not target or not target.from_user:
        await message.reply("Foydalanuvchining xabariga javob berib /warn yozing.")
        return

    if target.from_user.is_bot:
        await message.reply("🤖 Botlarga ogohlantirish berilmaydi.")
        return

    count = await db.warn_user(message.chat.id, target.from_user.id)
    await message.reply(
        f"⚠️ {target.from_user.full_name} ogohlantirildi. "
        f"Ogohlantirishlar soni: {count}"
    )


@router.message(Command("warnings"))
async def warnings_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Bu buyruq faqat guruh administratorlari uchun.")
        return

    target = message.reply_to_message
    if not target or not target.from_user:
        await message.reply("Foydalanuvchining xabariga javob berib /warnings yozing.")
        return

    async with __import__("aiosqlite").connect(config.DATABASE_PATH) as conn:
        cur = await conn.execute(
            "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
            (message.chat.id, target.from_user.id)
        )
        row = await cur.fetchone()

    count = row[0] if row else 0
    await message.reply(
        f"📋 {target.from_user.full_name}: {count} ta ogohlantirish."
    )


@router.message(Command("clearwarns"))
async def clearwarns_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Bu buyruq faqat guruh administratorlari uchun.")
        return

    target = message.reply_to_message
    if not target or not target.from_user:
        await message.reply("Foydalanuvchining xabariga javob berib /clearwarns yozing.")
        return

    async with __import__("aiosqlite").connect(config.DATABASE_PATH) as conn:
        await conn.execute(
            "DELETE FROM warnings WHERE chat_id=? AND user_id=?",
            (message.chat.id, target.from_user.id)
        )
        await conn.commit()

    await message.reply(
        f"✅ {target.from_user.full_name} uchun ogohlantirishlar tozalandi."
    )

async def moderation_target(message: Message):
    target = message.reply_to_message
    if not target or not target.from_user:
        await message.reply(
            "Foydalanuvchining xabariga javob berib buyruq yuboring."
        )
        return None

    user = target.from_user
    if user.is_bot:
        await message.reply("🤖 Botga bu amalni qo‘llab bo‘lmaydi.")
        return None

    try:
        member = await message.bot.get_chat_member(
            message.chat.id, user.id
        )
        if member.status in ("administrator", "creator"):
            await message.reply(
                "⛔ Guruh administratoriga bu amalni qo‘llab bo‘lmaydi."
            )
            return None
    except TelegramBadRequest:
        pass

    return user


@router.message(Command("ban"))
async def ban_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Faqat guruh administratorlari uchun.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Bu buyruq guruhda ishlaydi.")
        return

    user = await moderation_target(message)
    if not user:
        return

    try:
        await message.bot.ban_chat_member(message.chat.id, user.id)
        await message.reply(f"🔨 {user.full_name} guruhdan chiqarildi.")
    except TelegramBadRequest as e:
        await message.reply(f"Amal bajarilmadi: {e}")


@router.message(Command("unban"))
async def unban_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Faqat guruh administratorlari uchun.")
        return

    target = message.reply_to_message
    if not target or not target.from_user:
        await message.reply(
            "Foydalanuvchining xabariga javob berib /unban yozing."
        )
        return

    try:
        await message.bot.unban_chat_member(
            message.chat.id, target.from_user.id, only_if_banned=True
        )
        await message.reply(
            f"✅ {target.from_user.full_name} uchun taqiq olib tashlandi."
        )
    except TelegramBadRequest as e:
        await message.reply(f"Amal bajarilmadi: {e}")


@router.message(Command("kick"))
async def kick_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Faqat guruh administratorlari uchun.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Bu buyruq guruhda ishlaydi.")
        return

    user = await moderation_target(message)
    if not user:
        return

    try:
        await message.bot.ban_chat_member(message.chat.id, user.id)
        await message.bot.unban_chat_member(message.chat.id, user.id)
        await message.reply(f"👢 {user.full_name} guruhdan chiqarildi.")
    except TelegramBadRequest as e:
        await message.reply(f"Amal bajarilmadi: {e}")


@router.message(Command("mute"))
async def mute_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Faqat guruh administratorlari uchun.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Bu buyruq guruhda ishlaydi.")
        return

    user = await moderation_target(message)
    if not user:
        return

    parts = (message.text or "").split()
    try:
        minutes = int(parts[1]) if len(parts) > 1 else 10
    except ValueError:
        await message.reply("Foydalanish: /mute yoki /mute 10")
        return

    if not 1 <= minutes <= 10080:
        await message.reply("Muddat 1 daqiqadan 7 kungacha bo‘lishi kerak.")
        return

    try:
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await message.reply(
            f"🔇 {user.full_name} {minutes} daqiqaga yozishdan cheklandi."
        )
    except TelegramBadRequest as e:
        await message.reply(f"Amal bajarilmadi: {e}")


@router.message(Command("unmute"))
async def unmute_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Faqat guruh administratorlari uchun.")
        return
    if message.chat.type not in ("group", "supergroup"):
        await message.reply("Bu buyruq guruhda ishlaydi.")
        return

    user = await moderation_target(message)
    if not user:
        return

    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await message.reply(
            f"🔊 {user.full_name} uchun yozish cheklovi olib tashlandi."
        )
    except TelegramBadRequest as e:
        await message.reply(f"Amal bajarilmadi: {e}")


@router.message(Command("rules"))
async def rules_command(message: Message):
    rules = await db.get_setting(
        message.chat.id, "rules", "Guruh qoidalari hali sozlanmagan."
    )
    await message.reply(f"📜 Guruh qoidalari:\n{rules}")


@router.message(Command("setrules"))
async def setrules_command(message: Message):
    if not await is_group_admin(message):
        await message.reply("⛔ Faqat guruh administratorlari uchun.")
        return

    rules = (message.text or "").partition(" ")[2].strip()
    if not rules:
        await message.reply(
            "Foydalanish: /setrules Guruh qoidalarini shu yerga yozing"
        )
        return

    await db.set_setting(message.chat.id, "rules", rules[:3500])
    await message.reply("✅ Guruh qoidalari saqlandi.")


@router.message(Command("id"))
async def id_command(message: Message):
    result = f"🆔 Guruh ID: {message.chat.id}"
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        result += f"\n👤 Foydalanuvchi: {user.full_name}\n🆔 ID: {user.id}"
    elif message.from_user:
        result += f"\n👤 Sizning ID: {message.from_user.id}"
    await message.reply(result)



@router.message(Command("settings"))
async def settings_command(message: Message):
    if not await is_group_admin(message):
        await message.answer("⛔ Faqat guruh administratorlari uchun.")
        return

    chat_id = message.chat.id
    links = await db.get_setting(chat_id, "block_links", "0")
    welcome = await db.get_setting(chat_id, "welcome", "1")
    farewell = await db.get_setting(chat_id, "farewell", "1")

    await message.answer(
        "⚙️ Guruh sozlamalari\n\n"
        f"🔗 Havolalarni bloklash: {'YOQILGAN' if links == '1' else 'O‘CHIRILGAN'}\n"
        f"👋 Yangi a'zolarni kutib olish: {'YOQILGAN' if welcome == '1' else 'O‘CHIRILGAN'}\n"
        f"🚪 Xayrlashuv xabarlari: {'YOQILGAN' if farewell == '1' else 'O‘CHIRILGAN'}\n\n"
        "/togglelinks — havolalarni bloklash\n"
        "/togglewelcome — salomlashuv\n"
        "/togglefarewell — xayrlashuv"
    )


@router.message(Command("togglelinks"))
async def toggle_links_command(message: Message):
    if not await is_group_admin(message):
        await message.answer("⛔ Faqat guruh administratorlari uchun.")
        return

    current = await db.get_setting(message.chat.id, "block_links", "0")
    new_value = "0" if current == "1" else "1"
    await db.set_setting(message.chat.id, "block_links", new_value)
    await message.answer(
        f"🔗 Havolalarni bloklash: {'YOQILDI' if new_value == '1' else 'O‘CHIRILDI'}"
    )


@router.message(Command("togglewelcome"))
async def toggle_welcome_command(message: Message):
    if not await is_group_admin(message):
        await message.answer("⛔ Faqat guruh administratorlari uchun.")
        return

    current = await db.get_setting(message.chat.id, "welcome", "1")
    new_value = "0" if current == "1" else "1"
    await db.set_setting(message.chat.id, "welcome", new_value)
    await message.answer(
        f"👋 Yangi a'zolarni kutib olish: {'YOQILDI' if new_value == '1' else 'O‘CHIRILDI'}"
    )


@router.message(Command("togglefarewell"))
async def toggle_farewell_command(message: Message):
    if not await is_group_admin(message):
        await message.answer("⛔ Faqat guruh administratorlari uchun.")
        return

    current = await db.get_setting(message.chat.id, "farewell", "1")
    new_value = "0" if current == "1" else "1"

    await db.set_setting(message.chat.id, "farewell", new_value)

    status = "YOQILDI" if new_value == "1" else "O‘CHIRILDI"
    await message.answer(f"👋 Xayrlashuv xabarlari: {status}")


@router.message(Command("setwelcome"))
async def set_welcome_text(message: Message):
    if not await is_group_admin(message):
        await message.answer("⛔ Faqat guruh administratorlari uchun.")
        return

    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer(
            "Foydalanish: /setwelcome Salom, {name}! Guruhimizga xush kelibsiz!"
        )
        return

    await db.set_setting(message.chat.id, "welcome_text", text)
    await message.answer("✅ Salomlashuv matni saqlandi.")


@router.message(Command("setfarewell"))
async def set_farewell_text(message: Message):
    if not await is_group_admin(message):
        await message.answer("⛔ Faqat guruh administratorlari uchun.")
        return

    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer(
            "Foydalanish: /setfarewell Xayr, {name}! Yana ko‘rishguncha!"
        )
        return

    await db.set_setting(message.chat.id, "farewell_text", text)
    await message.answer("✅ Xayrlashuv matni saqlandi.")


# Asosiy menyu tugmalari — 6 ta til
LANGUAGES = ("uz", "ru", "en", "ar", "ko", "zh")


@router.message(F.text.in_({get_text(lang, "my_plan") for lang in LANGUAGES}))
async def personal_plan_button(message: Message):
    if not message.from_user:
        return

    language = await db.get_user_language(message.from_user.id)
    plan = await db.get_user_plan(message.from_user.id)
    used = await db.get_user_used_tokens(message.from_user.id)

    limits = {
        "free": config.FREE_DAILY_TOKENS,
        "pro": config.PRO_DAILY_TOKENS,
        "premium": config.PREMIUM_DAILY_TOKENS,
    }
    limit = limits.get(plan, config.FREE_DAILY_TOKENS)
    remaining = max(0, limit - used)

    labels = {
        "uz": ("Sizning tarifingiz", "Tarif", "Bugungi sarf", "Kunlik limit", "Qolgan limit"),
        "ru": ("Ваш тариф", "Тариф", "Использовано сегодня", "Дневной лимит", "Осталось"),
        "en": ("Your plan", "Plan", "Used today", "Daily limit", "Remaining"),
        "ar": ("باقتك", "الباقة", "المستخدم اليوم", "الحد اليومي", "المتبقي"),
        "ko": ("내 요금제", "요금제", "오늘 사용량", "일일 한도", "남은 한도"),
        "zh": ("我的套餐", "套餐", "今日已使用", "每日限额", "剩余额度"),
    }
    title, plan_label, used_label, limit_label, remaining_label = labels.get(
        language, labels["uz"]
    )

    await message.answer(
        f"👤 <b>{title}</b>\n"
        f"📦 {plan_label}: <b>{plan.upper()}</b>\n"
        f"📊 {used_label}: {used:,} token\n"
        f"📥 {limit_label}: {limit:,} token\n"
        f"✅ {remaining_label}: {remaining:,} token"
    )


@router.message(F.text.in_({get_text(lang, "plans") for lang in LANGUAGES}))
async def plans_button(message: Message):
    language = (
        await db.get_user_language(message.from_user.id)
        if message.from_user else "uz"
    )

    descriptions = {
        "uz": ("RoastAI tariflari", "AI bilan suhbat va asosiy imkoniyatlar.",
               "Ko‘proq AI foydalanish limiti.", "Eng yuqori kunlik AI limiti.",
               "Tarifni faollashtirish uchun «🛒 Tarif sotib olish» tugmasini bosing."),
        "ru": ("Тарифы RoastAI", "Общение с ИИ и основные возможности.",
               "Увеличенный лимит использования ИИ.", "Максимальный дневной лимит ИИ.",
               "Для покупки нажмите кнопку «🛒 Купить тариф»."),
        "en": ("RoastAI plans", "AI chat and basic features.",
               "Higher AI usage limit.", "Highest daily AI limit.",
               "To activate a plan, press «🛒 Buy a plan»."),
        "ar": ("باقات RoastAI", "محادثة الذكاء الاصطناعي والميزات الأساسية.",
               "حد استخدام أعلى للذكاء الاصطناعي.", "أعلى حد يومي للذكاء الاصطناعي.",
               "لتفعيل الباقة، اضغط على «🛒 شراء باقة»."),
        "ko": ("RoastAI 요금제", "AI 대화 및 기본 기능.",
               "더 높은 AI 사용 한도.", "가장 높은 일일 AI 한도.",
               "요금제를 구매하려면 «🛒 요금제 구매»를 누르세요."),
        "zh": ("RoastAI 套餐", "人工智能聊天和基本功能。",
               "更高的人工智能使用额度。", "最高的每日人工智能额度。",
               "如需开通套餐，请点击「🛒 购买套餐」。"),
    }
    title, free_desc, pro_desc, premium_desc, footer = descriptions.get(
        language, descriptions["uz"]
    )

    await message.answer(
        f"💎 <b>{title}</b>\n\n"
        f"🆓 <b>FREE</b> — {config.FREE_DAILY_TOKENS:,} token/kun\n"
        f"{free_desc}\n\n"
        f"⭐ <b>PRO</b> — {config.PRO_DAILY_TOKENS:,} token/kun\n"
        f"{pro_desc}\n\n"
        f"💎 <b>PREMIUM</b> — {config.PREMIUM_DAILY_TOKENS:,} token/kun\n"
        f"{premium_desc}\n\n{footer}"
    )


@router.message(F.text.in_({get_text(lang, "buy") for lang in LANGUAGES}))
async def buy_plan_button(message: Message):
    language = (
        await db.get_user_language(message.from_user.id)
        if message.from_user else "uz"
    )
    username = getattr(config, "SUPPORT_USERNAME", "").strip().lstrip("@")

    if username:
        from urllib.parse import quote
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        text = quote(get_text(language, "buy_message"))
        url = f"https://t.me/{username}?text={text}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_text(language, "contact_admin"),
                        url=url,
                    )
                ]
            ]
        )
        await message.answer(
            get_text(language, "buy_text"),
            reply_markup=keyboard,
        )
    else:
        await message.answer(get_text(language, "admin_missing"))


@router.message(F.text.in_({get_text(lang, "features") for lang in LANGUAGES}))
async def all_functions_button(message: Message):
    language = await db.get_user_language(message.from_user.id) if message.from_user else "uz"
    texts = {
        "uz": "📚 <b>Bot funksiyalari</b>\n\n🤖 AI: guruhda botga murojaat qiling yoki /ask buyrug'idan foydalaning.\n📦 Tarif: /plan\n📖 Qoidalar: /rules\n🆔 ID: /id\n⚙️ Sozlamalar: /settings\n🛡️ Boshqaruv: /warn, /ban, /mute va boshqa buyruqlar.\n🛠️ Bot administratori: /admin",
        "ru": "📚 <b>Функции бота</b>\n\n🤖 ИИ: обратитесь к боту в группе или используйте /ask.\n📦 Тариф: /plan\n📖 Правила: /rules\n🆔 Идентификатор: /id\n⚙️ Настройки: /settings\n🛡️ Управление: /warn, /ban, /mute и другие команды.\n🛠️ Администратор бота: /admin",
        "en": "📚 <b>Bot features</b>\n\n🤖 AI: mention the bot in a group or use /ask.\n📦 Plan: /plan\n📖 Rules: /rules\n🆔 ID: /id\n⚙️ Settings: /settings\n🛡️ Moderation: /warn, /ban, /mute and other commands.\n🛠️ Bot administrator: /admin",
        "ar": "📚 <b>ميزات البوت</b>\n\n🤖 الذكاء الاصطناعي: اذكر البوت في المجموعة أو استخدم /ask.\n📦 الباقة: /plan\n📖 القواعد: /rules\n🆔 المعرّف: /id\n⚙️ الإعدادات: /settings\n🛡️ الإدارة: /warn و /ban و /mute وأوامر أخرى.\n🛠️ مشرف البوت: /admin",
        "ko": "📚 <b>봇 기능</b>\n\n🤖 AI: 그룹에서 봇을 호출하거나 /ask를 사용하세요.\n📦 요금제: /plan\n📖 규칙: /rules\n🆔 ID: /id\n⚙️ 설정: /settings\n🛡️ 관리: /warn, /ban, /mute 및 기타 명령어.\n🛠️ 봇 관리자: /admin",
        "zh": "📚 <b>机器人功能</b>\n\n🤖 AI：在群组中提及机器人或使用 /ask。\n📦 套餐：/plan\n📖 规则：/rules\n🆔 ID：/id\n⚙️ 设置：/settings\n🛡️ 管理：/warn、/ban、/mute 等命令。\n🛠️ 机器人管理员：/admin",
    }
    await message.answer(texts.get(language, texts["uz"]))

@router.message(F.text.in_({get_text(lang, "rules") for lang in LANGUAGES}))
async def rules_button(message: Message):
    language = await db.get_user_language(message.from_user.id) if message.from_user else "uz"
    if message.chat.type not in ("group", "supergroup"):
        texts = {
            "uz": "📖 Guruh qoidalarini ko'rish uchun bot turgan guruhda /rules buyrug'ini ishlating.",
            "ru": "📖 Чтобы посмотреть правила группы, используйте команду /rules в группе, где находится бот.",
            "en": "📖 To view group rules, use /rules in the group where the bot is present.",
            "ar": "📖 لعرض قواعد المجموعة، استخدم الأمر /rules داخل المجموعة التي يوجد فيها البوت.",
            "ko": "📖 그룹 규칙을 보려면 봇이 있는 그룹에서 /rules 명령어를 사용하세요.",
            "zh": "📖 如需查看群组规则，请在机器人所在的群组中使用 /rules 命令。",
        }
        await message.answer(texts.get(language, texts["uz"]))
        return
    rules = await db.get_setting(message.chat.id, "rules")
    if rules:
        await message.answer(rules)
    else:
        texts = {
            "uz": "Guruh qoidalari hali kiritilmagan.",
            "ru": "Правила группы ещё не добавлены.",
            "en": "Group rules have not been added yet.",
            "ar": "لم تتم إضافة قواعد المجموعة بعد.",
            "ko": "아직 그룹 규칙이 등록되지 않았습니다.",
            "zh": "尚未设置群组规则。",
        }
        await message.answer(texts.get(language, texts["uz"]))

@router.message(F.text.in_({get_text(lang, "my_id") for lang in LANGUAGES}))
async def my_id_button(message: Message):
    if message.from_user:
        language = await db.get_user_language(message.from_user.id)
        labels = {
            "uz": "🆔 Sizning Telegram ID raqamingiz:",
            "ru": "🆔 Ваш Telegram ID:",
            "en": "🆔 Your Telegram ID:",
            "ar": "🆔 معرّف تيليجرام الخاص بك:",
            "ko": "🆔 회원님의 텔레그램 ID:",
            "zh": "🆔 您的 Telegram ID：",
        }
        await message.answer(
            f"{labels.get(language, labels['uz'])} <code>{message.from_user.id}</code>"
        )

# Qo‘shimcha menyu tugmalari

# Qo‘shimcha menyu tugmalari

@router.message(F.text.in_({get_text(lang, "group_management") for lang in LANGUAGES}))
async def group_management_button(message: Message):
    from app.keyboards import moderation_menu
    language = await db.get_user_language(message.from_user.id) if message.from_user else "uz"
    titles = {
        "uz": "🛡️ <b>Guruh boshqaruvi</b>\n\nAmalni tanlang. Kerakli foydalanuvchining xabariga javob berib buyruqni yuboring.",
        "ru": "🛡️ <b>Управление группой</b>\n\nВыберите действие. Ответьте на сообщение пользователя и отправьте команду.",
        "en": "🛡️ <b>Group management</b>\n\nChoose an action. Reply to a user's message and send the command.",
        "ar": "🛡️ <b>إدارة المجموعة</b>\n\nاختر إجراءً. قم بالرد على رسالة المستخدم وأرسل الأمر.",
        "ko": "🛡️ <b>그룹 관리</b>\n\n작업을 선택하세요. 사용자의 메시지에 답장하고 명령어를 보내세요.",
        "zh": "🛡️ <b>群组管理</b>\n\n请选择操作。回复用户的消息并发送相应命令。",
    }
    await message.answer(
        titles.get(language, titles["uz"]),
        reply_markup=moderation_menu(language)
    )



@router.message(F.text.in_({get_text(lang, "settings") for lang in LANGUAGES}))
async def group_settings_button(message: Message):
    language = await db.get_user_language(message.from_user.id) if message.from_user else "uz"
    if message.chat.type not in ("group", "supergroup"):
        texts = {
            "uz": "⚙️ Guruh sozlamalarini ko'rish uchun bot turgan guruhda /settings buyrug'ini ishlating.",
            "ru": "⚙️ Чтобы открыть настройки группы, используйте /settings в группе, где находится бот.",
            "en": "⚙️ To view group settings, use /settings in the group where the bot is present.",
            "ar": "⚙️ لعرض إعدادات المجموعة، استخدم /settings داخل المجموعة التي يوجد فيها البوت.",
            "ko": "⚙️ 그룹 설정을 보려면 봇이 있는 그룹에서 /settings 명령어를 사용하세요.",
            "zh": "⚙️ 如需查看群组设置，请在机器人所在的群组中使用 /settings 命令。",
        }
        await message.answer(texts.get(language, texts["uz"]))
        return
    if not await is_group_admin(message):
        texts = {
            "uz": "⛔ Bu bo'lim faqat guruh administratorlari uchun.",
            "ru": "⛔ Этот раздел доступен только администраторам группы.",
            "en": "⛔ This section is available only to group administrators.",
            "ar": "⛔ هذا القسم متاح لمشرفي المجموعة فقط.",
            "ko": "⛔ 이 메뉴는 그룹 관리자만 사용할 수 있습니다.",
            "zh": "⛔ 此功能仅供群组管理员使用。",
        }
        await message.answer(texts.get(language, texts["uz"]))
        return
    await settings_command(message)

@router.message(F.text.in_({get_text(lang, "admin") for lang in LANGUAGES}))
async def admin_panel_button(message: Message):
    from app.handlers.admin import admin_panel
    await admin_panel(message)




@router.message(F.text.in_({get_text(lang, "back") for lang in LANGUAGES}))
async def back_to_main_menu(message: Message):
    language = await db.get_user_language(message.from_user.id) if message.from_user else "uz"
    await message.answer(
        get_text(language, "main_menu"),
        reply_markup=main_menu(language)
    )


@router.message(F.text.in_({
    label
    for lang in LANGUAGES
    for label in {
        "uz": ["⚠️ Ogohlantirish", "📋 Ogohlantirishlar", "🧹 Ogohlantirishlarni tozalash", "🔨 Guruhdan bloklash", "🔓 Blokdan chiqarish", "👢 Guruhdan chiqarish", "🔇 Ovozsiz qilish", "🔊 Ovozini tiklash"],
        "ru": ["⚠️ Предупредить", "📋 Предупреждения", "🧹 Очистить предупреждения", "🔨 Заблокировать", "🔓 Разблокировать", "👢 Исключить из группы", "🔇 Ограничить сообщения", "🔊 Снять ограничение"],
        "en": ["⚠️ Warn", "📋 Warnings", "🧹 Clear warnings", "🔨 Ban", "🔓 Unban", "👢 Kick", "🔇 Mute", "🔊 Unmute"],
        "ar": ["⚠️ تحذير", "📋 التحذيرات", "🧹 مسح التحذيرات", "🔨 حظر", "🔓 إلغاء الحظر", "👢 طرد من المجموعة", "🔇 كتم", "🔊 إلغاء الكتم"],
        "ko": ["⚠️ 경고", "📋 경고 목록", "🧹 경고 삭제", "🔨 차단", "🔓 차단 해제", "👢 그룹에서 내보내기", "🔇 음소거", "🔊 음소거 해제"],
        "zh": ["⚠️ 警告", "📋 警告列表", "🧹 清除警告", "🔨 封禁", "🔓 解除封禁", "👢 移出群组", "🔇 禁言", "🔊 解除禁言"],
    }[lang]
}))
async def moderation_button_help(message: Message):
    if not message.text:
        return
    language = await db.get_user_language(message.from_user.id) if message.from_user else "uz"
    labels = {
        "uz": ["⚠️ Ogohlantirish", "📋 Ogohlantirishlar", "🧹 Ogohlantirishlarni tozalash", "🔨 Guruhdan bloklash", "🔓 Blokdan chiqarish", "👢 Guruhdan chiqarish", "🔇 Ovozsiz qilish", "🔊 Ovozini tiklash"],
        "ru": ["⚠️ Предупредить", "📋 Предупреждения", "🧹 Очистить предупреждения", "🔨 Заблокировать", "🔓 Разблокировать", "👢 Исключить из группы", "🔇 Ограничить сообщения", "🔊 Снять ограничение"],
        "en": ["⚠️ Warn", "📋 Warnings", "🧹 Clear warnings", "🔨 Ban", "🔓 Unban", "👢 Kick", "🔇 Mute", "🔊 Unmute"],
        "ar": ["⚠️ تحذير", "📋 التحذيرات", "🧹 مسح التحذيرات", "🔨 حظر", "🔓 إلغاء الحظر", "👢 طرد من المجموعة", "🔇 كتم", "🔊 إلغاء الكتم"],
        "ko": ["⚠️ 경고", "📋 경고 목록", "🧹 경고 삭제", "🔨 차단", "🔓 차단 해제", "👢 그룹에서 내보내기", "🔇 음소거", "🔊 음소거 해제"],
        "zh": ["⚠️ 警告", "📋 警告列表", "🧹 清除警告", "🔨 封禁", "🔓 解除封禁", "👢 移出群组", "🔇 禁言", "🔊 解除禁言"],
    }
    commands = ["/warn", "/warnings", "/clearwarns", "/ban", "/unban", "/kick", "/mute", "/unmute"]
    selected = labels.get(language, labels["uz"])
    index = next(
        i for lang in LANGUAGES
        for i, label in enumerate(labels[lang])
        if label == message.text
    )
    messages = {
        "uz": (f"Tanlangan amal: <b>{message.text}</b>\n\nKerakli foydalanuvchining xabariga javob bering va {commands[index]} buyrug‘ini yuboring.\n\n⚠️ Botda kerakli administrator huquqlari bo‘lishi kerak."),
        "ru": (f"Выбрано действие: <b>{message.text}</b>\n\nОтветьте на сообщение нужного пользователя и отправьте команду {commands[index]}.\n\n⚠️ У бота должны быть необходимые права администратора."),
        "en": (f"Selected action: <b>{message.text}</b>\n\nReply to the target user's message and send {commands[index]}.\n\n⚠️ The bot must have the required administrator permissions."),
        "ar": (f"الإجراء المحدد: <b>{message.text}</b>\n\nقم بالرد على رسالة المستخدم وأرسل الأمر {commands[index]}.\n\n⚠️ يجب أن يمتلك البوت صلاحيات المشرف اللازمة."),
        "ko": (f"선택한 작업: <b>{message.text}</b>\n\n대상 사용자의 메시지에 답장하고 {commands[index]} 명령어를 보내세요.\n\n⚠️ 봇에 필요한 관리자 권한이 있어야 합니다."),
        "zh": (f"所选操作：<b>{message.text}</b>\n\n回复目标用户的消息并发送命令 {commands[index]}。\n\n⚠️ 机器人必须拥有所需的管理员权限。"),
    }
    await message.answer(messages.get(language, messages["uz"]))

