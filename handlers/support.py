"""
SYNTH Platform v2.0 - Служба поддержки
=======================================
Чистая коммуникация: создание тикета и ответ менеджеру через Reply.
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
        "Опишите вашу проблему или вопрос. Менеджер ответит вам в этом чате.\n\n"
        "<i>Для отмены: Отмена</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

# ==========================================
# 2. СОЗДАНИЕ ТИКЕТА
# ==========================================
@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    logger.info(f"[SUPPORT] User {message.from_user.id} sent support message")
    
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Обращение отменено.", reply_markup=client_main_menu())
    
    if not message.text and not message.photo:
        return await message.answer("⚠️ Отправьте текст или фото.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Аккаунт заблокирован.", reply_markup=client_main_menu())
    
    user = await db.get_user(user_id)
    if not user:
        user = await db.get_or_create_user(message.from_user)
    
    try:
        ticket = await db.create_ticket(
            user_id=user['telegram_id'],
            channel='tg',
            type='support',
            title='Обращение в поддержку',
            description=message.text or "[Медиа]"
        )
        ticket_number = ticket['ticket_number']
        logger.info(f"[SUPPORT] Ticket {ticket_number} created")
    except Exception as e:
        logger.error(f"[SUPPORT] DB ERROR: {e}", exc_info=True)
        return await message.answer("❌ Ошибка создания тикета.", reply_markup=client_main_menu())
    
    await message.answer(
        f"✅ <b>Обращение принято!</b>\n\n🎫 <b>Тикет:</b> <code>{ticket_number}</code>\n\nМенеджер скоро ответит.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    await state.clear()
    
    # 🔥 УВЕДОМЛЕНИЕ В ГРУППУ
    user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Клиент'}</a>"
    header = (
        f"🆘 <b>Тикет: {ticket_number}</b>\n"
        f"👤 Клиент: {user_link} (<code>{user_id}</code>)\n"
        f"💬 {message.text or '[Медиа]'}\n\n"
        f"💡 <i>Ответь на это сообщение (Reply), чтобы отправить ответ клиенту.</i>"
    )
    
    target_group = config.support_group_id
    if not target_group or target_group == 0:
        logger.warning("[SUPPORT] support_group_id не настроен")
        return

    try:
        await bot.send_message(target_group, header, parse_mode="HTML")
        logger.info(f"[SUPPORT] ✅ Sent to group {target_group}")
    except Exception as e:
        logger.error(f"[SUPPORT] ❌ Failed: {e}", exc_info=True)

# ==========================================
# 3. ОТВЕТ МЕНЕДЖЕРА ЧЕРЕЗ REPLY (ИСПРАВЛЕНО)
# ==========================================
@router.message(F.reply_to_message)
async def support_reply_to_client(message: Message, bot: Bot):
    """Обрабатывает ответ менеджера на сообщение бота в группе поддержки"""
    logger.info(f"[SUPPORT] Reply detected in chat {message.chat.id} from user {message.from_user.id}")
    
    # Проверяем, что это именно группа поддержки
    if message.chat.id != int(config.support_group_id):
        logger.info(f"[SUPPORT] Not support group, ignoring")
        return
    
    replied_msg = message.reply_to_message
    if not replied_msg:
        logger.info("[SUPPORT] No replied message")
        return
    
    # 🔥 ИЩЕМ ID КЛИЕНТА В ТЕКСТЕ ОТВЕЧАЕМОГО СООБЩЕНИЯ
    # Формат: "Клиент: @username (<code>123456789</code>)"
    text = replied_msg.text or ""
    logger.info(f"[SUPPORT] Replied message text: {text[:100]}")
    
    # Ищем ID в скобках с тегом <code>
    match = re.search(r'\(<code>(\d+)</code>\)', text)
    if not match:
        logger.info("[SUPPORT] Client ID not found in replied message")
        await message.answer("⚠️ Это сообщение не содержит ID клиента. Ответь на сообщение бота о новом тикете.")
        return
    
    client_id = int(match.group(1))
    manager_name = message.from_user.full_name or message.from_user.username or "Менеджер"
    
    logger.info(f"[SUPPORT] Sending reply from {manager_name} to client {client_id}")
    
    try:
        # Отправляем ответ клиенту
        reply_text = message.text or message.caption or "[Медиа]"
        await bot.send_message(
            client_id,
            f"💬 <b>Ответ поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML"
        )
        await message.answer(f"✅ Ответ отправлен клиенту (<code>{client_id}</code>).", parse_mode="HTML")
        logger.info(f"[SUPPORT] ✅ Reply sent to client {client_id}")
    except Exception as e:
        logger.error(f"[SUPPORT] ❌ Failed to send to client {client_id}: {e}", exc_info=True)
        await message.answer(f"❌ Не удалось отправить. Ошибка: {e}")
