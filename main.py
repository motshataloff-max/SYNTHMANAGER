import sys, os, logging, socket, asyncio, sqlite3, secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from threading import Thread
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, FSInputFile

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, "handlershandlers"))

import db
from config import config
from handlershandlers import common, client, fix_code, deploy, partner, support, tickets, admin

app = Flask(__name__)
@app.route('/')
def health_check(): return "SYNTH Platform v2.0 is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

def _patch_dns() -> None:
    _orig = socket.getaddrinfo
    def _patched(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.telegram.org": return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]
        return _orig(host, port, family, type, proto, flags)
    socket.getaddrinfo = _patched

async def daily_backup_task(bot: Bot):
    while True:
        now = datetime.now()
        target = now.replace(hour=4, minute=0, second=0, microsecond=0)
        if now >= target: target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f"synth_backup_{date_str}.db"
            doc = FSInputFile(config.db_path, filename=filename)
            await bot.send_document(chat_id=config.ceo_group_id, document=doc, caption=f"💾 Бэкап БД {date_str}")
            logging.info(f"✅ Бэкап БД отправлен ({filename})")
        except Exception as e:
            logging.error(f"❌ Ошибка бэкапа БД: {e}")

@app.route('/vk-app')
def vk_app_page():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "vk_mini_app", "frontend", "index.html")
    try:
        with open(html_path, 'r', encoding='utf-8') as f: return f.read()
    except FileNotFoundError: return "Ошибка: файл index.html не найден", 500

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
    cur = conn.execute("SELECT ticket_number, title, status FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (-int(vk_id),))
    tickets = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify({"tickets": tickets})

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    await db.init(config.db_path)
    logging.info("✅ База данных инициализирована")
    proxy = os.getenv("PROXY_URL", "").strip()
    session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
    if not proxy: _patch_dns()
    bot = Bot(config.bot_token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(client.router)
    dp.include_router(fix_code.router)
    dp.include_router(deploy.router)
    dp.include_router(partner.router)
    dp.include_router(support.router)
    dp.include_router(tickets.router)
    dp.include_router(common.router)
    dp.include_router(admin.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="cancel", description="❌ Отменить"),
        BotCommand(command="backup_db", description="💾 Ручной бэкап"),
    ])
    Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(daily_backup_task(bot))
    logging.info("🚀 SYNTH Platform v2.0 started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
