from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu(language="uz"):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    from app.locales import get_text

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=get_text(language, "my_plan")),
                KeyboardButton(text=get_text(language, "plans")),
            ],
            [
                KeyboardButton(text=get_text(language, "buy")),
                KeyboardButton(text=get_text(language, "features")),
            ],
            [
                KeyboardButton(text=get_text(language, "rules")),
                KeyboardButton(text=get_text(language, "my_id")),
            ],
            [
                KeyboardButton(text=get_text(language, "group_management")),
                KeyboardButton(text=get_text(language, "settings")),
            ],
            [
                KeyboardButton(text=get_text(language, "admin")),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=get_text(language, "choose_language"),
    )


def moderation_menu(language="uz"):
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    from app.locales import get_text

    labels = {
        "uz": ["⚠️ Ogohlantirish", "📋 Ogohlantirishlar", "🧹 Ogohlantirishlarni tozalash", "🔨 Guruhdan bloklash", "🔓 Blokdan chiqarish", "👢 Guruhdan chiqarish", "🔇 Ovozsiz qilish", "🔊 Ovozini tiklash"],
        "ru": ["⚠️ Предупредить", "📋 Предупреждения", "🧹 Очистить предупреждения", "🔨 Заблокировать", "🔓 Разблокировать", "👢 Исключить из группы", "🔇 Ограничить сообщения", "🔊 Снять ограничение"],
        "en": ["⚠️ Warn", "📋 Warnings", "🧹 Clear warnings", "🔨 Ban", "🔓 Unban", "👢 Kick", "🔇 Mute", "🔊 Unmute"],
        "ar": ["⚠️ تحذير", "📋 التحذيرات", "🧹 مسح التحذيرات", "🔨 حظر", "🔓 إلغاء الحظر", "👢 طرد من المجموعة", "🔇 كتم", "🔊 إلغاء الكتم"],
        "ko": ["⚠️ 경고", "📋 경고 목록", "🧹 경고 삭제", "🔨 차단", "🔓 차단 해제", "👢 그룹에서 내보내기", "🔇 음소거", "🔊 음소거 해제"],
        "zh": ["⚠️ 警告", "📋 警告列表", "🧹 清除警告", "🔨 封禁", "🔓 解除封禁", "👢 移出群组", "🔇 禁言", "🔊 解除禁言"],
    }
    a = labels.get(language, labels["uz"])

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=a[0]), KeyboardButton(text=a[1])],
            [KeyboardButton(text=a[2])],
            [KeyboardButton(text=a[3]), KeyboardButton(text=a[4])],
            [KeyboardButton(text=a[5])],
            [KeyboardButton(text=a[6]), KeyboardButton(text=a[7])],
            [KeyboardButton(text=get_text(language, "back"))],
        ],
        resize_keyboard=True,
        input_field_placeholder=get_text(language, "choose_language"),
    )
