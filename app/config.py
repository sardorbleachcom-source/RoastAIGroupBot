import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def get_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default

def get_admin_ids():
    result = set()
    for value in os.getenv("ADMIN_IDS", "").split(","):
        value = value.strip()
        if value.isdigit():
            result.add(int(value))
    return result

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL", "llama-3.3-70b-versatile"
).strip()

DATABASE_PATH = os.getenv(
    "DATABASE_PATH", "data/roastai.db"
).strip()

if not Path(DATABASE_PATH).is_absolute():
    DATABASE_PATH = str(ROOT / DATABASE_PATH)

ADMIN_IDS = get_admin_ids()
BOT_OWNER_ID = get_int("BOT_OWNER_ID", 0)

def is_owner(user_id):
    return bool(user_id) and int(user_id) == BOT_OWNER_ID

def is_admin(user_id):
    return bool(user_id) and (
        int(user_id) == BOT_OWNER_ID or int(user_id) in ADMIN_IDS
    )
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")
FREE_DAILY_TOKENS = max(0, get_int("FREE_DAILY_TOKENS", 20000))
PRO_DAILY_TOKENS = max(0, get_int("PRO_DAILY_TOKENS", 100000))
PREMIUM_DAILY_TOKENS = max(0, get_int("PREMIUM_DAILY_TOKENS", 300000))
CONTEXT_MESSAGES = max(2, get_int("CONTEXT_MESSAGES", 20))

# AI avtomatik javob rejimi
AUTO_REPLY = os.getenv("AUTO_REPLY", "1").strip() == "1"

# Bank kartasi orqali to'lov
PRO_PRICE = max(1, get_int("PRO_PRICE", 30000))
PREMIUM_PRICE = max(1, get_int("PREMIUM_PRICE", 60000))
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "").strip()
PAYMENT_CARD_HOLDER = os.getenv("PAYMENT_CARD_HOLDER", "").strip()
