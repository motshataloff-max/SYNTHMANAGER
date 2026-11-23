"""
SYNTH Platform v2.0 - Единая база данных
=========================================
Все операции с данными проходят через этот модуль.
Используется aiosqlite для асинхронной работы с SQLite.
"""
import os
import aiosqlite
import secrets
from typing import Optional, List, Dict
from datetime import datetime

# Путь к файлу базы данных
DB_PATH = "data/bot.db"

# Полная схема базы данных (все таблицы)
SCHEMA = """
PRAGMA busy_timeout=5000;
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    ref_code TEXT UNIQUE,
    referrer_id INTEGER,
    discount_percent INTEGER DEFAULT 0,
    age INTEGER,
    country TEXT,
    is_samozanyat INTEGER DEFAULT 0,
    client_code TEXT UNIQUE,
    vk_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    telegram_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    level TEXT,
    referrer_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    PRIMARY KEY (telegram_id, role)
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    budget INTEGER NOT NULL,
    contact_info TEXT,
    country TEXT,
    is_samozanyat INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'new',
    referrer_id INTEGER,
    manager_id INTEGER,
    assigned_team TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS company_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delta INTEGER NOT NULL,
    reason TEXT,
    project_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rr_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    topic_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vacations (
    manager_id INTEGER PRIMARY KEY,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    team_name TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS banned_users (
    telegram_id INTEGER PRIMARY KEY,
    reason TEXT,
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
    budget INTEGER,
    assigned_team TEXT,
    assigned_manager INTEGER,
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

-- Начальные данные
INSERT OR IGNORE INTO rr_state(id, last_index) VALUES (1, 0);
INSERT OR IGNORE INTO ticket_counter(id, current_number) VALUES (1, 0);
INSERT OR IGNORE INTO settings(key, value) VALUES ('about', '🇷🇺 SYNTH — российская команда разработчиков. Работаем с РФ и дружественными странами.');
INSERT OR IGNORE INTO teams(team_name, chat_id, status) VALUES 
    ('Heavy', 0, 'free'), 
    ('Medium 1', 0, 'free'), 
    ('Medium 2', 0, 'free'),
    ('Fast 1', 0, 'free'), 
    ('Fast 2', 0, 'free'), 
    ('Fast 3', 0, 'free');
"""

# ==========================================
# БАЗОВЫЕ ФУНКЦИИ ПОДКЛЮЧЕНИЯ
# ==========================================
def _conn():
    """Возвращает контекст-менеджер подключения к БД"""
    return aiosqlite.connect(DB_PATH)

async def init(path: str) -> None:
    """Инициализация базы данных (создание таблиц и начальных данных)"""
    global DB_PATH
    DB_PATH = path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()

