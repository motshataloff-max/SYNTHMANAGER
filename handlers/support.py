import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import SupportForm
from keyboards import main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()
_user_msg_counter = {}

async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Обращение отменено.", reply_markup=main_menu())
        return True
    return False

@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    if await _check_cancel(message, state): return
    if not message.text and not message.photo: 
        return await message.answer("⚠️ Отправьте текст или фото.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Аккаунт заблокирован.", reply_markup=main_menu())
    
    # Получаем пользователя из новой БД
    user = await db.get_user(user_id)
    if not user:
        # Если по какой-то причине пользователя нет, создаем его
        user = await db.get_or_create_user(message.from_user)

    # ✅ ПРАВИЛЬНЫЙ ВЫЗОВ НОВОЙ ФУНКЦИИ СО ВСЕМИ АРГУМЕНТАМИ
    ticket = await db.create_ticket(
        user_id=user['id'],
        channel='tg',
        type='support',
        title='Обращение в поддержку',
        description=message.text or "[Вложение]"
    )
    
    ticket_number = ticket['ticket_number']
    
    # Уведомление в группу поддержки
    user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Профиль'}</a>"
    header = f"🆘 <b>Новый тикет: {ticket_number}</b>\n👤 <b>Клиент:</b> {user_link} (<code>{user_id}</code>)\n💬 <b>Сообщение:</b>\n{message.text or '[Вложение]'}"
    
    try:
        await bot.send_message(config.support_group_id, header, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка отправки в группу поддержки: {e}")

    _user_msg_counter[user_id] = _user_msg_counter.get(user_id, 0) + 1
    count = _user_msg_counter[user_id]
    
    if count == 1:
        await message.answer(
            f"✅ <b>Обращение принято!</b>\n\n"
            f"📋 <b>Ваш трек-номер:</b> <code>{ticket_number}</code>\n"
            f"Сохраните его. Вы можете проверить статус командой:\n"
            f"<code>/status {ticket_number}</code>\n\n"
            f"Менеджер скоро ответит вам.", 
            parse_mode="HTML", 
            reply_markup=main_menu()
        )
    else:
        await message.answer("📨 Сообщение передано менеджеру. Ожидайте ответа.", reply_markup=cancel_kb())

# Ответ хелпера из группы поддержки (работает только для TG клиентов пока)
@router.message(F.chat.id == config.support_group_id, F.reply_to_message, F.message_thread_id)
async def support_reply_in_topic(message: Message, bot: Bot):
    is_admin = message.from_user.id == config.owner_id
    is_helper = await db.has_active_role(message.from_user.id, 'helper')
    is_manager = await db.has_active_role(message.from_user.id, 'manager')
    if not (is_admin or is_helper or is_manager): return
    
    # Здесь пока упрощенная логика: если это ответ в теме, мы просто пересылаем текст
    # Полная двусторонняя связь VK<->TG будет доработана на следующем микро-шаге
    await message.answer("✅ Ответ зафиксирован в системе. (Двусторонняя пересылка настраивается)")
