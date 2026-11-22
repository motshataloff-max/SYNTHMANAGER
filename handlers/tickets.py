from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
from config import config

router = Router()

# ==========================================
# /status <номер> — для клиентов
# ==========================================
@router.message(Command("status"))
async def cmd_status(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer(
            "⚠️ Укажите трек-номер.\n\nПример: <code>/status SYNTH-2026-0042</code>",
            parse_mode="HTML"
        )
    
    ticket_number = parts[1].upper()
    ticket = await db.get_ticket(ticket_number)
    
    if not ticket:
        return await message.answer(f"❌ Тикет <code>{ticket_number}</code> не найден.", parse_mode="HTML")
    
    # Получаем пользователя
    user = await db.get_user_by_id(ticket['user_id'])
    
    # Проверяем: клиент видит только свои тикеты (CEO видит все)
    if message.from_user.id != config.owner_id:
        # Находим telegram_id или vk_id пользователя
        client_tg_id = user.get('telegram_id') if user else None
        client_vk_id = user.get('vk_id') if user else None
        
        if message.from_user.id != client_tg_id:
            return await message.answer("⚠️ Этот тикет не принадлежит вам.")
    
    # Формируем красивую карточку
    status_emoji = {
        'new': '🆕 Новый',
        'in_progress': '🔨 В работе',
        'done': '✅ Готов',
        'closed': '🔒 Закрыт'
    }
    status_text = status_emoji.get(ticket['status'], ticket['status'])
    
    text = (
        f"📊 <b>Статус тикета:</b> <code>{ticket['ticket_number']}</code>\n"
        f"{'─' * 30}\n"
        f"📋 <b>Тип:</b> {ticket['type']}\n"
        f"🔨 <b>Этап:</b> {status_text}\n"
    )
    
    if ticket['title']:
        text += f"📝 <b>Заголовок:</b> {ticket['title']}\n"
    if ticket['assigned_team']:
        text += f"👥 <b>Команда:</b> {ticket['assigned_team']}\n"
    if ticket['budget']:
        text += f"💰 <b>Бюджет:</b> {ticket['budget']} ₽\n"
    
    text += f"📅 <b>Создан:</b> {ticket['created_at'][:16]}"
    
    await message.answer(text, parse_mode="HTML")

# ==========================================
# /my_tickets — список своих тикетов
# ==========================================
@router.message(Command("my_tickets"))
async def cmd_my_tickets(message: Message):
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        return await message.answer("⚠️ Вы ещё не зарегистрированы в системе.")
    
    tickets = await db.get_user_tickets(user['id'])
    
    if not tickets:
        return await message.answer("📭 У вас пока нет тикетов.")
    
    status_emoji = {
        'new': '🆕',
        'in_progress': '🔨',
        'done': '✅',
        'closed': '🔒'
    }
    
    lines = ["📂 <b>Ваши тикеты:</b>", ""]
    for t in tickets[:10]:  # Показываем последние 10
        emoji = status_emoji.get(t['status'], '⚪')
        lines.append(f"{emoji} <code>{t['ticket_number']}</code> — {t['title'] or 'Без названия'}")
    
    if len(tickets) > 10:
        lines.append(f"\n<i>Показаны последние 10 из {len(tickets)}</i>")
    
    await message.answer("\n".join(lines), parse_mode="HTML")

# ==========================================
# /ticket <номер> — для менеджеров/CEO (с историей)
# ==========================================
@router.message(Command("ticket"))
async def cmd_ticket_admin(message: Message):
    if message.from_user.id != config.owner_id and not await db.has_role(message.from_user.id, 'manager'):
        return await message.answer("⚠️ Эта команда доступна только менеджерам и CEO.")
    
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("⚠️ Укажите трек-номер.\n\nПример: <code>/ticket SYNTH-2026-0042</code>", parse_mode="HTML")
    
    ticket_number = parts[1].upper()
    ticket = await db.get_ticket(ticket_number)
    
    if not ticket:
        return await message.answer(f"❌ Тикет <code>{ticket_number}</code> не найден.", parse_mode="HTML")
    
    user = await db.get_user_by_id(ticket['user_id'])
    
    status_emoji = {
        'new': '🆕 Новый',
        'in_progress': '🔨 В работе',
        'done': '✅ Готов',
        'closed': '🔒 Закрыт'
    }
    status_text = status_emoji.get(ticket['status'], ticket['status'])
    
    text = (
        f"🗂 <b>Карточка тикета:</b> <code>{ticket['ticket_number']}</code>\n"
        f"{'═' * 30}\n"
        f"👤 <b>Клиент:</b> {user['full_name'] if user else 'Неизвестно'}\n"
        f"📱 <b>Канал:</b> {ticket['channel'].upper()}\n"
        f"📋 <b>Тип:</b> {ticket['type']}\n"
        f"🔨 <b>Статус:</b> {status_text}\n"
    )
    
    if ticket['title']:
        text += f"📝 <b>Заголовок:</b> {ticket['title']}\n"
    if ticket['description']:
        text += f"📄 <b>Описание:</b> {ticket['description'][:200]}\n"
    if ticket['budget']:
        text += f"💰 <b>Бюджет:</b> {ticket['budget']} ₽\n"
    if ticket['assigned_team']:
        text += f"👥 <b>Команда:</b> {ticket['assigned_team']}\n"
    
    text += f"\n📅 <b>Создан:</b> {ticket['created_at'][:16]}"
    
    # Получаем историю изменений
    await db.connect()
    cursor = await db.conn.execute(
        "SELECT * FROM ticket_history WHERE ticket_number = ? ORDER BY created_at DESC LIMIT 5",
        (ticket_number,)
    )
    history = await cursor.fetchall()
    
    if history:
        text += "\n\n📜 <b>Последние действия:</b>"
        for h in history:
            text += f"\n• {h['created_at'][:16]}: {h['action']}"
            if h['old_value'] and h['new_value']:
                text += f" ({h['old_value']} → {h['new_value']})"
    
    # Кнопки управления
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔨 В работу", callback_data=f"ticket_status_{ticket_number}_in_progress"),
            InlineKeyboardButton(text="✅ Готов", callback_data=f"ticket_status_{ticket_number}_done")
        ],
        [
            InlineKeyboardButton(text="🔒 Закрыть", callback_data=f"ticket_status_{ticket_number}_closed")
        ]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# ==========================================
