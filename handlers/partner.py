"""
SYNTH Platform v2.0 - Заявки партнёров
=======================================
Обработка анкет партнёров и отправка заявок на модерацию в группу.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
import texts
from states import PartnerForm
from keyboards import client_main_menu, cancel_kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(PartnerForm.name)
async def process_name(message: Message, state: FSMContext):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    await state.update_data(name=message.text)
    await state.set_state(PartnerForm.niche)
    await message.answer("🎯 В какой нише вы работаете?", reply_markup=cancel_kb())

@router.message(PartnerForm.niche)
async def process_niche(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    
    data = await state.get_data()
    await state.clear()
    
    await db.upsert_role(message.from_user.id, "partner", "pending", referrer_text=f"{data['name']} | {message.text}")
    logger.info(f"[PARTNER] User {message.from_user.id} submitted partner application: {data}")
    
    await message.answer(
        f"✅ <b>Ваша заявка принята!</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🎯 Ниша: {message.text}\n\n"
        f"CEO рассмотрит вашу заявку в течение 48 часов.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    
    # 🔥 ОТПРАВКА УВЕДОМЛЕНИЯ В ГРУППУ CEO
    user_link = f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.username or 'Партнёр'}</a>"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{message.from_user.id}_partner"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}_partner")
        ]
    ])
    
    header = (
        f"🤝 <b>Новая заявка партнёра</b>\n"
        f"{'─' * 30}\n"
        f"👤 {user_link} (<code>{message.from_user.id}</code>)\n"
        f"📝 Имя: {data['name']}\n"
        f"🎯 Ниша: {message.text}\n\n"
        f"💡 <i>Нажмите кнопку для принятия решения</i>"
    )
    
    # Партнёров одобряет только CEO
    target_group = config.ceo_group_id
    
    try:
        await bot.send_message(target_group, header, parse_mode="HTML", reply_markup=kb)
        logger.info(f"[PARTNER] Notification sent to CEO group {target_group}")
    except Exception as e:
        logger.error(f"[PARTNER] Failed to send notification: {e}", exc_info=True)
