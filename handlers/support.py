import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import SupportForm
from keyboards import main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

async def check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and message.text.lower() in ["отмена", "cancel", "отменить"]:
        await state.clear()
        await message.answer("❌ Обращение отменено.", reply_markup=main_menu())
        return True
    return False

@router.message(SupportForm.waiting_message)
async def process_message(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    
    user_id = message.from_user.id
    username = message.from_user.username or "нет username"
    
    try:
        ticket_id = await db.create_ticket(user_id, message.text.strip())
        await state.clear()
        
        await message.answer("✅ <b>Ваше обращение принято!</b>\nХелпер SYNTH ответит вам в личных сообщениях в ближайшее время.", parse_mode="HTML", reply_markup=main_menu())

        notification = (
            f"🆘 <b>Новый тикет поддержки #{ticket_id}!</b>\n\n"
            f"👤 <b>От:</b> <code>{user_id}</code> (@{username})\n"
            f"📝 <b>Сообщение:</b> {message.text.strip()}\n\n"
            f"<i>Чтобы ответить, используйте: /msg {user_id} Ваш ответ</i>"
        )
        # TODO: Добавить message_thread_id для темы "Поддержка"
        await message.bot.send_message(config.admin_group_id, notification, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка создания тикета: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.", reply_markup=main_menu())
