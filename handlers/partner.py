import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import PartnerForm
from keyboards import main_menu, cancel_kb, partner_moderation_kb

logger = logging.getLogger(__name__)
router = Router()

async def check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and message.text.lower() in ["отмена", "cancel", "отменить"]:
        await state.clear()
        await message.answer("❌ Заявка отменена.", reply_markup=main_menu())
        return True
    return False

@router.message(PartnerForm.name)
async def process_name(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(name=message.text.strip())
    await state.set_state(PartnerForm.info)
    await message.answer("🏢 <b>Шаг 2/3:</b> Чем вы занимаетесь? (сайт, платформа, бизнес)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.info)
async def process_info(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(info=message.text.strip())
    await state.set_state(PartnerForm.offer)
    await message.answer("🤝 <b>Шаг 3/3:</b> Что вы предлагаете? (размещение нашего товара, обмен клиентами и т.д.)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.offer)
async def process_offer(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    data = await state.get_data()
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username or "нет username"

    try:
        await db.upsert_role(user_id, "partner", "pending", referrer_text=f"Имя: {data['name']}, Инфо: {data['info']}, Предложение: {message.text.strip()}")
        await message.answer("✅ <b>Ваша заявка на партнёрство отправлена лично CEO!</b>\nМы свяжемся с вами после рассмотрения.", parse_mode="HTML", reply_markup=main_menu())

        notification = (
            f"🤝 <b>Новая заявка на ПАРТНЁРСТВО!</b>\n\n"
            f"👤 <b>Пользователь:</b> <code>{user_id}</code> (@{username})\n"
            f"🏢 <b>Имя/Компания:</b> {data['name']}\n"
            f"💼 <b>Деятельность:</b> {data['info']}\n"
            f"📩 <b>Предложение:</b> {message.text.strip()}"
        )
        # Отправляем строго в личную группу CEO
        await message.bot.send_message(config.ceo_group_id, notification, parse_mode="HTML", reply_markup=partner_moderation_kb(user_id))
    except Exception as e:
        logger.error(f"Ошибка обработки заявки partner: {e}")
        await message.answer("❌ Произошла ошибка при отправке заявки.", reply_markup=main_menu())
