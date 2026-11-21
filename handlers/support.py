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

async def _ensure_topic(message: Message, state: FSMContext, bot: Bot) -> tuple[int, int]:
    user_id = message.from_user.id
    ticket = await db.find_open_ticket_by_user(user_id)
    if ticket and ticket["topic_id"]:
        return ticket["id"], ticket["topic_id"]
    
    ticket_id = await db.create_ticket(user_id, message.text or "[вложение]")
    try:
        topic = await bot.create_forum_topic(chat_id=config.support_group_id, name=f"🎫 #{ticket_id}")
        topic_id = topic.message_thread_id
        await db.set_ticket_topic(ticket_id, topic_id)
        
        user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Профиль'}</a>"
        header = f"🆘 <b>Тикет #{ticket_id}</b>\n👤 <b>Клиент:</b> {user_link} (<code>{user_id}</code>)\n──────────────────────\n\n"
        await bot.send_message(config.support_group_id, header, message_thread_id=topic_id, parse_mode="HTML")
        return ticket_id, topic_id
    except Exception as e:
        logger.error(f"Ошибка создания темы: {e}")
        return ticket_id, None

async def _forward_to_topic(message: Message, topic_id: int, bot: Bot) -> None:
    try:
        if message.text:
            await bot.send_message(config.support_group_id, f"💬 <b>Клиент пишет:</b>\n{message.text}", message_thread_id=topic_id, parse_mode="HTML")
        elif message.photo:
            await bot.send_photo(config.support_group_id, message.photo[-1].file_id, caption="📷 Фото от клиента", message_thread_id=topic_id)
        else:
            await bot.send_message(config.support_group_id, "📎 [Вложение]", message_thread_id=topic_id)
    except Exception as e:
        logger.error(f"Ошибка пересылки: {e}")

@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    if await _check_cancel(message, state): return
    if not message.text and not message.photo: return await message.answer("⚠️ Отправьте текст или фото.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Аккаунт заблокирован.", reply_markup=main_menu())
    
    ticket_id, topic_id = await _ensure_topic(message, state, bot)
    if topic_id:
        await _forward_to_topic(message, topic_id, bot)
    else:
        user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Профиль'}</a>"
        try:
            await bot.send_message(config.support_group_id, f"🆘 Тикет #{ticket_id} от {user_link}:\n{message.text or '[вложение]'}", parse_mode="HTML")
        except Exception: pass

    _user_msg_counter[user_id] = _user_msg_counter.get(user_id, 0) + 1
    count = _user_msg_counter[user_id]
    
    if count == 3:
        await message.answer("⏳ Хелпер уже изучает ваши сообщения. Пожалуйста, ожидайте.", reply_markup=cancel_kb())
    elif count == 1:
        await message.answer(f"✅ <b>Обращение #{ticket_id} принято!</b>\nПросто продолжайте писать сюда.", parse_mode="HTML", reply_markup=main_menu())

# ОТВЕТ ХЕЛПЕРА (ИСПРАВЛЕННЫЙ ФИЛЬТР: запятые вместо &)
@router.message(F.chat.id == config.support_group_id, F.reply_to_message, F.message_thread_id)
async def support_reply_in_topic(message: Message, bot: Bot):
    is_admin = message.from_user.id == config.owner_id
    is_helper = await db.has_active_role(message.from_user.id, "helper")
    is_manager = await db.has_active_role(message.from_user.id, "manager")
    if not (is_admin or is_helper or is_manager): return
    
    topic_id = message.message_thread_id
    ticket = await db.find_ticket_by_topic(topic_id)
    if not ticket: return
    
    user_id = ticket["user_id"]
    try:
        if message.text:
            await bot.send_message(user_id, f"💬 <b>Ответ поддержки (тикет #{ticket['id']}):</b>\n\n{message.text}", parse_mode="HTML")
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=f"💬 Ответ поддержки (тикет #{ticket['id']})")
        
        if user_id in _user_msg_counter: _user_msg_counter[user_id] = 0
        await message.answer("✅ Ответ доставлен клиенту.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(F.chat.id == config.support_group_id, F.text.startswith("/close"))
async def close_ticket_cmd(message: Message, bot: Bot):
    if not message.message_thread_id: return
    ticket = await db.find_ticket_by_topic(message.message_thread_id)
    if not ticket: return await message.answer("⚠️ Тикет не найден.")
    
    await db.close_ticket(ticket["id"])
    try: await bot.close_forum_topic(config.support_group_id, message.message_thread_id)
    except Exception: pass
    
    try:
        await bot.send_message(ticket["user_id"], f"✅ <b>Тикет #{ticket['id']} закрыт.</b>", parse_mode="HTML")
    except Exception: pass
    await message.answer(f"🔒 Тикет #{ticket['id']} закрыт.")