# /tickets — список активных тикетов
# ==========================================
@router.message(Command("tickets"))
async def cmd_tickets_list(message: Message):
    if message.from_user.id != config.owner_id and not await db.has_role(message.from_user.id, 'manager'):
        return await message.answer("⚠️ Эта команда доступна только менеджерам и CEO.")
    
    await db.connect()
    cursor = await db.conn.execute(
        "SELECT * FROM tickets WHERE status != 'closed' ORDER BY created_at DESC LIMIT 20"
    )
    tickets = await cursor.fetchall()
    
    if not tickets:
        return await message.answer("📭 Активных тикетов нет.")
    
    status_emoji = {
        'new': '🆕',
        'in_progress': '🔨',
        'done': '✅'
    }
    
    lines = ["📋 <b>Активные тикеты:</b>", ""]
    for t in tickets:
        emoji = status_emoji.get(t['status'], '⚪')
        lines.append(f"{emoji} <code>{t['ticket_number']}</code> | {t['channel'].upper()} | {t['title'] or 'Без названия'}")
    
    await message.answer("\n".join(lines), parse_mode="HTML")

# ==========================================
# Обработка кнопок изменения статуса
# ==========================================
@router.callback_query(F.data.startswith("ticket_status_"))
async def callback_ticket_status(callback):
    if callback.from_user.id != config.owner_id and not await db.has_role(callback.from_user.id, 'manager'):
        return await callback.answer("⚠️ Нет прав", show_alert=True)
    
    parts = callback.data.split("_")
    # ticket_status_<номер>_<статус>
    ticket_number = "_".join(parts[2:-1])  # Номер может содержать "_"
    new_status = parts[-1]
    
    await db.update_ticket_status(ticket_number, new_status, callback.from_user.id)
    
    status_emoji = {
        'new': '🆕',
        'in_progress': '🔨',
        'done': '✅',
        'closed': '🔒'
    }
    
    await callback.message.edit_text(
        f"✅ Статус тикета <code>{ticket_number}</code> изменён на {status_emoji.get(new_status, new_status)}",
        parse_mode="HTML"
    )
    await callback.answer()
