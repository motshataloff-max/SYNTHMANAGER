import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
import db
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/ban &lt;id&gt; [причина]</code>", parse_mode="HTML")
    user_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else "Без причины"
    if user_id == config.owner_id:
        return await message.answer("⚠️ Нельзя забанить CEO.")
    await db.ban_user(user_id, reason)
    await message.answer(f"🚫 <code>{user_id}</code> забанен.\n📝 Причина: {reason}", parse_mode="HTML")

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/unban &lt;id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.unban_user(user_id)
    await message.answer(f"✅ <code>{user_id}</code> разбанен.", parse_mode="HTML")

@router.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != config.owner_id:
        return
    s = await db.general_stats()
    text = (
        f"<b>📊 Статистика SYNTH</b>\n"
        f"──────────────────────\n"
        f"👥 Клиентов: <b>{s['clients']}</b>\n"
        f"🎫 Активных тикетов: <b>{s['active_tickets']}</b>\n"
        f"🔒 Закрытых тикетов: <b>{s['closed_tickets']}</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    if message.from_user.id != config.owner_id:
        return
    try:
        await message.answer_document(FSInputFile(config.db_path, filename="backup.db"), caption="💾 Бэкап")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
