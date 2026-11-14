import os
from typing import Optional
import aiosqlite

DB_PATH = "data/bot.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    ref_code    TEXT UNIQUE,
    referrer_id INTEGER,
    discount_percent INTEGER DEFAULT 0,
    age         INTEGER,
    country     TEXT,
    is_samozanyat INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    telegram_id   INTEGER NOT NULL,
    role          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    level         TEXT,
    referrer_text TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT,
    PRIMARY KEY (telegram_id, role)
);

CREATE TABLE IF NOT EXISTS projects (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id        INTEGER NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    budget           INTEGER NOT NULL,
    contact_info     TEXT,
    country          TEXT,
    is_samozanyat    INTEGER DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'new',
    referrer_id      INTEGER,
    manager_id       INTEGER,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at     TEXT
);

CREATE TABLE IF NOT EXISTS project_team (
    project_id      INTEGER NOT NULL,
    telegram_id     INTEGER NOT NULL,
    role_in_project TEXT NOT NULL,
    share_percent   INTEGER NOT NULL,
    PRIMARY KEY (project_id, telegram_id)
);

CREATE TABLE IF NOT EXISTS payouts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL,
    telegram_id INTEGER,
    role        TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_ledger (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    delta      INTEGER NOT NULL,
    reason     TEXT,
    project_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rr_state (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    last_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    message     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO rr_state(id, last_index) VALUES (1, 0);
INSERT OR IGNORE INTO settings(key, value) VALUES
('about', '🇷🇺 SYNTH — российская команда разработчиков. Мы не нанимаем представителей недружественных стран и не ведём с ними сделок. Мы делаем Telegram-ботов, парсеры и Python-скрипты. Работаем за Stars. Качество гарантируем.');
"""

async def init(path: str) -> None:
    global DB_PATH
    DB_PATH = path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        
        # Миграции: если база старая, добавляем новые колонки
        try:
            await db.execute("SELECT age FROM users LIMIT 1")
        except Exception:
            await db.execute("ALTER TABLE users ADD COLUMN age INTEGER")
            await db.execute("ALTER TABLE users ADD COLUMN country TEXT")
            await db.execute("ALTER TABLE users ADD COLUMN is_samozanyat INTEGER DEFAULT 0")
            await db.commit()
            
        await db.commit()

def _conn():
    return aiosqlite.connect(DB_PATH)

# ==========================================
# USERS
# ==========================================

async def get_or_create_user(tg_user, referrer_id: Optional[int] = None) -> aiosqlite.Row:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE telegram_id=?",
                (tg_user.username, tg_user.full_name, tg_user.id),
            )
            await db.commit()
            return row
        await db.execute(
            "INSERT INTO users(telegram_id, username, full_name, referrer_id) VALUES(?,?,?,?)",
            (tg_user.id, tg_user.username, tg_user.full_name, referrer_id),
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        return await cur.fetchone()

async def update_user_profile(user_id: int, age: int, country: str, is_samozanyat: int) -> None:
    async with _conn() as db:
        await db.execute(
            "UPDATE users SET age=?, country=?, is_samozanyat=? WHERE telegram_id=?",
            (age, country, is_samozanyat, user_id)
        )
        await db.commit()

async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
        return await cur.fetchone()

async def find_by_ref_code(code: str) -> Optional[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE ref_code=?", (code,))
        return await cur.fetchone()

async def set_ref_code(user_id: int, code: str) -> None:
    async with _conn() as db:
        await db.execute("UPDATE users SET ref_code=? WHERE telegram_id=?", (code, user_id))
        await db.commit()

# ==========================================
# ROLES
# ==========================================

async def get_role(user_id: int, role: str) -> Optional[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE telegram_id=? AND role=?", (user_id, role))
        return await cur.fetchone()

async def upsert_role(user_id: int, role: str, status: str,
                      level: Optional[str] = None, referrer_text: Optional[str] = None) -> None:
    async with _conn() as db:
        await db.execute("""
            INSERT INTO roles(telegram_id, role, status, level, referrer_text, updated_at)
            VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id, role) DO UPDATE SET
                status=excluded.status,
                level=COALESCE(excluded.level, roles.level),
                referrer_text=COALESCE(excluded.referrer_text, roles.referrer_text),
                updated_at=CURRENT_TIMESTAMP
        """, (user_id, role, status, level, referrer_text))
        await db.commit()

async def has_active_role(user_id: int, role: str) -> bool:
    r = await get_role(user_id, role)
    return bool(r and r["status"] == "active")

async def list_active_by_role(role: str) -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE role=? AND status='active' ORDER BY telegram_id", (role,))
        return await cur.fetchall()

async def list_managers() -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE role='manager' ORDER BY telegram_id")
        return await cur.fetchall()

# ==========================================
# SETTINGS
# ==========================================

async def get_setting(key: str, default: str = "") -> str:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else default

async def set_setting(key: str, value: str) -> None:
    async with _conn() as db:
        await db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()

# ==========================================
# SUPPORT TICKETS
# ==========================================

async def create_ticket(user_id: int, message: str) -> int:
    async with _conn() as db:
        cur = await db.execute(
            "INSERT INTO support_tickets(user_id, message) VALUES(?,?)",
            (user_id, message)
        )
        await db.commit()
        return cur.lastrowid

async def get_open_tickets() -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM support_tickets WHERE status='open' ORDER BY id DESC")
        return await cur.fetchall()

async def close_ticket(ticket_id: int) -> None:
    async with _conn() as db:
        await db.execute("UPDATE support_tickets SET status='closed' WHERE id=?", (ticket_id,))
        await db.commit()

# ==========================================
# PROJECTS & STATS
# ==========================================

async def create_project(client_id: int, title: str, description: str, budget: int, 
                         contact_info: str, country: str, is_samozanyat: int, 
                         referrer_id: Optional[int], manager_id: int) -> int:
    async with _conn() as db:
        cur = await db.execute(
            "INSERT INTO projects(client_id, title, description, budget, contact_info, country, is_samozanyat, referrer_id, manager_id) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (client_id, title, description, budget, contact_info, country, is_samozanyat, referrer_id, manager_id),
        )
        await db.commit()
        return cur.lastrowid

async def get_project(project_id: int) -> Optional[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        return await cur.fetchone()

async def set_project_status(project_id: int, status: str) -> None:
    async with _conn() as db:
        await db.execute(
            "UPDATE projects SET status=?, completed_at=CASE WHEN ?='done' THEN CURRENT_TIMESTAMP ELSE completed_at END WHERE id=?",
            (status, status, project_id),
        )
        await db.commit()

async def delete_project(project_id: int) -> None:
    async with _conn() as db:
        await db.execute("DELETE FROM project_team WHERE project_id=?", (project_id,))
        await db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        await db.commit()

async def list_projects(limit: int = 50) -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,))
        return await cur.fetchall()

async def general_stats() -> dict:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async def scalar(sql: str, params: tuple = ()) -> int:
            cur = await db.execute(sql, params)
            row = await cur.fetchone()
            return row[0] if row else 0

        clients = await scalar("SELECT COUNT(*) FROM users")
        active_projects = await scalar("SELECT COUNT(*) FROM projects WHERE status IN ('new','assigned','in_progress')")
        done_projects = await scalar("SELECT COUNT(*) FROM projects WHERE status='done'")
        turnover = await scalar("SELECT COALESCE(SUM(budget),0) FROM projects")
        company = await scalar("SELECT COALESCE(SUM(delta),0) FROM company_ledger")

    return {
        "clients": clients,
        "active_projects": active_projects,
        "done_projects": done_projects,
        "turnover": turnover,
        "company": company,
    }

async def increment_discount_by_user_id(user_id: int) -> int:
    async with _conn() as db:
        await db.execute(
            "UPDATE users SET discount_percent = COALESCE(discount_percent, 0) + 1 WHERE telegram_id = ?",
            (user_id,)
        )
        await db.commit()
        cur = await db.execute("SELECT discount_percent FROM users WHERE telegram_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row and row[0] else 1

async def get_user_discount(user_id: int) -> int:
    async with _conn() as db:
        cursor = await db.execute("SELECT discount_percent FROM users WHERE telegram_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            return 0
        return row[0] or 0
