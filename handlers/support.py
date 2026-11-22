"""
SYNTH Platform v2.0 - Служба поддержки
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

@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    await message.answer(
        "🆘 <b>Служба поддержки</b>\n\nОпишите проблему.\n\n<i>Отмена: Отмена</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Отменено.", reply_markup=client_main_menu())
    
    if not message.text and not message.photo:
        return await message.answer("⚠️ Отправьте текст или фото.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Забанен.", reply_markup=client_main_menu())
    
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
    except Exception as e:
        logger.error(f"[SUPPORT] DB ERROR: {e}", exc_info=True)
        return await message.answer("❌ Ошибка.", reply_markup=client_main_menu())
    
    await message.answer(
        f"✅ <b>Принято!</b>\n\n🎫 <code>{ticket_number}</code>\n\nМенеджер скоро ответит.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    await state.clear()
    
    # 🔥 УВЕДОМЛЕНИЕ В ГРУППУ С ПРОСТОЙ МЕТКОЙ
    user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Клиент'}</a>"
    header = (
        f"🆘 <b>Тикет: {ticket_number}</b>\n"
        f"👤 {user_link}\n"
        f"💬 {message.text or '[Медиа]'}\n\n"
        f"#client_{user_id}\n\n"
        f"💡 <i>Ответь (Reply) на это сообщение</i>"
    )
    
    target_group = config.support_group_id
    if not target_group or target_group == 0:
        logger.warning("[SUPPORT] support_group_id не настроен")
        return

    try:
        await bot.send_message(target_group, header, parse_mode="HTML")
        logger.info(f"[SUPPORT] ✅ Sent to group")
    except Exception as e:
        logger.error(f"[SUPPORT] ❌ Failed: {e}", exc_info=True)

@router.message(F.reply_to_message)
async def support_reply_to_client(message: Message, bot: Bot):
    """Ответ менеджера через Reply"""
    if message.chat.id != int(config.support_group_id):
        return
    
    replied_msg = message.reply_to_message
    if not replied_msg:
        return
    
    text = replied_msg.text or ""
    
    # 🔥 ИЩЕМ ПРОСТУЮ МЕТКУ #client_123456789
    match = re.search(r'#client_(\d+)', text)
    if not match:
        await message.answer("⚠️ Это не тикет. Ответь на сообщение бота о новом тикете.")
        return
    
    client_id = int(match.group(1))
    
    try:
        reply_text = message.text or message.caption or "[Медиа]"
        await bot.send_message(
            client_id,
            f"💬 <b>Ответ поддержки:</b>\n\n{reply_text}",
            parse_mode="HTML"
        )
        await message.answer(f"✅ Отправлено клиенту.")
        logger.info(f"[SUPPORT] ✅ Reply sent to {client_id}")
    except Exception as e:
        logger.error(f"[SUPPORT] ❌ Failed: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")
