import os
from typing import Optional
import aiosqlite

DB_PATH = "data/bot.db"

SCHEMA = """
PRAGMA busy_timeout=5000;
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
    ref_code TEXT UNIQUE, referrer_id INTEGER, discount_percent INTEGER DEFAULT 0,
    age INTEGER, country TEXT, is_samozanyat INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    telegram_id INTEGER NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
    level TEXT, referrer_text TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT, PRIMARY KEY (telegram_id, role)
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, title TEXT NOT NULL,
    description TEXT NOT NULL, budget INTEGER NOT NULL, contact_info TEXT, country TEXT,
    is_samozanyat INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'new',
    referrer_id INTEGER, manager_id INTEGER, assigned_team TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT
);

CREATE TABLE IF NOT EXISTS company_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT, delta INTEGER NOT NULL, reason TEXT,
    project_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rr_state (
    id INTEGER PRIMARY KEY CHECK (id = 1), last_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open', created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vacations (
    manager_id INTEGER PRIMARY KEY, start_date TEXT, end_date TEXT
);

-- НОВАЯ ТАБЛИЦА: Команды разработки
CREATE TABLE IF NOT EXISTS teams (
    team_name TEXT PRIMARY KEY, chat_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'free'
);

INSERT OR IGNORE INTO rr_state(id, last_index) VALUES (1, 0);
INSERT OR IGNORE INTO settings(key, value) VALUES
('about', '🇷🇺 SYNTH — российская команда разработчиков. Мы не нанимаем представителей недружественных стран и не ведём с ними сделок. Мы делаем Telegram-ботов, парсеры и Python-скрипты. Работаем за Stars. Качество гарантируем.');

-- Инициализация команд (если их еще нет в базе)
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES ('Heavy', 0, 'free');
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES ('Medium 1', 0, 'free');
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES ('Medium 2', 0, 'free');
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES ('Fast 1', 0, 'free');
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES ('Fast 2', 0, 'free');
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES ('Fast 3', 0, 'free');
"""

async def init(path: str) -> None:
    global DB_PATH
    DB_PATH = path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

def _conn():
    return aiosqlite.connect(DB_PATH)

# ==========================================
# USERS & ROLES
# ==========================================
async def get_or_create_user(tg_user, referrer_id: Optional[int] = None) -> aiosqlite.Row:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE users SET username=?, full_name=? WHERE telegram_id=?", (tg_user.username, tg_user.full_name, tg_user.id))
            await db.commit()
            return row
        await db.execute("INSERT INTO users(telegram_id, username, full_name, referrer_id) VALUES(?,?,?,?)", (tg_user.id, tg_user.username, tg_user.full_name, referrer_id))
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        return await cur.fetchone()

async def get_all_users() -> list[int]:
    async with _conn() as db:
        cur = await db.execute("SELECT telegram_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]

async def get_role(user_id: int, role: str) -> Optional[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE telegram_id=? AND role=?", (user_id, role))
        return await cur.fetchone()

async def upsert_role(user_id: int, role: str, status: str, level: Optional[str] = None, referrer_text: Optional[str] = None) -> None:
    async with _conn() as db:
        await db.execute("""INSERT INTO roles(telegram_id, role, status, level, referrer_text, updated_at)
            VALUES(?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(telegram_id, role) DO UPDATE SET
            status=excluded.status, level=COALESCE(excluded.level, roles.level),
            referrer_text=COALESCE(excluded.referrer_text, roles.referrer_text), updated_at=CURRENT_TIMESTAMP""",
            (user_id, role, status, level, referrer_text))
        await db.commit()

async def has_active_role(user_id: int, role: str) -> bool:
    r = await get_role(user_id, role)
    return bool(r and r["status"] == "active")

async def list_managers() -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE role='manager' ORDER BY telegram_id")
        return await cur.fetchall()

async def list_recipients(owner_id: int) -> list[int]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT telegram_id FROM roles WHERE role='manager' AND status='active'")
        rows = await cur.fetchall()
    return [owner_id] + [r["telegram_id"] for r in rows]

async def next_recipient(owner_id: int) -> int:
    recipients = await list_recipients(owner_id)
    if not recipients: return owner_id
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT last_index FROM rr_state WHERE id=1")
        row = await cur.fetchone()
        last = row["last_index"] if row else 0
        idx = last % len(recipients)
        chosen = recipients[idx]
        await db.execute("UPDATE rr_state SET last_index=? WHERE id=1", ((idx + 1) % len(recipients),))
        await db.commit()
    return chosen

# ==========================================
# TEAMS (КОМАНДЫ)
# ==========================================
async def get_all_teams() -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM teams ORDER BY team_name")
        return await cur.fetchall()

async def update_team_status(team_name: str, status: str) -> None:
    async with _conn() as db:
        await db.execute("UPDATE teams SET status=? WHERE team_name=?", (status, team_name))
        await db.commit()

async def update_team_chat_id(team_name: str, chat_id: int) -> None:
    async with _conn() as db:
        await db.execute("UPDATE teams SET chat_id=? WHERE team_name=?", (chat_id, team_name))
        await db.commit()

# ==========================================
# PROJECTS
# ==========================================
async def create_project(client_id: int, title: str, description: str, budget: int, 
                         contact_info: str, country: str, is_samozanyat: int, 
                         referrer_id: Optional[int], manager_id: int) -> int:
    async with _conn() as db:
        cur = await db.execute("INSERT INTO projects(client_id, title, description, budget, contact_info, country, is_samozanyat, referrer_id, manager_id) VALUES(?,?,?,?,?,?,?,?,?)",
            (client_id, title, description, budget, contact_info, country, is_samozanyat, referrer_id, manager_id))
        await db.commit()
        return cur.lastrowid

async def get_project(project_id: int) -> Optional[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM projects WHERE id=?", (project_id,))
        return await cur.fetchone()

async def set_project_status(project_id: int, status: str, team_name: Optional[str] = None) -> None:
    async with _conn() as db:
        if team_name:
            await db.execute("UPDATE projects SET status=?, assigned_team=? WHERE id=?", (status, team_name, project_id))
        else:
            await db.execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))
        await db.commit()

async def list_projects(limit: int = 50) -> list[aiosqlite.Row]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,))
        return await cur.fetchall()

async def general_stats() -> dict:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async def scalar(sql: str) -> int:
            cur = await db.execute(sql)
            row = await cur.fetchone()
            return row[0] if row else 0
        return {
            "clients": await scalar("SELECT COUNT(*) FROM users"),
            "active_projects": await scalar("SELECT COUNT(*) FROM projects WHERE status IN ('new','assigned')"),
            "done_projects": await scalar("SELECT COUNT(*) FROM projects WHERE status='done'"),
            "turnover": await scalar("SELECT COALESCE(SUM(budget),0) FROM projects"),
            "company": await scalar("SELECT COALESCE(SUM(delta),0) FROM company_ledger"),
        }

async def increment_discount_by_user_id(user_id: int) -> int:
    async with _conn() as db:
        await db.execute("UPDATE users SET discount_percent = COALESCE(discount_percent, 0) + 15 WHERE telegram_id = ?", (user_id,))
        await db.commit()
        cur = await db.execute("SELECT discount_percent FROM users WHERE telegram_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row and row[0] else 15

async def get_user_discount(user_id: int) -> int:
    async with _conn() as db:
        cursor = await db.execute("SELECT discount_percent FROM users WHERE telegram_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0
