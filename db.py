import os
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime

DB_PATH = "data/synth.db"

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        if not self.conn:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row
            await self._init_schema()

    async def _init_schema(self):
        """Создаёт все таблицы при первом запуске (идемпотентно)"""
        await self.conn.executescript("""
            PRAGMA foreign_keys = ON;
            PRAGMA journal_mode = WAL;

            -- Пользователи (единые для TG и VK)
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                vk_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                channel TEXT NOT NULL DEFAULT 'tg',
                referrer_id INTEGER,
                discount_percent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Роли пользователей
            CREATE TABLE IF NOT EXISTS roles (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                level TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- Тикеты (заявки, поддержка, проекты)
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_number TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'new',
                title TEXT,
                description TEXT,
                budget INTEGER,
                assigned_team TEXT,
                assigned_manager INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- История изменений тикета
            CREATE TABLE IF NOT EXISTS ticket_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT NOT NULL,
                action TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_number) REFERENCES tickets(ticket_number)
            );

            -- Команды разработки
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                chat_id INTEGER NOT NULL,
                status TEXT DEFAULT 'free',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            -- Забаненные пользователи
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- Контент-задачи (Редактор -> QA -> Паблишер)
            CREATE TABLE IF NOT EXISTS content_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT,
                editor_id INTEGER NOT NULL,
                qa_id INTEGER,
                publisher_id INTEGER,
                description TEXT,
                file_url TEXT,
                status TEXT DEFAULT 'uploading',
                version INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_number) REFERENCES tickets(ticket_number)
            );

            -- Счётчик для генерации трек-номеров
            CREATE TABLE IF NOT EXISTS ticket_counter (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_number INTEGER DEFAULT 0
            );

            -- Инициализация счетчика и дефолтных команд
            INSERT OR IGNORE INTO ticket_counter(id, current_number) VALUES (1, 0);
            INSERT OR IGNORE INTO teams(name, chat_id, status) VALUES 
                ('Heavy', 0, 'free'), ('Medium 1', 0, 'free'), ('Medium 2', 0, 'free'),
                ('Fast 1', 0, 'free'), ('Fast 2', 0, 'free'), ('Fast 3', 0, 'free');
        """)
        await self.conn.commit()

    # === ПОЛЬЗОВАТЕЛИ ===
    async def get_or_create_user(self, telegram_id: Optional[int] = None, vk_id: Optional[int] = None, 
                                 username: str = None, full_name: str = None, referrer_id: Optional[int] = None) -> Dict:
        await self.connect()
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ? OR vk_id = ?", 
            (telegram_id, vk_id)
        )
        user = await cursor.fetchone()
        
        if user:
            await self.conn.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE id = ?", 
                (username, full_name, user['id'])
            )
            await self.conn.commit()
            return dict(user)
        
        channel = 'tg' if telegram_id else 'vk'
        cursor = await self.conn.execute("""
            INSERT INTO users (telegram_id, vk_id, username, full_name, channel, referrer_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (telegram_id, vk_id, username, full_name, channel, referrer_id))
        await self.conn.commit()
        
        user_id = cursor.lastrowid
        cursor = await self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(await cursor.fetchone())

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        await self.connect()
        cursor = await self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # === РОЛИ ===
    async def set_role(self, user_id: int, role: str, status: str = 'active', level: str = None):
        await self.connect()
        await self.conn.execute("""
            INSERT INTO roles (user_id, role, status, level)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = ?, status = ?, level = ?
        """, (user_id, role, status, level, role, status, level))
        await self.conn.commit()

    async def has_role(self, user_id: int, role: str) -> bool:
        await self.connect()
        cursor = await self.conn.execute("SELECT * FROM roles WHERE user_id = ? AND role = ? AND status = 'active'", (user_id, role))
        return await cursor.fetchone() is not None

    # === ТИКЕТЫ ===
    async def generate_ticket_number(self) -> str:
        await self.connect()
        cursor = await self.conn.execute("SELECT current_number FROM ticket_counter WHERE id = 1")
        row = await cursor.fetchone()
        current = row['current_number'] + 1
        
        year = datetime.now().year
        ticket_number = f"SYNTH-{year}-{current:04d}"
        
        await self.conn.execute("UPDATE ticket_counter SET current_number = ? WHERE id = 1", (current,))
        await self.conn.commit()
        return ticket_number

    async def create_ticket(self, user_id: int, channel: str, type: str, title: str = None, 
                            description: str = None, budget: int = None) -> Dict:
        await self.connect()
        ticket_number = await self.generate_ticket_number()
        
        await self.conn.execute("""
            INSERT INTO tickets (ticket_number, user_id, channel, type, title, description, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_number, user_id, channel, type, title, description, budget))
        await self.conn.commit()
        
        await self._add_ticket_history(ticket_number, 'created', None, 'new', user_id)
        
        cursor = await self.conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,))
        return dict(await cursor.fetchone())

    async def get_ticket(self, ticket_number: str) -> Optional[Dict]:
        await self.connect()
        cursor = await self.conn.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def update_ticket_status(self, ticket_number: str, new_status: str, changed_by: int):
        await self.connect()
        cursor = await self.conn.execute("SELECT status FROM tickets WHERE ticket_number = ?", (ticket_number,))
        row = await cursor.fetchone()
        old_status = row['status'] if row else None
        
        await self.conn.execute("""
            UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ticket_number = ?
        """, (new_status, ticket_number))
        
        if new_status == 'closed':
            await self.conn.execute("UPDATE tickets SET closed_at = CURRENT_TIMESTAMP WHERE ticket_number = ?", (ticket_number,))
        
        await self.conn.commit()
        await self._add_ticket_history(ticket_number, 'status_changed', old_status, new_status, changed_by)

    async def get_user_tickets(self, user_id: int) -> List[Dict]:
        await self.connect()
        cursor = await self.conn.execute("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in await cursor.fetchall()]

    async def _add_ticket_history(self, ticket_number: str, action: str, old_value: str, new_value: str, changed_by: int):
        await self.conn.execute("""
            INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_number, action, old_value, new_value, changed_by))
        await self.conn.commit()

    # === КОМАНДЫ ===
    async def get_all_teams(self) -> List[Dict]:
        await self.connect()
        cursor = await self.conn.execute("SELECT * FROM teams ORDER BY name")
        return [dict(row) for row in await cursor.fetchall()]

    async def update_team_status(self, team_name: str, status: str):
        await self.connect()
        await self.conn.execute("UPDATE teams SET status = ? WHERE name = ?", (status, team_name))
        await self.conn.commit()

    # === БАНЫ ===
    async def ban_user(self, user_id: int, reason: str = ""):
        await self.connect()
        await self.conn.execute("""
            INSERT INTO banned_users (user_id, reason) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET reason = ?
        """, (user_id, reason, reason))
        await self.conn.commit()

    async def unban_user(self, user_id: int):
        await self.connect()
        await self.conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def is_banned(self, user_id: int) -> bool:
        await self.connect()
        cursor = await self.conn.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None
    # ==========================================
# НОВЫЕ ФУНКЦИИ ДЛЯ ТИКЕТОВ (v2.0)
# ==========================================

async def _ensure_ticket_tables():
    """Добавляет таблицы для тикетов, если их нет"""
    async with _conn() as db:
        await db.executescript("""
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

            INSERT OR IGNORE INTO ticket_counter(id, current_number) VALUES (1, 0);
        """)
        await db.commit()

async def generate_ticket_number() -> str:
    """Генерирует трек-номер SYNTH-YYYY-NNNN"""
    from datetime import datetime
    await _ensure_ticket_tables()
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
                        description: str = None, budget: int = None) -> dict:
    """Создаёт новый тикет"""
    await _ensure_ticket_tables()
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

async def get_ticket(ticket_number: str):
    """Получает тикет по номеру"""
    await _ensure_ticket_tables()
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tickets WHERE ticket_number = ?", (ticket_number,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def update_ticket_status(ticket_number: str, new_status: str, changed_by: int):
    """Обновляет статус тикета с записью в историю"""
    await _ensure_ticket_tables()
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT status FROM tickets WHERE ticket_number = ?", (ticket_number,))
        row = await cur.fetchone()
        old_status = row["status"] if row else None
        
        await db.execute("""
            UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ticket_number = ?
        """, (new_status, ticket_number))
        
        if new_status == 'closed':
            await db.execute("""
                UPDATE tickets SET closed_at = CURRENT_TIMESTAMP WHERE ticket_number = ?
            """, (ticket_number,))
        
        await db.execute("""
            INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by)
            VALUES (?, 'status_changed', ?, ?, ?)
        """, (ticket_number, old_status, new_status, changed_by))
        await db.commit()

async def get_user_tickets(user_id: int) -> list:
    """Получает все тикеты пользователя"""
    await _ensure_ticket_tables()
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", 
            (user_id,)
        )
        return [dict(row) for row in await cur.fetchall()]

async def get_or_create_vk_user(vk_id: int, username: str = None, full_name: str = None) -> dict:
    """Создаёт или возвращает VK-пользователя (использует отрицательный telegram_id как ключ)"""
    tg_id = -vk_id  # Хак: используем отрицательный vk_id как telegram_id
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        
        await db.execute("""
            INSERT INTO users (telegram_id, username, full_name, ref_code)
            VALUES (?, ?, ?, ?)
        """, (tg_id, username or f"vk_{vk_id}", full_name or "VK User", f"vk_{vk_id}"))
        await db.commit()
        
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
        return dict(await cur.fetchone())

async def get_stats() -> dict:
    """Общая статистика (новая версия для v2.0)"""
    await _ensure_ticket_tables()
    async with _conn() as db:
        async def scalar(sql):
            cur = await db.execute(sql)
            row = await cur.fetchone()
            return row[0] if row else 0
        
        return {
            "total_users": await scalar("SELECT COUNT(*) FROM users"),
            "active_tickets": await scalar("SELECT COUNT(*) FROM tickets WHERE status != 'closed'"),
            "closed_tickets": await scalar("SELECT COUNT(*) FROM tickets WHERE status = 'closed'"),
            "total_budget": await scalar("SELECT COALESCE(SUM(budget), 0) FROM tickets WHERE budget IS NOT NULL"),
        }
# Глобальный экземпляр для импорта
db = Database()
