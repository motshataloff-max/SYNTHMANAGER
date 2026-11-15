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

async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Обращение в поддержку отменено.", reply_markup=main_menu())
        return True
    return False

@router.message(SupportForm.waiting_message)
async def process_message(message: Message, state: FSMContext):
    try:
        if await _check_cancel(message, state): return
        if not message.text:
            return await message.answer("⚠️ Пожалуйста, опишите проблему текстом.", reply_markup=cancel_kb())
        
        user_id = message.from_user.id
        username = message.from_user.username
        user_link = f"<a href=\"tg://user?id={user_id}\">{username or 'Профиль'}</a>"
        
        # 1. Создаем тикет в базе данных
        ticket_id = await db.create_ticket(user_id, message.text.strip())
        await state.clear()
        
        # 2. Отвечаем клиенту
        await message.answer(
            f"✅ <b>Ваше обращение #{ticket_id} принято!</b>\n\n"
            f"Хелпер SYNTH ответит вам в личных сообщениях в ближайшее время.\n"
            f"<i>Чтобы отменить ожидание, нажмите /cancel</i>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

        # 3. Уведомление в группу поддержки
        notification = (
            f"🆘 <b>Новый тикет поддержки #{ticket_id}!</b>\n\n"
            f"👤 <b>От:</b> {user_link} (<code>{user_id}</code>)\n"
            f"📝 <b>Сообщение:</b> {message.text.strip()}\n\n"
            f"<i>Чтобы ответить клиенту, используйте команду:</i>\n"
            f"<code>/msg {user_id} Ваш ответ</code>"
        )
        
        try:
            await message.bot.send_message(config.support_group_id, notification, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка отправки тикета в группу поддержки: {e}")
            # Фоллбэк: если группа поддержки недоступна, шлем CEO
            await message.bot.send_message(
                config.owner_id, 
                notification + "\n\n⚠️ Бот не смог написать в группу поддержки!", 
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В SUPPORT: {e}")
        await message.answer("❌ Произошла техническая ошибка. Попробуйте позже.", reply_markup=main_menu())
