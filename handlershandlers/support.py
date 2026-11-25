import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
from keyboards import client_main_menu, admin_main_menu
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "📂 Мои заявки")
async def my_tickets(message: Message, state: FSMContext):
    await state.clear()
    tickets = await db.get_user_tickets(message.from_user.id)
    if not tickets:
        await message.answer("📭 У вас нет заявок.", reply_markup=client_main_menu())
        return
    lines = ["<b>📂 Ваши заявки:</b>"]
    for t in tickets:
        status_emoji = "🆕" if t['status'] == 'new' else "🔄" if t['status'] == 'in_progress' else "✅"
        lines.append(f"{status_emoji} <b>{t['ticket_number']}</b> — {t['title']}\n   Статус: {t['status']}")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=client_main_menu())

@router.message(F.text == "🎫 Все заявки")
async def all_tickets(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id:
        return
    await state.clear()
    tickets = await db.get_all_active_tickets()
    if not tickets:
        await message.answer("📭 Активных заявок нет.", reply_markup=admin_main_menu())
        return
    lines = ["<b>🎫 Все активные заявки:</b>"]
    for t in tickets[:10]:
        lines.append(f"• <b>{t['ticket_number']}</b> — {t['title']}\n  Статус: {t['status']} | Канал: {t['channel']}")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_main_menu())
