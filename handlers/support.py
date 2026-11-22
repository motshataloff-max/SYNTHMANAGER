import logging
import re
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import SupportForm
from keyboards import client_main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    await message.answer(
        "🆘 <b>Служба поддержки SYNTH</b>\n\n"
        "Опишите вашу проблему или вопрос кратко. Наш менеджер ответит вам.",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Обращение отменено.", reply_markup=client_main_menu())
    
    if not message.text:
        return await message.answer("⚠️ Пожалуйста, отправьте текстовое сообщение.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    
    # Получаем или создаем пользователя
    user = await db.get_user(user_id)
    if not user:
        user = await db.get_or_create_user(message.from_user)
    
    # Создаем тикет в БД
    ticket = await db.create_ticket(
        user_id=user['telegram_id'],
        channel='tg',
        type='support',
        title='Обращение в поддержку',
        description=message.text
    )
    
    ticket_number = ticket['ticket_number']
    
    # ✅ ТОТ САМЫЙ ТЕКСТ, КОТОРЫЙ ТЫ ПРОСИЛ
    response_text = (
        f"✅ Ваша заявка успешно создана!\n\n"
        f"📋 Номер заявки: {ticket['id']}\n"
        f"🎫 Ваш тикет: <code>{ticket_number}</code>\n\n"
        f"Сохраните его. По этому тикету вы всегда можете посмотреть, "
        f"на какой стадии находится ваше обращение, просто отправив его номер боту.\n\n"
        f"Менеджер скоро свяжется с вами!"
    )
    
    await message.answer(response_text, parse_mode="HTML", reply_markup=client_main_menu())
    await state.clear()
    
    # Уведомление в группу поддержки
    user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Клиент'}</a>"
    header = (
        f"🆘 <b>Новый тикет: {ticket_number}</b>\n"
        f"👤 <b>Клиент:</b> {user_link} (<code>{user_id}</code>)\n"
        f"💬 <b>Сообщение:</b>\n{message.text}"
    )
    
    try:
        await bot.send_message(config.support_group_id, header, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка отправки в группу поддержки: {e}")

# Умный перехват: если пользователь просто прислал номер тикета (например, SYNTH-2026-0001)
@router.message(F.text.regexp(r'(?i)^SYNTH-\d{4}-\d{4}$'))
async def auto_check_status(message: Message):
    ticket_number = message.text.upper()
    ticket = await db.get_ticket(ticket_number)
    
    if not ticket:
        return await message.answer(f"❌ Тикет <code>{ticket_number}</code> не найден.", parse_mode="HTML")
    
    # Проверка прав (клиент видит только свои, админ видит все)
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
