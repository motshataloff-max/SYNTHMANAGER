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

async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Заявка отменена.", reply_markup=main_menu())
        return True
    return False

async def _require_text(message: Message, state: FSMContext) -> bool:
    if not message.text:
        await message.answer("⚠️ Пожалуйста, отправьте текстом, а не файлом или стикером.", reply_markup=cancel_kb())
        return True
    return False

@router.message(PartnerForm.name)
async def process_name(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(name=message.text.strip())
    await state.set_state(PartnerForm.info)
    await message.answer("🏢 <b>Шаг 2/6:</b> Чем вы занимаетесь? (сайт, платформа, бизнес)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.info)
async def process_info(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(info=message.text.strip())
    await state.set_state(PartnerForm.offer)
    await message.answer("🤝 <b>Шаг 3/6:</b> Что вы предлагаете? (размещение нашего товара, обмен клиентами и т.д.)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.offer)
async def process_offer(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(offer=message.text.strip())
    await state.set_state(PartnerForm.country)
    await message.answer("🌍 <b>Шаг 4/6:</b> Из какой вы страны?", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.country)
async def process_country(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if not message.text: return
    country = message.text.strip().lower()
    forbidden = ["сша", "usa", "украина", "ukraine", "великобритания", "uk", "евросоюз", "eu"]
    if any(f in country for f in forbidden):
        await state.clear()
        return await message.answer("🇷🇺 Извините, SYNTH не работает с представителями недружественных стран. Заявка отклонена.", reply_markup=main_menu())
    
    await state.update_data(country=message.text.strip())
    await state.set_state(PartnerForm.age)
    await message.answer("🎂 <b>Шаг 5/6:</b> Сколько вам полных лет? (только число)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.age)
async def process_age(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if not message.text or not message.text.isdigit() or int(message.text) < 18:
        await state.clear()
        return await message.answer("⚠️ Мы работаем только с совершеннолетними (18+). Заявка отклонена.", reply_markup=main_menu())
    
    await state.update_data(age=int(message.text))
    await state.set_state(PartnerForm.contact)
    await message.answer("📞 <b>Шаг 6/6:</b> Как с вами связаться? (Ваш @username или номер телефона)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.contact)
async def process_contact(message: Message, state: FSMContext):
    try:
        if await _check_cancel(message, state): return
        if not message.text or len(message.text.strip()) < 3:
            return await message.answer("⚠️ Контакт слишком короткий. Напишите @username или номер телефона:", reply_markup=cancel_kb())
        
        data = await state.get_data()
        await state.clear()

        user_id = message.from_user.id
        username = message.from_user.username
        user_link = f"<a href=\"tg://user?id={user_id}\">{username or 'Профиль'}</a>"

        referrer_text = (
            f"Имя/Компания: {data.get('name')}\n"
            f"Деятельность: {data.get('info')}\n"
            f"Предложение: {data.get('offer')}\n"
            f"Страна: {data.get('country')} | Возраст: {data.get('age')}\n"
            f"Контакт: {message.text.strip()}"
        )

        await db.upsert_role(user_id, "partner", "pending", referrer_text=referrer_text)
        
        await message.answer(
            "✅ <b>Ваша заявка на партнёрство отправлена лично CEO!</b>\n\n"
            "Мы свяжемся с вами после рассмотрения.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

        notification = (
            f"🤝 <b>Новая заявка на ПАРТНЁРСТВО!</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_link} (<code>{user_id}</code>)\n"
            f"🏢 <b>Имя/Компания:</b> {data.get('name')}\n"
            f"💼 <b>Деятельность:</b> {data.get('info')}\n"
            f"📩 <b>Предложение:</b> {data.get('offer')}\n"
            f"🌍 <b>Страна:</b> {data.get('country')} | 🎂 <b>Возраст:</b> {data.get('age')}\n"
            f"📞 <b>Контакт:</b> {message.text.strip()}"
        )
        
        # Отправляем строго в личную группу CEO
        try:
            await message.bot.send_message(
                config.ceo_group_id, 
                notification, 
                parse_mode="HTML", 
                reply_markup=partner_moderation_kb(user_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки заявки partner в CEO группу: {e}")
            await message.bot.send_message(config.owner_id, notification + "\n\n⚠️ Бот не смог написать в группу CEO!", parse_mode="HTML")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В PARTNER: {e}")
        await message.answer("❌ Произошла техническая ошибка. Попробуйте позже.", reply_markup=main_menu())
