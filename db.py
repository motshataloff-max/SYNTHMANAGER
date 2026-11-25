import os
import aiosqlite
import secrets
from typing import Optional, List, Dict
from datetime import datetime

DB_PATH = "data/bot.db"

SCHEMA = """
PRAGMA busy_timeout=5000;
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    client_code TEXT UNIQUE,
    vk_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_number TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    channel TEXT NOT NULL DEFAULT 'tg',
    type TEXT NOT NULL DEFAULT 'support',
    status TEXT DEFAULT 'new',
    title TEXT,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS ticket_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number TEXT NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_counter (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_number INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS banned_users (
    telegram_id INTEGER PRIMARY KEY,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO ticket_counter(id, current_number) VALUES (1, 0);
INSERT OR IGNORE INTO settings(key, value) VALUES ('about', '🇷🇺 SYNTH — российская команда разработчиков.');
"""

def _conn():
    return aiosqlite.connect(DB_PATH)

async def init(path: str) -> None:
    global DB_PATH
    DB_PATH = path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        
        # 🔥 БЕЗОПАСНАЯ МИГРАЦИЯ: проверяем, есть ли колонка phone, и добавляем только если её нет
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in await cursor.fetchall()]
        if 'phone' not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            
        await db.commit()

async def get_or_create_user(tg_user) -> Dict:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE users SET username=?, full_name=? WHERE telegram_id=?", (tg_user.username, tg_user.full_name, tg_user.id))
            await db.commit()
            return dict(row)
        await db.execute("INSERT INTO users(telegram_id, username, full_name) VALUES(?,?,?)", (tg_user.id, tg_user.username, tg_user.full_name))
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        return dict(await cur.fetchone())

async def get_user(user_id: int) -> Optional[Dict]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def update_user_phone(user_id: int, phone: str) -> None:
    async with _conn() as db:
        await db.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, user_id))
        await db.commit()

async def generate_client_code() -> str:
    while True:
        code = f"SYNTH-{secrets.token_hex(2).upper()}"
        async with _conn() as db:
            cur = await db.execute("SELECT 1 FROM users WHERE client_code = ?", (code,))
            if not await cur.fetchone():
                return code

async def ensure_client_code(user_id: int) -> str:
    user = await get_user(user_id)
    if user and user.get('client_code'):
        return user['client_code']
    code = await generate_client_code()
    async with _conn() as db:
        await db.execute("UPDATE users SET client_code = ? WHERE telegram_id = ?", (code, user_id))
        await db.commit()
    return code

async def is_banned(user_id: int) -> bool:
    async with _conn() as db:
        cur = await db.execute("SELECT 1 FROM banned_users WHERE telegram_id=?", (user_id,))
        return await cur.fetchone() is not None

async def ban_user(user_id: int, reason: str = "") -> None:
    async with _conn() as db:
        await db.execute("INSERT OR REPLACE INTO banned_users(telegram_id, reason) VALUES(?,?)", (user_id, reason))
        await db.commit()

async def unban_user(user_id: int) -> None:
    async with _conn() as db:
        await db.execute("DELETE FROM banned_users WHERE telegram_id=?", (user_id,))
        await db.commit()

async def generate_ticket_number() -> str:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT current_number FROM ticket_counter WHERE id = 1")
        row = await cur.fetchone()
        current = (row["current_number"] if row else 0) + 1
        year = datetime.now().year
        ticket_number = f"SYNTH-{year}-{current:04d}"
        await db.execute("UPDATE ticket_counter SET current_number = ? WHERE id = 1", (current,))
        await db.commit()
        return ticket_number

async def create_ticket(user_id: int, channel: str, type: str, title: str = None, description: str = None) -> Dict:
    ticket_number = await generate_ticket_number()
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT INTO tickets (ticket_number, user_id, channel, type, title, description) VALUES (?, ?, ?, ?, ?, ?)", (ticket_number, user_id, channel, type, title, description))
        await db.execute("INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by) VALUES (?, 'created', NULL, 'new', ?)", (ticket_number, user_id))
        await db.commit()
        cur = await db.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,))
        return dict(await cur.fetchone())

async def get_user_tickets(user_id: int) -> List[Dict]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in await cur.fetchall()]

async def get_all_active_tickets() -> List[Dict]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tickets WHERE status != 'closed' ORDER BY created_at DESC LIMIT 20")
        return [dict(row) for row in await cur.fetchall()]

async def general_stats() -> Dict:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async def scalar(sql: str) -> int:
            cur = await db.execute(sql)
            row = await cur.fetchone()
            return row[0] if row else 0
        return {
            "clients": await scalar("SELECT COUNT(*) FROM users"),
            "active_tickets": await scalar("SELECT COUNT(*) FROM tickets WHERE status != 'closed'"),
            "closed_tickets": await scalar("SELECT COUNT(*) FROM tickets WHERE status = 'closed'"),
        }
