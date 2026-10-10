import aiosqlite
from pathlib import Path
from datetime import datetime

from app import config

def today():
    # Serverdagi mahalliy sana bo'yicha kunlik hisob.
    return datetime.now().date().isoformat()

async def connect():
    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(config.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    return db

async def init_db():
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            language TEXT DEFAULT 'uz',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS groups(
            chat_id INTEGER PRIMARY KEY,
            title TEXT DEFAULT '',
            language TEXT DEFAULT 'uz',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subscriptions(
            chat_id INTEGER PRIMARY KEY,
            plan TEXT NOT NULL DEFAULT 'free',
            expires_at TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS user_subscriptions(
            user_id INTEGER PRIMARY KEY,
            plan TEXT NOT NULL DEFAULT 'free',
            expires_at TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS group_settings(
            chat_id INTEGER NOT NULL,
            setting TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY(chat_id, setting)
        );

        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS memories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_usage(
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            tokens INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id, day)
        );

        CREATE TABLE IF NOT EXISTS usage(
            chat_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            tokens INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(chat_id, day)
        );

        CREATE TABLE IF NOT EXISTS warnings(
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS blocked_domains(
            chat_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            PRIMARY KEY(chat_id, domain)
        );

        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_messages_chat
            ON messages(chat_id, id);
        CREATE INDEX IF NOT EXISTS idx_memories_chat
            ON memories(chat_id, id);
        CREATE INDEX IF NOT EXISTS idx_usage_day
            ON usage(day);
        """)
        await db.commit()

async def user_exists(user_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,),
        )
        return await cur.fetchone() is not None


async def register_user(user_id, username=""):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO users(user_id, username) VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
        """, (user_id, username or ""))
        await db.commit()

async def register_group(chat_id, title=""):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO groups(chat_id, title) VALUES(?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title
        """, (chat_id, title or ""))
        await db.execute("""
            INSERT OR IGNORE INTO subscriptions(chat_id, plan)
            VALUES(?, 'free')
        """, (chat_id,))
        await db.commit()

async def get_setting(chat_id, key, default="1"):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT value FROM group_settings WHERE chat_id=? AND setting=?",
            (chat_id, key)
        )
        row = await cur.fetchone()
        return row["value"] if row else default

async def set_setting(chat_id, key, value):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO group_settings(chat_id, setting, value)
            VALUES(?, ?, ?)
            ON CONFLICT(chat_id, setting)
            DO UPDATE SET value=excluded.value
        """, (chat_id, key, str(value)))
        await db.commit()

async def get_plan(chat_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT plan FROM subscriptions WHERE chat_id=?", (chat_id,)
        )
        row = await cur.fetchone()
        return row["plan"] if row else "free"

async def set_plan(chat_id, plan):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO subscriptions(chat_id, plan) VALUES(?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET plan=excluded.plan
        """, (chat_id, plan))
        await db.commit()

async def get_used_tokens(chat_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT tokens FROM usage WHERE chat_id=? AND day=?",
            (chat_id, today())
        )
        row = await cur.fetchone()
        return row["tokens"] if row else 0

async def add_usage(chat_id, tokens):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO usage(chat_id, day, tokens) VALUES(?, ?, ?)
            ON CONFLICT(chat_id, day)
            DO UPDATE SET tokens=tokens+excluded.tokens
        """, (chat_id, today(), max(0, int(tokens))))
        await db.commit()

async def save_message(chat_id, user_id, role, content):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO messages(chat_id, user_id, role, content)
            VALUES(?, ?, ?, ?)
        """, (chat_id, user_id, role, content[:6000]))
        await db.execute("""
            DELETE FROM messages
            WHERE chat_id=? AND id NOT IN (
                SELECT id FROM messages
                WHERE chat_id=? ORDER BY id DESC LIMIT 100
            )
        """, (chat_id, chat_id))
        await db.commit()

async def get_context(chat_id, user_id, limit=20):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT role, content FROM (
                SELECT id, role, content FROM messages
                WHERE chat_id=? AND user_id=?
                ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
        """, (chat_id, user_id, limit))
        return [
            {"role": row["role"], "content": row["content"]}
            for row in await cur.fetchall()
        ]

async def save_memory(chat_id, user_id, content):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO memories(chat_id, user_id, content)
            VALUES(?, ?, ?)
        """, (chat_id, user_id, content[:1000]))
        await db.commit()


async def get_memories(chat_id, user_id, limit=10):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT content FROM memories
            WHERE chat_id=? AND user_id=?
            ORDER BY id DESC LIMIT ?
        """, (chat_id, user_id, limit))
        return [row["content"] for row in await cur.fetchall()]


async def warn_user(chat_id, user_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO warnings(chat_id, user_id, count) VALUES(?, ?, 1)
            ON CONFLICT(chat_id, user_id)
            DO UPDATE SET count=count+1
        """, (chat_id, user_id))
        cur = await db.execute(
            "SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        row = await cur.fetchone()
        await db.commit()
        return row["count"]

async def get_stats():
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        users = await (await db.execute(
            "SELECT COUNT(*) AS n FROM users"
        )).fetchone()
        groups = await (await db.execute(
            "SELECT COUNT(*) AS n FROM groups"
        )).fetchone()
        return users["n"], groups["n"]


async def delete_memories(chat_id, user_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM memories WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        await db.commit()


async def find_user(query):
    query = str(query).strip().lstrip("@")
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query.isdigit():
            cur = await db.execute(
                "SELECT user_id, username FROM users WHERE user_id=?",
                (int(query),)
            )
        else:
            cur = await db.execute(
                "SELECT user_id, username FROM users WHERE LOWER(username)=LOWER(?)",
                (query,)
            )
        return await cur.fetchone()


async def set_user_plan(user_id, plan, expires_at=""):
    plan = str(plan).lower()
    if plan not in ("free", "pro", "premium"):
        raise ValueError("Noto‘g‘ri tarif")
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO user_subscriptions(user_id, plan, expires_at)
            VALUES(?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan=excluded.plan,
                expires_at=excluded.expires_at
        """, (int(user_id), plan, expires_at or ""))
        await db.commit()


async def get_user_plan(user_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT plan, expires_at FROM user_subscriptions WHERE user_id=?",
            (int(user_id),)
        )
        row = await cur.fetchone()

    if not row:
        return "free"

    expiry = row["expires_at"]
    if expiry:
        try:
            if datetime.fromisoformat(expiry) <= datetime.now():
                await set_user_plan(user_id, "free", "")
                return "free"
        except ValueError:
            pass

    return row["plan"]


async def get_user_used_tokens(user_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT tokens FROM user_usage WHERE user_id=? AND day=?",
            (int(user_id), today())
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def add_user_usage(user_id, tokens):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO user_usage(user_id, day, tokens)
            VALUES(?, ?, ?)
            ON CONFLICT(user_id, day)
            DO UPDATE SET tokens=tokens+excluded.tokens
        """, (int(user_id), today(), max(0, int(tokens))))
        await db.commit()


async def set_user_language(user_id, language):
    allowed = {"uz", "ru", "en", "ar", "ko", "zh"}
    if language not in allowed:
        raise ValueError("Noto‘g‘ri til kodi")

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, language)
               VALUES (?, ?)
               ON CONFLICT(user_id)
               DO UPDATE SET language = excluded.language""",
            (user_id, language),
        )
        await db.commit()


async def get_user_language(user_id):
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
        return row[0] if row and row[0] else "uz"


# ==============================
# TO'LOV TIZIMI
# ==============================

async def log_payment(payment_id, user_id, action, details=""):
    conn = await connect()
    try:
        await conn.execute("""
            INSERT INTO payment_logs(payment_id, user_id, action, details)
            VALUES(?, ?, ?, ?)
        """, (payment_id, int(user_id), str(action), str(details)[:1000]))
        await conn.commit()
    finally:
        await conn.close()


async def create_payment(
    user_id,
    amount,
    payment_type="plan",
    plan="pro",
    package_tokens=0,
    chat_id=None,
):
    user_id = int(user_id)
    amount = int(amount)
    package_tokens = int(package_tokens)
    payment_type = str(payment_type).lower()
    plan = str(plan).lower()

    if amount <= 0:
        raise ValueError("To'lov summasi musbat bo'lishi kerak.")

    if payment_type not in ("plan", "tokens"):
        raise ValueError("To'lov turi noto'g'ri.")

    if payment_type == "plan" and plan not in ("pro", "premium"):
        raise ValueError("Tarif noto'g'ri.")

    if payment_type == "tokens" and package_tokens <= 0:
        raise ValueError("Token miqdori musbat bo'lishi kerak.")

    conn = await connect()
    try:
        cur = await conn.execute("""
            INSERT INTO payments(
                chat_id, user_id, plan, amount, status,
                payment_type, package_tokens
            )
            VALUES(?, ?, ?, ?, 'pending', ?, ?)
        """, (
            int(chat_id if chat_id is not None else user_id),
            user_id,
            plan if payment_type == "plan" else "tokens",
            amount,
            payment_type,
            package_tokens,
        ))
        await conn.commit()
        payment_id = cur.lastrowid

        await conn.execute("""
            INSERT INTO payment_logs(payment_id, user_id, action, details)
            VALUES(?, ?, 'created', ?)
        """, (payment_id, user_id, f"{payment_type}; summa={amount}"))
        await conn.commit()
        return payment_id
    finally:
        await conn.close()


async def get_user_pending_payment(user_id):
    conn = await connect()
    try:
        cur = await conn.execute("""
            SELECT *
            FROM payments
            WHERE user_id=? AND status='pending'
              AND payment_type='plan'
            ORDER BY id DESC
            LIMIT 1
        """, (int(user_id),))
        return await cur.fetchone()
    finally:
        await conn.close()


async def get_payment(payment_id):
    conn = await connect()
    try:
        cur = await conn.execute(
            "SELECT * FROM payments WHERE id=?",
            (int(payment_id),)
        )
        return await cur.fetchone()
    finally:
        await conn.close()


async def get_pending_payments(limit=20):
    conn = await connect()
    try:
        cur = await conn.execute("""
            SELECT p.*, u.username
            FROM payments p
            LEFT JOIN users u ON u.user_id=p.user_id
            WHERE p.status='pending'
            ORDER BY p.id DESC
            LIMIT ?
        """, (max(1, min(int(limit), 100)),))
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_token_balance(user_id):
    conn = await connect()
    try:
        cur = await conn.execute(
            "SELECT tokens FROM token_balances WHERE user_id=?",
            (int(user_id),)
        )
        row = await cur.fetchone()
        return int(row["tokens"]) if row else 0
    finally:
        await conn.close()


async def add_token_balance(user_id, tokens):
    user_id = int(user_id)
    tokens = int(tokens)

    if tokens <= 0:
        raise ValueError("Token miqdori musbat bo'lishi kerak.")

    conn = await connect()
    try:
        await conn.execute("""
            INSERT INTO token_balances(user_id, tokens)
            VALUES(?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                tokens=tokens + excluded.tokens,
                updated_at=CURRENT_TIMESTAMP
        """, (user_id, tokens))
        await conn.commit()
        return await get_token_balance(user_id)
    finally:
        await conn.close()


async def confirm_payment_once(payment_id, admin_id):
    """
    To'lovni faqat pending holatidan bir marta tasdiqlaydi.
    Tarif yoki token va to'lov holati bitta tranzaksiyada saqlanadi.
    """
    from datetime import timedelta

    payment_id = int(payment_id)
    admin_id = int(admin_id)
    conn = await connect()

    try:
        await conn.execute("BEGIN IMMEDIATE")

        cur = await conn.execute(
            "SELECT * FROM payments WHERE id=?",
            (payment_id,)
        )
        payment = await cur.fetchone()

        if not payment:
            await conn.rollback()
            return {"ok": False, "reason": "not_found"}

        if payment["status"] != "pending":
            await conn.rollback()
            return {"ok": False, "reason": "already_processed"}

        user_id = int(payment["user_id"])
        payment_type = payment["payment_type"]
        plan = payment["plan"]
        tokens = int(payment["package_tokens"] or 0)

        if payment_type == "tokens":
            if tokens <= 0:
                await conn.rollback()
                await log_payment(
                    payment_id, user_id, "error",
                    "Token miqdori noto'g'ri."
                )
                return {"ok": False, "reason": "invalid_tokens"}

            await conn.execute("""
                INSERT INTO token_balances(user_id, tokens)
                VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    tokens=tokens + excluded.tokens,
                    updated_at=CURRENT_TIMESTAMP
            """, (user_id, tokens))

        elif payment_type == "plan":
            if plan not in ("pro", "premium"):
                await conn.rollback()
                await log_payment(
                    payment_id, user_id, "error",
                    "Tarif nomi noto'g'ri."
                )
                return {"ok": False, "reason": "invalid_plan"}

            expires_at = (
                datetime.now() + timedelta(days=30)
            ).isoformat(timespec="seconds")

            await conn.execute("""
                INSERT INTO user_subscriptions(user_id, plan, expires_at)
                VALUES(?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    plan=excluded.plan,
                    expires_at=excluded.expires_at
            """, (user_id, plan, expires_at))

        else:
            await conn.rollback()
            await log_payment(
                payment_id, user_id, "error",
                "To'lov turi noma'lum."
            )
            return {"ok": False, "reason": "invalid_type"}

        cur = await conn.execute("""
            UPDATE payments
            SET status='paid',
                confirmed_at=?,
                confirmed_by=?,
                error=''
            WHERE id=? AND status='pending'
        """, (
            datetime.now().isoformat(timespec="seconds"),
            admin_id,
            payment_id,
        ))

        if cur.rowcount != 1:
            await conn.rollback()
            return {"ok": False, "reason": "already_processed"}

        await conn.execute("""
            INSERT INTO payment_logs(payment_id, user_id, action, details)
            VALUES(?, ?, 'confirmed', ?)
        """, (
            payment_id,
            user_id,
            f"Admin ID: {admin_id}; summa: {payment['amount']}",
        ))

        await conn.commit()

        return {
            "ok": True,
            "payment_id": payment_id,
            "user_id": user_id,
            "payment_type": payment_type,
            "plan": plan,
            "tokens": tokens,
            "amount": int(payment["amount"]),
        }

    except Exception as exc:
        await conn.rollback()
        try:
            await log_payment(
                payment_id,
                int(payment["user_id"]) if "payment" in locals() and payment else 0,
                "error",
                str(exc),
            )
        except Exception:
            pass
        raise
    finally:
        await conn.close()


async def reject_payment(payment_id, admin_id, reason="Admin rad etdi"):
    conn = await connect()
    try:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute(
            "SELECT user_id, status FROM payments WHERE id=?",
            (int(payment_id),)
        )
        payment = await cur.fetchone()

        if not payment:
            await conn.rollback()
            return False

        if payment["status"] != "pending":
            await conn.rollback()
            return False

        await conn.execute("""
            UPDATE payments
            SET status='rejected',
                confirmed_by=?,
                confirmed_at=?,
                error=?
            WHERE id=? AND status='pending'
        """, (
            int(admin_id),
            datetime.now().isoformat(timespec="seconds"),
            str(reason)[:1000],
            int(payment_id),
        ))

        await conn.execute("""
            INSERT INTO payment_logs(payment_id, user_id, action, details)
            VALUES(?, ?, 'rejected', ?)
        """, (
            int(payment_id),
            int(payment["user_id"]),
            f"Admin ID: {admin_id}; sabab: {reason}",
        ))

        await conn.commit()
        return True
    finally:
        await conn.close()


async def get_payment_history(user_id=None, limit=20):
    conn = await connect()
    try:
        if user_id is None:
            cur = await conn.execute("""
                SELECT p.*, u.username
                FROM payments p
                LEFT JOIN users u ON u.user_id=p.user_id
                ORDER BY p.id DESC
                LIMIT ?
            """, (max(1, min(int(limit), 100)),))
        else:
            cur = await conn.execute("""
                SELECT *
                FROM payments
                WHERE user_id=?
                ORDER BY id DESC
                LIMIT ?
            """, (int(user_id), max(1, min(int(limit), 100))))

        return await cur.fetchall()
    finally:
        await conn.close()


async def get_payment_logs(limit=30):
    conn = await connect()
    try:
        cur = await conn.execute("""
            SELECT * FROM payment_logs
            ORDER BY id DESC
            LIMIT ?
        """, (max(1, min(int(limit), 100)),))
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_payment_stats():
    conn = await connect()
    try:
        cur = await conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status='paid' THEN 1 ELSE 0 END) AS paid,
                SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) AS revenue
            FROM payments
        """)
        row = await cur.fetchone()
        return {
            key: int(row[key] or 0)
            for key in ("total", "pending", "paid", "rejected", "revenue")
        }
    finally:
        await conn.close()
