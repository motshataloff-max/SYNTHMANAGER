import asyncio
import logging
import os
import socket
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, FSInputFile

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
            stats = await db.get_stats()
            text = (
                f"🟢 <b>Часовая сводка SYNTH</b>\n"
                f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')} UTC\n\n"
                f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
                f"📋 Активных тикетов: <b>{stats['active_tickets']}</b>\n"
                f"✅ Закрытых: <b>{stats['closed_tickets']}</b>\n"
                f"💰 Общий бюджет: <b>{stats['total_budget']} ₽</b>"
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
            stats = await db.get_stats()
            lines = [
                f"📊 ЕЖЕДНЕВНЫЙ ОТЧЁТ SYNTH",
                f"📅 {datetime.now().strftime('%d.%m.%Y')}",
                "=" * 40,
                f"👥 Всего пользователей: {stats['total_users']}",
                f"📋 Активных тикетов: {stats['active_tickets']}",
                f"✅ Закрытых тикетов: {stats['closed_tickets']}",
                f"💰 Общий оборот: {stats['total_budget']} ₽",
            ]
            file_bytes = "\n".join(lines).encode("utf-8")
            from aiogram.types import BufferedInputFile
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
                await bot.send_document(
                    chat_id=config.ping_chat_id,
                    document=doc2,
                    caption=f"💾 Бэкап БД {date_str}"
                )
            logging.info(f"✅ Бэкап БД отправлен ({filename})")
        except Exception as e:
            logging.error(f"❌ Ошибка бэкапа БД: {e}")

def run_vk_bot_sync(tg_bot: Bot):
    if not config.vk_token or config.vk_group_id == 0:
        logging.info("⚠️ VK_TOKEN или VK_GROUP_ID не найдены. VK-бот не запущен.")
        return
    
    try:
        vk_session = vk_api.VkApi(token=config.vk_token)
        longpoll = VkLongPoll(vk_session)
        vk = vk_session.get_api()
        logging.info("✅ VK Бот SYNTH запущен и слушает сообщения...")
        
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                vk_id = event.user_id
                text = event.text.lower().strip()
                
                try:
                    user_info = vk.users.get(user_ids=vk_id)[0]
                    name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip() or "VK Пользователь"
                except:
                    name = "VK Пользователь"

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                user = loop.run_until_complete(db.get_or_create_user(vk_id=vk_id, username=f"vk_{vk_id}", full_name=name))
                user_id = user['id']

                if text in ["привет", "здравствуйте", "хай", "поддержка", "помощь"]:
                    ticket = loop.run_until_complete(db.create_ticket(
                        user_id=user_id, channel='vk', type='support', 
                        title='Обращение в поддержку', description=event.text
                    ))
                    response = f"Привет! 👋 Ваш тикет: {ticket['ticket_number']}. Менеджер скоро ответит."
                    
                    header = f"🆘 <b>Новый тикет VK: {ticket['ticket_number']}</b>\n👤 <b>Клиент:</b> {name} (VK: <code>{vk_id}</code>)\n💬 <b>Сообщение:</b>\n{event.text}"
                    loop.run_until_complete(tg_bot.send_message(config.support_group_id, header, parse_mode="HTML"))
                
                elif text in ["цена", "стоимость", "бюджет"]:
                    response = "Стоимость от 500 ₽. Опишите задачу, и мы оценим!"
                elif text in ["контакты", "телеграм", "тг", "tg"]:
                    response = "📱 Наш основной бот: @Synthmanager_bot"
                else:
                    response = "Спасибо за сообщение! 📩\nДля заявки напишите 'поддержка' или перейдите в Telegram: @Synthmanager_bot"

                try:
                    vk.messages.send(user_id=vk_id, message=response, random_id=0)
                    logging.info(f"✅ VK: Ответ отправлен {vk_id}")
                except Exception as e:
                    logging.error(f"❌ VK Ошибка отправки: {e}")
                loop.close()
                    
    except Exception as e:
        logging.error(f"❌ Ошибка VK-бота: {e}")

# ==========================================
# 4. ГЛАВНАЯ ФУНКЦИЯ
# ==========================================
async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    await db.connect()
    logging.info("✅ База данных инициализирована")

    proxy = os.getenv("PROXY_URL", "").strip()
    session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
    if not proxy: 
        _patch_dns()

    bot = Bot(config.bot_token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем только существующие роутеры
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
        BotCommand(command="backup_db", description="💾 Ручной бэкап"),
    ])
    logging.info("✅ Меню команд обновлено")

    Thread(target=run_flask, daemon=True).start()
    logging.info("🌐 Flask started")
    
    Thread(target=run_vk_bot_sync, args=(bot,), daemon=True).start()
    
    asyncio.create_task(hourly_report_task(bot))
    asyncio.create_task(daily_report_task(bot))
    asyncio.create_task(daily_backup_task(bot))
    
    logging.info("🚀 SYNTH Platform v2.0 started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
