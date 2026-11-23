import sys
import os

# 🔥 МАГИЧЕСКИЙ БЛОК: автоматически находит папку handlers, где бы она ни лежала
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(current_dir, "tg_bot", "handlers")):
    sys.path.insert(0, os.path.join(current_dir, "tg_bot"))
else:
    sys.path.insert(0, current_dir)

import logging
import socket
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, FSInputFile, BufferedInputFile

import db
from config import config
from handlers import admin, client, common, dev, partner, projects, support, tickets

# ... ДАЛЬШЕ ВЕСЬ ОСТАЛЬНОЙ ТВОЙ КОД БЕЗ ИЗМЕНЕНИЙ ...

# ==========================================
# 1. FLASK ДЛЯ RAILWAY
# ==========================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "SYNTH Platform v2.0 is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ==========================================
# 2. DNS-ПАТЧ ДЛЯ TELEGRAM
# ==========================================
def _patch_dns() -> None:
    _orig = socket.getaddrinfo
    def _patched(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.telegram.org":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]
        return _orig(host, port, family, type, proto, flags)
    socket.getaddrinfo = _patched

# ==========================================
# 3. ФОНОВЫЕ ЗАДАЧИ
# ==========================================
async def hourly_report_task(bot: Bot):
    while True:
        await asyncio.sleep(3600)
        try:
            stats = await db.general_stats()
            text = (
                f"🟢 <b>Часовая сводка SYNTH</b>\n"
                f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')} UTC\n\n"
                f"👥 Пользователей: <b>{stats['clients']}</b>\n"
                f"📦 Активных проектов: <b>{stats['active_projects']}</b>\n"
                f"✅ Завершённых: <b>{stats['done_projects']}</b>\n"
                f"💰 Оборот: <b>{stats['turnover']} ₽</b>"
            )
            await bot.send_message(config.ceo_group_id, text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка часового отчёта: {e}")

async def daily_report_task(bot: Bot):
    while True:
        now = datetime.now()
        target = now.replace(hour=4, minute=30, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        
        try:
            stats = await db.general_stats()
            lines = [
                f"📊 ЕЖЕДНЕВНЫЙ ОТЧЁТ SYNTH",
                f"📅 {datetime.now().strftime('%d.%m.%Y')}",
                "=" * 40,
                f"👥 Всего клиентов: {stats['clients']}",
                f"📦 Активных проектов: {stats['active_projects']}",
                f"✅ Завершённых: {stats['done_projects']}",
                f"💰 Оборот: {stats['turnover']} ₽",
            ]
            file_bytes = "\n".join(lines).encode("utf-8")
            await bot.send_document(
                chat_id=config.ceo_group_id,
                document=BufferedInputFile(file_bytes, filename=f"synth_daily_{datetime.now().strftime('%Y%m%d')}.txt"),
                caption="📦 Ежедневный отчёт"
            )
        except Exception as e:
            logging.error(f"Ошибка ежедневного отчёта: {e}")

async def daily_backup_task(bot: Bot):
    while True:
        now = datetime.now()
        target = now.replace(hour=4, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        seconds_to_wait = (target - now).total_seconds()
        logging.info(f"💾 Следующий бэкап БД через {seconds_to_wait/3600:.1f} часов")
        await asyncio.sleep(seconds_to_wait)
        
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f"synth_backup_{date_str}.db"
            file_size_kb = os.path.getsize(config.db_path) / 1024
            
            doc = FSInputFile(config.db_path, filename=filename)
            await bot.send_document(
                chat_id=config.owner_id,
                document=doc,
                caption=f"💾 <b>Ежедневный бэкап БД SYNTH</b>\n📅 Дата: {date_str}\n📦 Размер: {file_size_kb:.1f} KB",
                parse_mode="HTML"
            )
            
            if config.ping_chat_id != config.owner_id:
                doc2 = FSInputFile(config.db_path, filename=filename)
                await bot.send_document(chat_id=config.ping_chat_id, document=doc2, caption=f"💾 Бэкап БД {date_str}")
            logging.info(f"✅ Бэкап БД отправлен ({filename})")
        except Exception as e:
            logging.error(f"❌ Ошибка бэкапа БД: {e}")

# ==========================================
# 4. VK MINI APP API (ЧИТАЕТ ИЗ ФАЙЛА)
# ==========================================
import sqlite3
import secrets
from datetime import datetime

@app.route('/vk-app')
def vk_app_page():
    """Отдает HTML-страницу для VK Mini App из отдельного файла"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(base_dir, "vk_mini_app", "frontend", "index.html")
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Ошибка: файл vk_mini_app/frontend/index.html не найден", 500

def get_db_sync():
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/vk/login', methods=['POST'])
def vk_login():
    data = request.json
    vk_id = data.get('vk_id')
    client_code = data.get('client_code', '').upper().strip()
    if not vk_id: return jsonify({"error": "vk_id required"}), 400
    
    conn = get_db_sync()
    cur = conn.execute("SELECT * FROM users WHERE vk_id = ?", (vk_id,))
    user = cur.fetchone()
    if user:
        conn.close()
        return jsonify({"success": True, "user": dict(user), "message": "С возвращением!"})
    
    if client_code:
        cur = conn.execute("SELECT * FROM users WHERE client_code = ?", (client_code,))
        user = cur.fetchone()
        if user:
            conn.execute("UPDATE users SET vk_id = ? WHERE telegram_id = ?", (vk_id, user['telegram_id']))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "user": dict(user), "message": "Аккаунты связаны!"})
        else:
            conn.close()
            return jsonify({"error": "Неверный код клиента"}), 404
    
    new_code = f"SYNTH-{secrets.token_hex(2).upper()}"
    conn.execute("INSERT INTO users (telegram_id, username, full_name, client_code, vk_id) VALUES (?, ?, ?, ?, ?)",
                 (-int(vk_id), f"vk_{vk_id}", f"VK Пользователь", new_code, vk_id))
    conn.commit()
    cur = conn.execute("SELECT * FROM users WHERE vk_id = ?", (vk_id,))
    user = cur.fetchone()
    conn.close()
    return jsonify({"success": True, "user": dict(user), "message": f"Создан аккаунт. Код: {new_code}"})

@app.route('/api/vk/tickets', methods=['GET'])
def vk_get_tickets():
    vk_id = request.args.get('vk_id')
    if not vk_id: return jsonify({"error": "vk_id required"}), 400
    conn = get_db_sync()
    cur = conn.execute("""
        SELECT ticket_number, title, budget, status FROM tickets 
        WHERE user_id = ? OR user_id = (SELECT telegram_id FROM users WHERE vk_id = ?)
        ORDER BY created_at DESC
    """, (-int(vk_id), vk_id))
    tickets = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify({"tickets": tickets})

@app.route('/api/vk/order', methods=['POST'])
def vk_create_order():
    data = request.json
    vk_id, title, budget = data.get('vk_id'), data.get('title'), data.get('budget')
    if not all([vk_id, title, budget]): return jsonify({"error": "Заполните поля"}), 400
    
    conn = get_db_sync()
    cur = conn.execute("SELECT telegram_id FROM users WHERE vk_id = ?", (vk_id,))
    row = cur.fetchone()
    user_id = row['telegram_id'] if row else -int(vk_id)
    
    cur = conn.execute("SELECT current_number FROM ticket_counter WHERE id = 1")
    current = (cur.fetchone()[0] if cur.fetchone() else 0) + 1
    ticket_number = f"SYNTH-{datetime.now().year}-{current:04d}"
    conn.execute("UPDATE ticket_counter SET current_number = ? WHERE id = 1", (current,))
    
    conn.execute("INSERT INTO tickets (ticket_number, user_id, channel, type, title, description, budget, status) VALUES (?, ?, 'vk', 'project', ?, ?, ?, 'new')",
                 (ticket_number, user_id, title, f"{data.get('description', '')}\n📱 {data.get('contact', '')}", budget))
    conn.execute("INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by) VALUES (?, 'created', NULL, 'new', ?)", (ticket_number, user_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "ticket_number": ticket_number})

@app.route('/api/vk/support', methods=['POST'])
def vk_create_support():
    data = request.json
    vk_id, message = data.get('vk_id'), data.get('message')
    if not all([vk_id, message]): return jsonify({"error": "Введите сообщение"}), 400
    
    conn = get_db_sync()
    cur = conn.execute("SELECT telegram_id FROM users WHERE vk_id = ?", (vk_id,))
    row = cur.fetchone()
    user_id = row['telegram_id'] if row else -int(vk_id)
    
    cur = conn.execute("SELECT current_number FROM ticket_counter WHERE id = 1")
    current = (cur.fetchone()[0] if cur.fetchone() else 0) + 1
    ticket_number = f"SYNTH-{datetime.now().year}-{current:04d}"
    conn.execute("UPDATE ticket_counter SET current_number = ? WHERE id = 1", (current,))
    
    conn.execute("INSERT INTO tickets (ticket_number, user_id, channel, type, title, description, status) VALUES (?, ?, 'vk', 'support', 'Обращение (VK)', ?, 'new')",
                 (ticket_number, user_id, message))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "ticket_number": ticket_number})

# ==========================================
# 5. ГЛАВНАЯ ФУНКЦИЯ
# ==========================================
async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    await db.init(config.db_path)
    logging.info("✅ База данных инициализирована")

    proxy = os.getenv("PROXY_URL", "").strip()
    session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
    if not proxy: 
        _patch_dns()

    bot = Bot(config.bot_token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # 🔥 ПОРЯДОК ПОДКЛЮЧЕНИЯ РОУТЕРОВ
    dp.include_router(support.router)
    dp.include_router(tickets.router)
    dp.include_router(client.router)
    dp.include_router(dev.router)
    dp.include_router(partner.router)
    dp.include_router(projects.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)

    await bot.delete_webhook(drop_pending_updates=True)
    
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="status", description="📋 Проверить статус тикета"),
        BotCommand(command="my_tickets", description="📂 Мои заявки"),
        BotCommand(command="cancel", description="❌ Отменить"),
        BotCommand(command="ban", description="🚫 Забанить (CEO)"),
        BotCommand(command="unban", description="✅ Разбанить (CEO)"),
        BotCommand(command="backup_db", description="💾 Ручной бэкап"),
    ])
    logging.info("✅ Меню команд обновлено")

    Thread(target=run_flask, daemon=True).start()
    logging.info("🌐 Flask started")
    
    asyncio.create_task(hourly_report_task(bot))
    asyncio.create_task(daily_report_task(bot))
    asyncio.create_task(daily_backup_task(bot))
    
    logging.info("🚀 SYNTH Platform v2.0 started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