# ==========================================
# БЛОК: ПОЛЬЗОВАТЕЛИ (USERS)
# ==========================================
async def get_or_create_user(tg_user, referrer_id: Optional[int] = None) -> Dict:
    """Получает или создаёт Telegram-пользователя"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE telegram_id=?",
                (tg_user.username, tg_user.full_name, tg_user.id)
            )
            await db.commit()
            return dict(row)
        await db.execute(
            "INSERT INTO users(telegram_id, username, full_name, referrer_id) VALUES(?,?,?,?)",
            (tg_user.id, tg_user.username, tg_user.full_name, referrer_id)
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_user.id,))
        return dict(await cur.fetchone())

async def get_user(user_id: int) -> Optional[Dict]:
    """Получает пользователя по telegram_id"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def get_or_create_vk_user(vk_id: int, username: str = None, full_name: str = None) -> Dict:
    """Получает или создаёт VK-пользователя (использует отрицательный vk_id как telegram_id)"""
    tg_id = -vk_id
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        await db.execute(
            "INSERT INTO users (telegram_id, username, full_name, ref_code) VALUES (?, ?, ?, ?)",
            (tg_id, username or f"vk_{vk_id}", full_name or "VK User", f"vk_{vk_id}")
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
        return dict(await cur.fetchone())

# ==========================================
# БЛОК: ЛИЧНЫЙ КОД КЛИЕНТА (НОВОЕ)
# ==========================================
async def generate_client_code() -> str:
    """Генерирует уникальный личный код клиента формата SYNTH-XXXX"""
    while True:
        code = f"SYNTH-{secrets.token_hex(2).upper()}"
        async with _conn() as db:
            cur = await db.execute("SELECT 1 FROM users WHERE client_code = ?", (code,))
            if not await cur.fetchone():
                return code

async def get_user_by_client_code(client_code: str) -> Optional[Dict]:
    """Ищет пользователя по личному коду"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE client_code = ?", (client_code.upper(),))
        row = await cur.fetchone()
        return dict(row) if row else None

async def ensure_client_code(user_id: int) -> str:
    """Гарантирует, что у пользователя есть личный код. Если нет — генерирует."""
    user = await get_user(user_id)
    if user and user.get('client_code'):
        return user['client_code']
    
    code = await generate_client_code()
    async with _conn() as db:
        await db.execute("UPDATE users SET client_code = ? WHERE telegram_id = ?", (code, user_id))
        await db.commit()
    return code

async def link_vk_to_user(telegram_id: int, vk_id: int) -> bool:
    """Привязывает VK ID к существующему пользователю"""
    async with _conn() as db:
        await db.execute("UPDATE users SET vk_id = ? WHERE telegram_id = ?", (vk_id, telegram_id))
        await db.commit()
        return True

async def get_user_by_vk_id(vk_id: int) -> Optional[Dict]:
    """Ищет пользователя по VK ID"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE vk_id = ?", (vk_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

# ==========================================
# БЛОК: РОЛИ (ROLES)
# ==========================================
async def get_role(user_id: int, role: str) -> Optional[Dict]:
    """Получает роль пользователя"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE telegram_id=? AND role=?", (user_id, role))
        row = await cur.fetchone()
        return dict(row) if row else None

async def has_active_role(user_id: int, role: str) -> bool:
    """Проверяет, есть ли у пользователя активная роль"""
    r = await get_role(user_id, role)
    return bool(r and r["status"] == "active")

async def list_active_by_role(role: str) -> List[Dict]:
    """Список всех пользователей с активной ролью"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM roles WHERE role=? AND status='active' ORDER BY telegram_id",
            (role,)
        )
        return [dict(r) for r in await cur.fetchall()]

async def list_managers() -> List[Dict]:
    """Список всех менеджеров"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roles WHERE role='manager' ORDER BY telegram_id")
        return [dict(r) for r in await cur.fetchall()]

async def upsert_role(user_id: int, role: str, status: str, level: Optional[str] = None, 
                      referrer_text: Optional[str] = None) -> None:
    """Создаёт или обновляет роль пользователя"""
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

# ==========================================
# БЛОК: БАНЫ (BANS)
# ==========================================
async def is_banned(user_id: int) -> bool:
    """Проверяет, забанен ли пользователь"""
    async with _conn() as db:
        cur = await db.execute("SELECT 1 FROM banned_users WHERE telegram_id=?", (user_id,))
        return await cur.fetchone() is not None

async def ban_user(user_id: int, reason: str = "") -> None:
    """Банит пользователя"""
    async with _conn() as db:
        await db.execute(
            "INSERT OR REPLACE INTO banned_users(telegram_id, reason) VALUES(?,?)",
            (user_id, reason)
        )
        await db.commit()

async def unban_user(user_id: int) -> None:
    """Разбанивает пользователя"""
    async with _conn() as db:
        await db.execute("DELETE FROM banned_users WHERE telegram_id=?", (user_id,))
        await db.commit()

# ==========================================
# БЛОК: КОМАНДЫ РАЗРАБОТЧИКОВ (TEAMS)
# ==========================================
async def get_all_teams() -> List[Dict]:
    """Получает список всех команд"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM teams ORDER BY team_name")
        return [dict(r) for r in await cur.fetchall()]

async def update_team_status(team_name: str, status: str) -> None:
    """Обновляет статус команды"""
    async with _conn() as db:
        await db.execute("UPDATE teams SET status=? WHERE team_name=?", (status, team_name))
        await db.commit()

async def update_team_chat_id(team_name: str, chat_id: int) -> None:
    """Обновляет chat_id команды"""
    async with _conn() as db:
        await db.execute("UPDATE teams SET chat_id=? WHERE team_name=?", (chat_id, team_name))
        await db.commit()

# ==========================================
# БЛОК: ТИКЕТЫ (TICKETS)
# ==========================================
async def generate_ticket_number() -> str:
    """Генерирует уникальный трек-номер формата SYNTH-YYYY-NNNN"""
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

