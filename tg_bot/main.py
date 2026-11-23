"""
SYNTH Platform v2.0 - Главный файл
===================================
Telegram-бот для управления заявками, поддержкой и админкой.
VK-бот отключён (переходим на VK Mini App).
"""
import asyncio
import logging
import os
import socket
import sys
import os
# Эта строка говорит Python'ю искать файлы на уровень выше, в корне проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta
from flask import Flask
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
# 4. ГЛАВНАЯ ФУНКЦИЯ
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
    asyncio.run(main())


