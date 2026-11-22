"""
SYNTH Platform v2.0 - Служба поддержки
=======================================
Чистая коммуникация: создание тикета и возможность ответить клиенту через Reply в группе.
"""
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

# ==========================================
# 1. ЗАПУСК ПОДДЕРЖКИ (ДЛЯ КЛИЕНТА)
# ==========================================
@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext):
    logger.info(f"[SUPPORT] User {message.from_user.id} opened support")
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    await message.answer(
        "🆘 <b>Служба поддержки SYNTH</b>\n\n"
        "Опишите вашу проблему или вопрос. Наш менеджер ответит вам в этом чате.\n\n"
        "<i>Для отмены введите: Отмена</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

# ==========================================
# 2. СОЗДАНИЕ ТИКЕТА И УВЕДОМЛЕНИЕ ГРУППЫ
# ==========================================
@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    logger.info(f"[SUPPORT] User {message.from_user.id} sent support message")
    
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Обращение отменено.", reply_markup=client_main_menu())
    
    if not message.text and not message.photo:
        return await message.answer("⚠️ Пожалуйста, отправьте текстовое сообщение или фото.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Ваш аккаунт заблокирован.", reply_markup=client_main_menu())
    
    user = await db.get_user(user_id)
    if not user:
        user = await db.get_or_create_user(message.from_user)
    
    try:
        ticket = await db.create_ticket(
            user_id=user['telegram_id'],
            channel='tg',
            type='support',
            title='Обращение в поддержку',
            description=message.text or "[Медиа вложение]"
        )
        ticket_number = ticket['ticket_number']
        logger.info(f"[SUPPORT] Ticket {ticket_number} created for user {user_id}")
    except Exception as db_err:
        logger.error(f"[SUPPORT] DB ERROR: {db_err}", exc_info=True)
        return await message.answer("❌ Системная ошибка при создании тикета.", reply_markup=client_main_menu())
    
    # Ответ клиенту
    response_text = (
        f"✅ <b>Ваше обращение принято!</b>\n\n"
        f"🎫 <b>Ваш тикет:</b> <code>{ticket_number}</code>\n\n"
        f"Менеджер скоро ответит вам в этом чате."
    )
    await message.answer(response_text, parse_mode="HTML", reply_markup=client_main_menu())
    await state.clear()
    
    # 🔥 УВЕДОМЛЕНИЕ В ГРУППУ ПОДДЕРЖКИ (БЕЗ ЛИШНИХ КНОПОК, ТОЛЬКО ИНСТРУКЦИЯ)
    user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Клиент'}</a>"
    header = (
        f"🆘 <b>Новый тикет: {ticket_number}</b>\n"
        f"{'─' * 35}\n"
        f"👤 <b>Клиент:</b> {user_link} (<code>{user_id}</code>)\n"
        f"💬 <b>Сообщение:</b>\n{message.text or '[Медиа вложение]'}\n\n"
        f"💡 <i>Чтобы ответить клиенту, просто сделай <b>Reply (Ответить)</b> на это сообщение бота.</i>"
    )
    
    target_group = config.support_group_id
    if not target_group or target_group == 0:
        logger.warning("[SUPPORT] support_group_id не настроен.")
        return

    try:
        await bot.send_message(target_group, header, parse_mode="HTML")
        logger.info(f"[SUPPORT] ✅ SUCCESS: Notification sent to group {target_group}")
    except Exception as e:
        logger.error(f"[SUPPORT] ❌ FAILED to send to group {target_group}. Error: {e}", exc_info=True)

# ==========================================
# 3. ОТВЕТ МЕНЕДЖЕРА КЛИЕНТУ ЧЕРЕЗ REPLY (НОВАЯ ФУНКЦИЯ)
# ==========================================
@router.message(F.chat.id == int(config.support_group_id) if config.support_group_id else 0, F.reply_to_message)
async def support_reply_to_client(message: Message, bot: Bot):
    """Обрабатывает ответ менеджера на сообщение бота в группе поддержки"""
    replied_msg = message.reply_to_message
    
    # Проверяем, что это ответ на сообщение бота
    if not replied_msg or not replied_msg.from_user.is_bot:
        return
    
    # Ищем ID клиента в тексте сообщения бота: (<code>123456789</code>)
    match = re.search(r'\(<code>(\d+)</code>\)', replied_msg.text or "")
    if not match:
        return  # Не наше сообщение
    
    client_id = int(match.group(1))
    manager_name = message.from_user.full_name or message.from_user.username or "Менеджер"
    
    try:
        # Отправляем ответ клиенту
        await bot.send_message(
            client_id,
            f"💬 <b>Ответ поддержки (Менеджер: {manager_name}):</b>\n\n{message.text or '[Медиа]'}",
            parse_mode="HTML"
        )
        await message.answer(f"✅ Ответ успешно отправлен клиенту (<code>{client_id}</code>).", parse_mode="HTML")
        logger.info(f"[SUPPORT] Reply sent from manager {message.from_user.id} to client {client_id}")
    except Exception as e:
        logger.error(f"[SUPPORT] Failed to send reply to client {client_id}: {e}")
        await message.answer(f"❌ Не удалось отправить ответ. Возможно, клиент заблокировал бота.\nОшибка: {e}")