async def create_ticket(user_id: int, channel: str, type: str, title: str = None, 
                        description: str = None, budget: int = None) -> Dict:
    """Создаёт новый тикет (заявку)"""
    ticket_number = await generate_ticket_number()
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("""
            INSERT INTO tickets (ticket_number, user_id, channel, type, title, description, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_number, user_id, channel, type, title, description, budget))
        await db.execute("""
            INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by)
            VALUES (?, 'created', NULL, 'new', ?)
        """, (ticket_number, user_id))
        await db.commit()
        cur = await db.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,))
        return dict(await cur.fetchone())

async def get_ticket(ticket_number: str) -> Optional[Dict]:
    """Получает тикет по номеру"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def update_ticket_status(ticket_number: str, new_status: str, changed_by: int) -> None:
    """Обновляет статус тикета с записью в историю"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT status FROM tickets WHERE ticket_number = ?", (ticket_number,))
        row = await cur.fetchone()
        old_status = row["status"] if row else None
        await db.execute(
            "UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ticket_number = ?",
            (new_status, ticket_number)
        )
        if new_status == 'closed':
            await db.execute(
                "UPDATE tickets SET closed_at = CURRENT_TIMESTAMP WHERE ticket_number = ?",
                (ticket_number,)
            )
        await db.execute("""
            INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by)
            VALUES (?, 'status_changed', ?, ?, ?)
        """, (ticket_number, old_status, new_status, changed_by))
        await db.commit()

async def get_user_tickets(user_id: int) -> List[Dict]:
    """Получает все тикеты пользователя"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return [dict(row) for row in await cur.fetchall()]

async def get_all_active_tickets() -> List[Dict]:
    """Получает все активные (не закрытые) тикеты для админки"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM tickets WHERE status != 'closed' ORDER BY created_at DESC LIMIT 20"
        )
        return [dict(row) for row in await cur.fetchall()]

# ==========================================
# БЛОК: МОДЕРАЦИЯ И БАНЫ (АДМИНКА)
# ==========================================
async def get_pending_roles() -> List[Dict]:
    """Получает все заявки на роли со статусом pending (для модерации)"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT r.*, u.username, u.full_name 
            FROM roles r 
            LEFT JOIN users u ON r.telegram_id = u.telegram_id
            WHERE r.status = 'pending'
            ORDER BY r.created_at DESC
            LIMIT 50
        """)
        return [dict(row) for row in await cur.fetchall()]

async def get_all_banned_users() -> List[Dict]:
    """Получает список всех забаненных пользователей"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT b.*, u.username, u.full_name 
            FROM banned_users b 
            LEFT JOIN users u ON b.telegram_id = u.telegram_id
            ORDER BY b.created_at DESC
        """)
        return [dict(row) for row in await cur.fetchall()]

# ==========================================
# БЛОК: СТАТИСТИКА И НАСТРОЙКИ
# ==========================================
async def general_stats() -> Dict:
    """Общая статистика системы"""
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
            "active_tickets": await scalar("SELECT COUNT(*) FROM tickets WHERE status != 'closed'"),
            "closed_tickets": await scalar("SELECT COUNT(*) FROM tickets WHERE status = 'closed'"),
        }

async def get_user_discount(user_id: int) -> int:
    """Получает скидку пользователя"""
    async with _conn() as db:
        cursor = await db.execute("SELECT discount_percent FROM users WHERE telegram_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0

async def get_setting(key: str) -> str:
    """Получает значение настройки по ключу"""
    async with _conn() as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else ""

async def set_ref_code(user_id: int, code: str) -> None:
    """Устанавливает реферальный код пользователя"""
    async with _conn() as db:
        await db.execute("UPDATE users SET ref_code=? WHERE telegram_id=?", (code, user_id))
        await db.commit()

async def pr_stats(user_id: int) -> Dict:
    """Статистика пиарщика/партнёра"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT COUNT(*) c FROM users WHERE referrer_id=?", (user_id,))
        clients = (await cur.fetchone())["c"]
        cur = await db.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(budget),0) s FROM projects WHERE referrer_id=?",
            (user_id,)
        )
        row = await cur.fetchone()
        return {
            "clients": clients,
            "orders": row["c"],
            "total": row["s"],
            "earned": 0
        }

async def list_projects(limit: int = 50) -> List[Dict]:
    """Список проектов (для обратной совместимости)"""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in await cur.fetchall()]


