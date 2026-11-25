import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import db
from keyboards import client_main_menu, admin_main_menu
from config import config

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# КЛИЕНТ: МОИ ЗАЯВКИ
# ==========================================
@router.message(F.text == "📂 Мои заявки")
async def my_tickets(message: Message, state: FSMContext):
    await state.clear()
    tickets = await db.get_user_tickets(message.from_user.id)
    if not tickets:
        await message.answer("📭 У вас нет заявок.", reply_markup=client_main_menu())
        return
    
    lines = ["<b>📂 Ваши заявки:</b>\n"]
    for t in tickets:
        # Определяем эмодзи и текст статуса
        if t['status'] == 'new':
            status_text = "🆕 В разработке"
        elif t['status'] == 'in_progress':
            status_text = "🔄 В работе"
        elif t['status'] == 'closed':
            status_text = "✅ Завершено"
        else:
            status_text = f"❓ {t['status']}"
        
        lines.append(f"• <b>{t['ticket_number']}</b> — {t['title']}\n  Статус: {status_text}")
    
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=client_main_menu())

# ==========================================
# CEO: ВСЕ ЗАЯВКИ С КНОПКАМИ УПРАВЛЕНИЯ
# ==========================================
@router.message(F.text == "🎫 Все заявки")
async def all_tickets(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id:
        return
    await state.clear()
    tickets = await db.get_all_active_tickets()
    if not tickets:
        await message.answer("📭 Активных заявок нет.", reply_markup=admin_main_menu())
        return
    
    lines = ["<b>🎫 Все активные заявки:</b>\n"]
    for t in tickets[:10]:
        # Определяем эмодзи и текст статуса
        if t['status'] == 'new':
            status_text = "🆕 В разработке"
        elif t['status'] == 'in_progress':
            status_text = "🔄 В работе"
        elif t['status'] == 'closed':
            status_text = "✅ Завершено"
        else:
            status_text = f"❓ {t['status']}"
        
        lines.append(f"• <b>{t['ticket_number']}</b> — {t['title']}\n  Статус: {status_text} | Канал: {t['channel']}")
        
        # Добавляем кнопки управления под каждой заявкой
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 В работу", callback_data=f"status_inprogress_{t['ticket_number']}"),
                InlineKeyboardButton(text="✅ Завершить", callback_data=f"status_closed_{t['ticket_number']}")
            ]
        ])
        lines.append("")  # Пустая строка для разделения
    
    # Отправляем список с кнопками (кнопки будут только под последним сообщением, но это ок для MVP)
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_main_menu())
    
    # Отправляем отдельное сообщение с кнопками для первой заявки (для демонстрации)
    if tickets:
        first_ticket = tickets[0]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 В работу", callback_data=f"status_inprogress_{first_ticket['ticket_number']}"),
                InlineKeyboardButton(text="✅ Завершить", callback_data=f"status_closed_{first_ticket['ticket_number']}")
            ]
        ])
        await message.answer(
            f"<b>Управление заявкой {first_ticket['ticket_number']}:</b>",
            parse_mode="HTML",
            reply_markup=kb
        )

# ==========================================
# CEO: ОБРАБОТКА КНОПОК СМЕНЫ СТАТУСА
# ==========================================
@router.callback_query(F.data.startswith("status_inprogress_"))
async def set_in_progress(callback: CallbackQuery):
    if callback.from_user.id != config.owner_id:
        return await callback.answer("⛔ Только для CEO", show_alert=True)
    
    ticket_number = callback.data.replace("status_inprogress_", "")
    await db.update_ticket_status(ticket_number, "in_progress", callback.from_user.id)
    await callback.answer(f"✅ Заявка {ticket_number} переведена в работу", show_alert=True)
    await callback.message.edit_text(f"✅ <b>Заявка {ticket_number}</b> переведена в статус 'В работе'.", parse_mode="HTML")

@router.callback_query(F.data.startswith("status_closed_"))
async def set_closed(callback: CallbackQuery):
    if callback.from_user.id != config.owner_id:
        return await callback.answer("⛔ Только для CEO", show_alert=True)
    
    ticket_number = callback.data.replace("status_closed_", "")
    await db.update_ticket_status(ticket_number, "closed", callback.from_user.id)
    await callback.answer(f"✅ Заявка {ticket_number} завершена", show_alert=True)
    await callback.message.edit_text(f"✅ <b>Заявка {ticket_number}</b> завершена.", parse_mode="HTML")
