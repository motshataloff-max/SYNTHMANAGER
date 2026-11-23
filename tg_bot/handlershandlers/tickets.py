"""
SYNTH Platform v2.0 - Обработка тикетов и статусов
===================================================
Включает: просмотр своих заявок, проверку статуса по номеру, 
админскую панель заявок и управление статусами.
"""
import logging
import re
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
from config import config
from keyboards import client_main_menu, admin_main_menu

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# 1. КЛИЕНТ: Мои заявки
# ==========================================
@router.message(F.text == "📂 Мои заявки")
async def menu_my_tickets(message: Message, state: FSMContext):
    logger.info(f"[TICKETS] User {message.from_user.id} clicked 'Мои заявки'")
    await state.clear() # Сброс состояния на всякий случай
    
    tg_id = message.from_user.id
    user = await db.get_user(tg_id)
    if not user: 
        return await message.answer("⚠️ Нажмите /start для регистрации.", reply_markup=client_main_menu())
    
    tickets = await db.get_user_tickets(tg_id)
    logger.info(f"[TICKETS] Found {len(tickets)} tickets for user {tg_id}")
    
    if not tickets: 
        return await message.answer(
            "📭 У вас пока нет активных заявок.\n\n"
            "💡 Нажмите '🆘 Поддержка' или '🛒 Заказать разработку', чтобы создать первую.", 
            reply_markup=client_main_menu()
        )
    
    status_emoji = {'new': '🆕', 'in_progress': '🔨', 'done': '✅', 'closed': '🔒'}
    lines = ["📂 <b>Ваши заявки:</b>", ""]
    
    for t in tickets[:10]:
        emoji = status_emoji.get(t['status'], '⚪')
        title = t.get('title') or 'Без названия'
        lines.append(f"{emoji} <code>{t['ticket_number']}</code> — {title[:30]}")
    
    if len(tickets) > 10:
        lines.append(f"\n<i>Показаны последние 10 из {len(tickets)}</i>")
    
    lines.append("\n💡 <i>Чтобы проверить статус, просто отправьте номер тикета (например, SYNTH-2026-0001) в чат.</i>")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=client_main_menu())

# ==========================================
# 2. КЛИЕНТ: Проверка статуса (КНОПКА МЕНЮ)
# ==========================================
@router.message(F.text == "🔍 Проверить статус заявки")
async def menu_ask_status(message: Message, state: FSMContext):
    """Кнопка проверки статуса заявки — принудительно сбрасывает любое состояние"""
    logger.info(f"[TICKETS] User {message.from_user.id} clicked 'Проверить статус заявки'")
    
    # 🔥 КРИТИЧЕСКИЙ ФИКС: Сбрасываем любое зависшее FSM-состояние
    await state.clear()
    
    await message.answer(
        "📋 <b>Введите трек-номер вашей заявки.</b>\n\n"
        "Пример: <code>SYNTH-2026-0001</code>\n"
        "(Номер вам выдавал бот при создании заявки)\n\n"
        "💡 Или просто отправьте номер тикета в чат — бот автоматически покажет статус.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

# ==========================================
# 3. КЛИЕНТ: Умный перехват номера тикета (Regex)
# ==========================================
@router.message(F.text.regexp(r'(?i)^SYNTH-\d{4}-\d{4}$'))
async def auto_check_status(message: Message, state: FSMContext):
    """Автоматически распознает номер тикета и показывает статус"""
    ticket_number = message.text.upper()
    logger.info(f"[TICKETS] User {message.from_user.id} checking status for {ticket_number}")
    
    # Сбрасываем состояние, чтобы эта проверка сработала из любого места
    await state.clear()
    
    ticket = await db.get_ticket(ticket_number)
    if not ticket:
        return await message.answer(f"❌ Тикет <code>{ticket_number}</code> не найден в базе данных.", parse_mode="HTML")
    
    # Проверка прав: клиент видит только свои, CEO видит все
    if message.from_user.id != config.owner_id:
        user = await db.get_user(ticket['user_id'])
        if not user or message.from_user.id != user.get('telegram_id'):
            return await message.answer("⚠️ Этот тикет не принадлежит вам.")
    
    status_emoji = {'new': '🆕 Новый', 'in_progress': '🔨 В работе', 'done': '✅ Готов', 'closed': '🔒 Закрыт'}
    text = f"📊 <b>Статус тикета:</b> <code>{ticket['ticket_number']}</code>\n{'─' * 30}\n🔨 <b>Этап:</b> {status_emoji.get(ticket['status'], ticket['status'])}\n"
    if ticket.get('title'): text += f"📝 <b>Тема:</b> {ticket['title']}\n"
    if ticket.get('assigned_team'): text += f"👥 <b>Команда:</b> {ticket['assigned_team']}\n"
    if ticket.get('budget'): text += f"💰 <b>Бюджет:</b> {ticket['budget']} ₽\n"
    text += f"📅 <b>Создан:</b> {ticket['created_at'][:16]}"
    
    await message.answer(text, parse_mode="HTML", reply_markup=client_main_menu())

# ==========================================
# 4. КЛИЕНТ: Команда /status (резервный вариант)
# ==========================================
@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    await state.clear()
    parts = message.text.split()
    if len(parts) < 2: 
        return await message.answer("⚠️ Укажите трек-номер.\n\nПример: <code>/status SYNTH-2026-0001</code>", parse_mode="HTML")
    
    # Хакируем текст сообщения, чтобы сработал обработчик Regex выше
    message.text = parts[1].upper()
    await auto_check_status(message, state)

# ==========================================
# 5. АДМИН: Все заявки (Тикеты)
# ==========================================
@router.message(F.text == "📋 Все заявки (Тикеты)")
async def menu_all_tickets(message: Message):
    logger.info(f"[TICKETS] Admin {message.from_user.id} clicked 'Все заявки (Тикеты)'")
    
    if message.from_user.id != config.owner_id and not await db.has_active_role(message.from_user.id, 'manager'): 
        logger.warning(f"[TICKETS] Access denied for user {message.from_user.id}")
        return await message.answer("⚠️ Доступ только для менеджеров и CEO.")
    
    try:
        tickets = await db.get_all_active_tickets()
        logger.info(f"[TICKETS] DB returned {len(tickets)} active tickets")
        
        if not tickets:
            # Проверим, есть ли вообще хоть какие-то в базе
            async with db._conn() as conn:
                import aiosqlite
                conn.row_factory = aiosqlite.Row
                cur = await conn.execute("SELECT COUNT(*) FROM tickets")
                total = (await cur.fetchone())[0]
            
            if total == 0:
                return await message.answer(
                    "📭 <b>В системе пока нет ни одной заявки.</b>\n\n"
                    "💡 <i>Нажмите '🆘 Поддержка' или '🛒 Заказать разработку', чтобы создать тестовую заявку.</i>",
                    reply_markup=admin_main_menu()
                )
            else:
                return await message.answer(
                    f"📭 <b>Активных заявок нет</b> (все закрыты).\n"
                    f"📊 Всего заявок в базе: <b>{total}</b>",
                    reply_markup=admin_main_menu()
                )

        status_emoji = {'new': '🆕', 'in_progress': '🔨', 'done': '✅', 'closed': '🔒'}
        lines = ["📋 <b>Активные заявки:</b>", ""]
        for t in tickets:
            emoji = status_emoji.get(t['status'], '⚪')
            channel = t.get('channel', 'TG').upper()
            title = t.get('title') or 'Без названия'
            lines.append(f"{emoji} <code>{t['ticket_number']}</code> | {channel} | {title[:30]}")
        
        lines.append(f"\n<i>Всего показано: {len(tickets)} из 20</i>")
        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_main_menu())
        
    except Exception as e:
        logger.error(f"[TICKETS] CRITICAL ERROR in menu_all_tickets: {e}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при чтении базы данных:\n<code>{e}</code>", parse_mode="HTML")

