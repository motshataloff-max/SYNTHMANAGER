import asyncio
import logging
import os
import socket
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
# 2. ОБХОД БЛОКИРОВОК TELEGRAM
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
        await asyncio.sleep(3600)
        try:
            stats = await db.general_stats()
            text = (
                f"🟢 <b>Часовая сводка SYNTH</b>\n"
                f"🕒 {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC\n\n"
                f"👥 Всего пользователей: <b>{stats['clients']}</b>\n"
                f"📦 Активных проектов: <b>{stats['active_projects']}</b>\n"
                f"✅ Завершённых: <b>{stats['done_projects']}</b>\n"
                f"💰 Оборот: <b>{stats['turnover']} ⭐</b>\n"
                f"🏦 Счёт компании: <b>{stats['company']} ⭐</b>"
            )
            await bot.send_message(config.ceo_group_id, text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка часового отчёта: {e}")


async def daily_report_task(bot: Bot):
    """Подробный отчёт файлом каждый день в 04:30 UTC в группу CEO."""
    while True:
        now = datetime.utcnow()
        target = time(4, 30)
        next_run = datetime.combine(now.date(), target)
        if now.time() >= target:
            next_run = datetime.combine(now.date() + timedelta(days=1), target)
        seconds_to_wait = (next_run - now).total_seconds()
        await asyncio.sleep(seconds_to_wait)
        
        try:
            stats = await db.general_stats()
            managers = await db.list_managers()
            devs = await db.list_active_by_role("dev")
            partners = await db.list_active_by_role("partner")
            pr_list = await db.list_active_by_role("pr")
            
            lines = [
                "=" * 50,
                "📊 ЕЖЕДНЕВНЫЙ ОТЧЁТ SYNTH",
                f"📅 {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC",
                "=" * 50,
                "",
                "📈 ОБЩАЯ СВОДКА:",
                f"👥 Всего пользователей: {stats['clients']}",
                f"📦 Активных проектов: {stats['active_projects']}",
                f"✅ Завершённых проектов: {stats['done_projects']}",
                f"💰 Общий оборот: {stats['turnover']} ⭐",
                f"🏦 Счёт компании: {stats['company']} ⭐",
                "",
                "👥 ПЕРСОНАЛ:",
                f"👨‍💼 Менеджеров: {len(managers)}",
                f"👨‍💻 Разработчиков: {len(devs)}",
                f"🤝 Партнёров: {len(partners)}",
                f"📣 Пиарщиков: {len(pr_list)}",
                "",
                "📋 ПОСЛЕДНИЕ 10 ПРОЕКТОВ:",
            ]
            
            recent_projects = await db.list_projects(limit=10)
            for p in recent_projects:
                lines.append(f"  #{p['id']} | {p['status']} | {p['budget']}⭐ | {p['title'][:40]}")
            
            file_content = "\n".join(lines)
            file_bytes = file_content.encode("utf-8")
            
            await bot.send_document(
                chat_id=config.ceo_group_id,
                document=BufferedInputFile(file_bytes, filename=f"synth_daily_{datetime.utcnow().strftime('%Y%m%d')}.txt"),
                caption="📦 Ежедневный отчёт SYNTH"
            )
        except Exception as e:
            logging.error(f"Ошибка ежедневного отчёта: {e}")


async def three_day_report_task(bot: Bot):
    """Расширенный отчёт файлом раз в 3 дня (72 часа) в канал."""
    while True:
        await asyncio.sleep(259200)
        try:
            stats = await db.general_stats()
            pr_list = await db.list_active_by_role("pr")
            
            lines = [
                "=" * 50,
                "📊 ПОДРОБНЫЙ ОТЧЁТ SYNTH (3 ДНЯ)",
                f"📅 {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC",
                "=" * 50,
                "",
                "📈 ОБЩАЯ СВОДКА:",
                f"👥 Всего пользователей: {stats['clients']}",
                f"📦 Активных проектов: {stats['active_projects']}",
                f"✅ Завершённых: {stats['done_projects']}",
                f"💰 Общий оборот: {stats['turnover']} ⭐",
                f"🏦 Счёт компании: {stats['company']} ⭐",
                "",
                "📣 СТАТИСТИКА ПИАРЩИКОВ:",
            ]
            
            for pr in pr_list:
                try:
                    s = await db.pr_stats(pr["telegram_id"])
                    lines.append(f"  👤 {pr['telegram_id']}: клиентов={s['clients']}, заказов={s['orders']}, оборот={s['total']}⭐")
                except Exception:
                    pass
            
            file_content = "\n".join(lines)
            file_bytes = file_content.encode("utf-8")
            
            await bot.send_document(
                chat_id=config.ping_chat_id,
                document=BufferedInputFile(file_bytes, filename=f"synth_3days_{datetime.utcnow().strftime('%Y%m%d')}.txt"),
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
        BotCommand(command="msg", description="💬 Написать клиенту"),
        BotCommand(command="assign", description="⚙️ Назначить команду"),
        BotCommand(command="complete", description="✅ Завершить проект"),
        BotCommand(command="status", description="📊 Изменить статус проекта"),
        BotCommand(command="backup_db", description="💾 Бэкап базы данных"),
        BotCommand(command="restart_bot", description="🔄 Перезапустить бота"),
    ]
    await bot.set_my_commands(commands)
    logging.info("✅ Меню команд обновлено!")

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("🌐 Flask health check server started")
    
    asyncio.create_task(hourly_report_task(bot))
    asyncio.create_task(daily_report_task(bot))
    asyncio.create_task(three_day_report_task(bot))
    
    logging.info("🚀 SYNTH Bot started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
