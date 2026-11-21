import asyncio, logging, os, socket
from datetime import datetime, time, timedelta
from flask import Flask
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BufferedInputFile

import db
from config import config
from handlers import admin, client, common, dev, partner, projects, support

app = Flask(__name__)
@app.route('/')
def health_check(): return "SYNTH Bot v6.1 is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def _patch_dns() -> None:
    _orig = socket.getaddrinfo
    def _patched(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.telegram.org": return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]
        return _orig(host, port, family, type, proto, flags)
    socket.getaddrinfo = _patched

async def hourly_report_task(bot: Bot):
    while True:
        await asyncio.sleep(3600)
        try:
            stats = await db.general_stats()
            text = f"🟢 <b>Часовая сводка SYNTH</b>\n🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')} UTC\n\n👥 Пользователей: <b>{stats['clients']}</b>\n📦 Активных: <b>{stats['active_projects']}</b>\n✅ Завершённых: <b>{stats['done_projects']}</b>\n💰 Оборот: <b>{stats['turnover']} ⭐</b>"
            await bot.send_message(config.ceo_group_id, text, parse_mode="HTML")
        except Exception as e: logging.error(f"Ошибка отчёта: {e}")

async def daily_report_task(bot: Bot):
    while True:
        now = datetime.utcnow()
        target = time(4, 30)
        next_run = datetime.combine(now.date() + (timedelta(days=1) if now.time() >= target else timedelta(days=0)), target)
        await asyncio.sleep((next_run - now).total_seconds())
        try:
            stats = await db.general_stats()
            lines = [f"📊 ЕЖЕДНЕВНЫЙ ОТЧЁТ SYNTH\n📅 {datetime.utcnow().strftime('%d.%m.%Y')}", "="*40,
                     f"👥 Пользователей: {stats['clients']}", f"📦 Активных: {stats['active_projects']}",
                     f"💰 Оборот: {stats['turnover']} ⭐", f"🏦 Счёт: {stats['company']} ⭐"]
            file_bytes = "\n".join(lines).encode("utf-8")
            await bot.send_document(chat_id=config.ceo_group_id, document=BufferedInputFile(file_bytes, filename=f"synth_daily_{datetime.utcnow().strftime('%Y%m%d')}.txt"), caption="📦 Ежедневный отчёт")
        except Exception as e: logging.error(f"Ошибка отчёта: {e}")

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    await db.init(config.db_path)

    proxy = os.getenv("PROXY_URL", "").strip()
    session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
    if not proxy: _patch_dns()

    bot = Bot(config.bot_token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(client.router)
    dp.include_router(dev.router)
    dp.include_router(partner.router)
    dp.include_router(support.router)
    dp.include_router(projects.router)
    dp.include_router(admin.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="cancel", description="❌ Отменить"),
        BotCommand(command="ban", description="🚫 Забанить (CEO)"),
        BotCommand(command="unban", description="✅ Разбанить (CEO)"),
        BotCommand(command="backup_db", description="💾 Бэкап"),
    ])
    logging.info("✅ Меню команд обновлено!")

    Thread(target=run_flask, daemon=True).start()
    logging.info("🌐 Flask started")
    
    asyncio.create_task(hourly_report_task(bot))
    asyncio.create_task(daily_report_task(bot))
    
    logging.info("🚀 SYNTH Bot v6.1 started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
