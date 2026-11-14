import asyncio
import logging
import os
import socket
from datetime import datetime
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

# ==========================================
# 1. FLASK ДЛЯ RAILWAY (HEALTH CHECK)
# ==========================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "SYNTH Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. ОБХОД БЛОКИРОВОК
# ==========================================
def _patch_dns() -> None:
    _orig = socket.getaddrinfo
    def _patched(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.telegram.org":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]
        return _orig(host, port, family, type, proto, flags)
    socket.getaddrinfo = _patched

# ==========================================
# 3. ФОНОВЫЕ ЗАДАЧИ (ОТЧЁТЫ)
# ==========================================
async def hourly_report_task(bot: Bot):
    """Короткая сводка раз в час в группу CEO."""
    while True:
        await asyncio.sleep(3600)  # 1 час
        try:
            stats = await db.general_stats()
            text = (
                f"🟢 <b>Часовая сводка SYNTH</b>\n"
                f"👥 Всего пользователей: {stats['clients']}\n"
                f"📦 Активных проектов: {stats['active_projects']}\n"
                f"💰 Оборот: {stats['turnover']} ⭐\n"
                f"🏦 Счёт компании: {stats['company']} ⭐"
            )
            await bot.send_message(config.ceo_group_id, text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка часового отчёта: {e}")

async def three_day_report_task(bot: Bot):
    """Подробный отчёт файлом раз в 3 дня в канал."""
    while True:
        await asyncio.sleep(259200)  # 3 дня (72 часа)
        try:
            stats = await db.general_stats()
            referrers = await db.get_all_referrers() # Нужна будет эта функция в db.py, добавим её ниже
            
            report_lines = [
                "📊 ПОДРОБНЫЙ ОТЧЁТ SYNTH (3 дня)",
                "=" * 40,
                f"👥 Всего пользователей: {stats['clients']}",
                f"📦 Активных проектов: {stats['active_projects']}",
                f"✅ Завершённых: {stats['done_projects']}",
                f"💰 Общий оборот: {stats['turnover']} ⭐",
                f"🏦 Счёт компании: {stats['company']} ⭐",
                "=" * 40,
                "📈 СТАТИСТИКА ПИАРЩИКОВ/РЕФЕРЕРОВ:",
            ]
            
            # Если функция get_all_referrers ещё не добавлена, этот блок можно упростить
            # Для надёжности сейчас сделаем генерацию текстового файла из general_stats
            
            file_content = "\n".join(report_lines)
            file_bytes = file_content.encode("utf-8")
            
            await bot.send_document(
                chat_id=config.ping_chat_id,
                document=BufferedInputFile(file_bytes, filename="synth_report_3days.txt"),
                caption="📦 Автоматический отчёт SYNTH за последние 3 дня"
            )
        except Exception as e:
            logging.error(f"Ошибка отчёта за 3 дня: {e}")

# ==========================================
# 4. ГЛАВНАЯ ФУНКЦИЯ
# ==========================================
async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    
    await db.init(config.db_path)

    proxy = os.getenv("PROXY_URL", "").strip()
    if proxy:
        session = AiohttpSession(proxy=proxy)
        logging.info("Using proxy: %s", proxy)
    else:
        _patch_dns()
        session = AiohttpSession()
        logging.info("PROXY_URL не задан — использую прямой IP")

    bot = Bot(
        config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(client.router)
    dp.include_router(dev.router)
    dp.include_router(partner.router)
    dp.include_router(support.router)
    dp.include_router(projects.router)
    dp.include_router(admin.router)

    await bot.delete_webhook(drop_pending_updates=True)
    
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="❓ Справка по командам"),
        BotCommand(command="cancel", description="❌ Отменить действие"),
        BotCommand(command="backup_db", description="💾 Бэкап базы данных"),
    ]
    await bot.set_my_commands(commands)
    logging.info("✅ Меню команд обновлено!")

    # Запуск Flask
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("🌐 Flask health check server started")
    
    # Запуск фоновых задач
    asyncio.create_task(hourly_report_task(bot))
    asyncio.create_task(three_day_report_task(bot))
    
    logging.info("🚀 SYNTH Bot started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