# ==========================================
# 6. АДМИН: Карточка тикета по команде /ticket
# ==========================================
@router.message(Command("ticket"))
async def cmd_ticket_admin(message: Message):
    if message.from_user.id != config.owner_id and not await db.has_active_role(message.from_user.id, 'manager'): 
        return await message.answer("⚠️ Доступ только для менеджеров и CEO.")
    
    parts = message.text.split()
    if len(parts) < 2: 
        return await message.answer("⚠️ Укажите трек-номер.\n\nПример: <code>/ticket SYNTH-2026-0001</code>", parse_mode="HTML")
    
    ticket_number = parts[1].upper()
    ticket = await db.get_ticket(ticket_number)
    if not ticket: 
        return await message.answer(f"❌ Тикет <code>{ticket_number}</code> не найден.", parse_mode="HTML")
    
    user = await db.get_user(ticket['user_id'])
    status_emoji = {'new': '🆕 Новый', 'in_progress': '🔨 В работе', 'done': '✅ Готов', 'closed': '🔒 Закрыт'}
    
    text = f"🗂 <b>Карточка тикета:</b> <code>{ticket['ticket_number']}</code>\n{'═' * 30}\n👤 <b>Клиент:</b> {user.get('full_name') if user else 'Неизвестно'}\n📱 <b>Канал:</b> {ticket['channel'].upper()}\n🔨 <b>Статус:</b> {status_emoji.get(ticket['status'], ticket['status'])}\n"
    if ticket.get('title'): text += f"📝 <b>Заголовок:</b> {ticket['title']}\n"
    if ticket.get('description'): text += f"📄 <b>Описание:</b> {ticket['description'][:200]}\n"
    if ticket.get('budget'): text += f"💰 <b>Бюджет:</b> {ticket['budget']} ₽\n"
    if ticket.get('assigned_team'): text += f"👥 <b>Команда:</b> {ticket['assigned_team']}\n"
    text += f"\n📅 <b>Создан:</b> {ticket['created_at'][:16]}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔨 В работу", callback_data=f"ticket_status_{ticket_number}_in_progress"), 
         InlineKeyboardButton(text="✅ Готов", callback_data=f"ticket_status_{ticket_number}_done")],
        [InlineKeyboardButton(text="🔒 Закрыть", callback_data=f"ticket_status_{ticket_number}_closed")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# ==========================================
# 7. АДМИН: Обработка кнопок смены статуса
# ==========================================
@router.callback_query(F.data.startswith("ticket_status_"))
async def callback_ticket_status(callback):
    if callback.from_user.id != config.owner_id and not await db.has_active_role(callback.from_user.id, 'manager'): 
        return await callback.answer("⚠️ Нет прав", show_alert=True)
    
    parts = callback.data.split("_")
    ticket_number = "_".join(parts[2:-1])
    new_status = parts[-1]
    
    await db.update_ticket_status(ticket_number, new_status, callback.from_user.id)
    status_emoji = {'new': '🆕', 'in_progress': '🔨', 'done': '✅', 'closed': '🔒'}
    
    await callback.message.edit_text(
        f"✅ Статус тикета <code>{ticket_number}</code> изменён на {status_emoji.get(new_status, new_status)}", 
        parse_mode="HTML"
    )
    await callback.answer()
