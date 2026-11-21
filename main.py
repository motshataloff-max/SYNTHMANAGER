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

# Добавляем библиотеки для VK
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

import db
from config import config
from handlers import admin, client, common, dev, partner, projects, support

# ==========================================
# 1. FLASK ДЛЯ RAILWAY
# ==========================================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "SYNTH Bot v6.1 (TG + VK) is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# 2. VK БОТ (ФОНОВЫЙ ПОТОК)
# ==========================================
def run_vk_bot():
    vk_token = os.getenv("VK_TOKEN")
    vk_group_id_str = os.getenv("VK_GROUP_ID", "0")
    
    if not vk_token or vk_group_id_str == "0":
        print("⚠️ VK_TOKEN или VK_GROUP_ID не найдены. VK-бот не запущен.")
        return
    
    try:
        vk_group_id = int(vk_group_id_str)
        vk_session = vk_api.VkApi(token=vk_token)
        longpoll = VkLongPoll(vk_session)
        vk = vk_session.get_api()
        print("✅ VK Бот SYNTH запущен и слушает сообщения...")
        
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                text = event.text.lower().strip()
                
                if text in ["привет", "здравствуйте", "хай"]:
                    response = "Привет! 👋 Я помощник SYNTH. Опишите задачу, и я передам её менеджеру."
                elif text in ["цена", "стоимость", "бюджет"]:
                    response = "Стоимость от 500 ⭐. Опишите задачу, и мы оценим!"
                elif text in ["контакты", "телеграм", "тг", "tg"]:
                    response = "📱 Наш основной бот для заказов в Telegram: @Synthmanager_bot"
                else:
                    response = "Спасибо за сообщение! 📩\nМенеджер скоро ответит.\nДля быстрой связи пишите в Telegram: @Synthmanager_bot"
                
                try:
                    vk.messages.send(user_id=user_id, message=response, random_id=0)
                    print(f"✅ VK: Ответ отправлен пользователю {user_id}")
                except Exception as e:
                    print(f"❌ VK Ошибка отправки: {e}")
    except Exception as e:
        print(f"❌ Ошибка запуска VK-бота: {e}")

# ==========================================
# 3. ОБХОД БЛОКИРОВОК TELEGRAM
# ==========================================
def _patch_dns() -> None:
    _orig = socket.getaddrinfo
    def _patched(host, port, family=0, type=0, proto=0, flags=0):
        if host == "api.telegram.org":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("149.154.167.220", port))]
        return _orig(host, port, family, type, proto, flags)
    socket.getaddrinfo = _patched

# ==========================================
# 4. ФОНОВЫЕ ЗАДАЧИ TELEGRAM
# ==========================================
async def hourly_report_task(bot: Bot):
    while True:
        await asyncio.sleep(3600)
        try:
            stats = await db.general_stats()
            text = f"🟢 <b>Часовая сводка SYNTH</b>\n🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')} UTC\n\n👥 Пользователей: <b>{stats['clients']}</b>\n📦 Активных: <b>{stats['active_projects']}</b>\n✅ Завершённых: <b>{stats['done_projects']}</b>\n💰 Оборот: <b>{stats['turnover']} ⭐</b>"
            await bot.send_message(config.ceo_group_id, text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка отчёта: {e}")

# ==========================================
# 5. ГЛАВНАЯ ФУНКЦИЯ
# ==========================================
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

    # Запускаем Flask
    Thread(target=run_flask, daemon=True).start()
    logging.info("🌐 Flask started")
    
    # 🔥 ЗАПУСКАЕМ VK БОТА В ОТДЕЛЬНОМ ПОТОКЕ
    Thread(target=run_vk_bot, daemon=True).start()
    
    # Запускаем задачи Telegram
    asyncio.create_task(hourly_report_task(bot))
    
    logging.info("🚀 SYNTH Bot v6.1 (TG + VK) started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
