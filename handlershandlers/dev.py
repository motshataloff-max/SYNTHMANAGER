"""
SYNTH Platform v2.0 - Заявки разработчиков
===========================================
Обработка анкет разработчиков и отправка заявок на модерацию в группу.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
import texts
from states import DevForm
from keyboards import client_main_menu, cancel_kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(DevForm.name)
async def process_name(message: Message, state: FSMContext):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    if not message.text or len(message.text) < 2:
        return await message.answer("⚠️ Укажите имя.", reply_markup=cancel_kb())
    await state.update_data(name=message.text)
    await state.set_state(DevForm.stack)
    await message.answer("💻 Какой у вас стек технологий? (Python, JS, Go и т.д.)", reply_markup=cancel_kb())

@router.message(DevForm.stack)
async def process_stack(message: Message, state: FSMContext):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    await state.update_data(stack=message.text)
    await state.set_state(DevForm.experience)
    await message.answer("📅 Сколько лет опыта?", reply_markup=cancel_kb())

@router.message(DevForm.experience)
async def process_experience(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    
    data = await state.get_data()
    await state.clear()
    
    # Сохраняем заявку как pending роль
    await db.upsert_role(message.from_user.id, "dev", "pending", level=f"{data['stack']}, {message.text} лет")
    logger.info(f"[DEV] User {message.from_user.id} submitted dev application: {data}")
    
    await message.answer(
        f"✅ <b>Ваша заявка принята!</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"💻 Стек: {data['stack']}\n"
        f"📅 Опыт: {message.text} лет\n\n"
        f"Модераторы рассмотрят вашу заявку в течение 24 часов.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    
    # 🔥 ОТПРАВКА УВЕДОМЛЕНИЯ В ГРУППУ МОДЕРАТОРОВ
    user_link = f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.username or 'Кандидат'}</a>"
    
    # Кнопки для модерации
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{message.from_user.id}_dev"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}_dev")
        ]
    ])
    
    header = (
        f"👨‍💻 <b>Новая заявка разработчика</b>\n"
        f"{'─' * 30}\n"
        f"👤 {user_link} (<code>{message.from_user.id}</code>)\n"
        f"📝 Имя: {data['name']}\n"
        f"💻 Стек: {data['stack']}\n"
        f"📅 Опыт: {message.text} лет\n\n"
        f"💡 <i>Нажмите кнопку для принятия решения</i>"
    )
    
    # Отправляем в группу админов (или CEO, если группы нет)
    target_group = config.admin_group_id if config.admin_group_id else config.ceo_group_id
    
    try:
        await bot.send_message(target_group, header, parse_mode="HTML", reply_markup=kb)
        logger.info(f"[DEV] Notification sent to group {target_group}")
    except Exception as e:
        logger.error(f"[DEV] Failed to send notification to group: {e}", exc_info=True)

