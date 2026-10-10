from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def language_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            ],
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
                InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang:ar"),
            ],
            [
                InlineKeyboardButton(text="🇰🇷 한국어", callback_data="lang:ko"),
                InlineKeyboardButton(text="🇨🇳 中文", callback_data="lang:zh"),
            ],
        ]
    )
