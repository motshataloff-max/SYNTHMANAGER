import re
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
from config import config
from keyboards import client_main_menu

router = Router()

# ==========================================
# КНОПКА: 📂 Мои заявки
# ==========================================
@router.message(F.text == "📂 Мои заявки")
async def menu_my_tickets(message: Message):
    tg_id = message.from_user.id
    user = await db.get_user(tg_id)
    if not user:
        return await message.answer("⚠️ Вы ещё не зарегистрированы в системе. Нажмите /start", reply_markup=client_main_menu())
    
    tickets = await db.get_user_tickets(tg_id)
    
    if not tickets:
        return await message.answer("📭 У вас пока нет активных заявок.", reply_markup=client_main_menu())
    
    status_emoji = {'new': '🆕', 'in_progress': '🔨', 'done': '✅', 'closed': '🔒'}
    
    lines = ["📂 <b>Ваши заявки:</b>", ""]
    for t in tickets[:10]:
        emoji = status_emoji.get(t['status'], '⚪')
        lines.append(f"{emoji} <code>{t['ticket_number']}</code> — {t.get('title') or 'Без названия'}")
    
    if len(tickets) > 10:
        lines.append(f"\n<i>Показаны последние 10 из {len(tickets)}</i>")
    
    lines.append("\n💡 <i>Чтобы проверить статус, просто отправьте номер тикета боту или нажмите кнопку '🔍 Проверить статус заявки'</i>")
    
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=client_main_menu())

# ==========================================
# КНОПКА: 🔍 Проверить статус заявки
# ==========================================
@router.message(F.text == "🔍 Проверить статус заявки")
async def menu_ask_status(message: Message):
    await message.answer(
        "📋 <b>Введите трек-номер вашей заявки.</b>\n\n"
        "Пример: <code>SYNTH-2026-0001</code>\n"
        "(Номер вам выдавал бот при создании заявки)",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

# ==========================================
# КОМАНДА: /status (дублирует умный перехват для надежности)
# ==========================================
@router.message(Command("status"))
async def cmd_status(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer(
            "⚠️ Укажите трек-номер.\n\nПример: <code>/status SYNTH-2026-0001</code>",
            parse_mode="HTML"
        )
    
    ticket_number = parts[1].upper()
    ticket = await db.get_ticket(ticket_number)
    
    if not ticket:
        return await message.answer(f"❌ Тикет <code>{ticket_number}</code> не найден.", parse_mode="HTML")
    
    if message.from_user.id != config.owner_id:
        user = await db.get_user(ticket['user_id'])
        if not user or message.from_user.id != user.get('telegram_id'):
            return await message.answer("⚠️ Этот тикет не принадлежит вам.")
    
    status_emoji = {'new': '🆕 Новый', 'in_progress': '🔨 В работе', 'done': '✅ Готов', 'closed': '🔒 Закрыт'}
    status_text = status_emoji.get(ticket['status'], ticket['status'])
    
    text = (
        f"📊 <b>Статус тикета:</b> <code>{ticket['ticket_number']}</code>\n"
        f"{'─' * 30}\n"
        f"🔨 <b>Этап:</b> {status_text}\n"
    )
    if ticket.get('title'): text += f"📝 <b>Тема:</b> {ticket['title']}\n"
    if ticket.get('assigned_team'): text += f"👥 <b>Команда:</b> {ticket['assigned_team']}\n"
    if ticket.get('budget'): text += f"💰 <b>Бюджет:</b> {ticket['budget']} ₽\n"
    text += f"📅 <b>Создан:</b> {ticket['created_at'][:16]}"
    
    await message.answer(text, parse_mode="HTML")
