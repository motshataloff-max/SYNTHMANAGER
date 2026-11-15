import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import DevForm
from keyboards import main_menu, cancel_kb, dev_moderation_kb

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

@router.message(DevForm.name)
async def process_name(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(name=message.text.strip())
    await state.set_state(DevForm.age)
    await message.answer("🎂 <b>Шаг 2/7:</b> Сколько вам полных лет? (только число)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.age)
async def process_age(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if not message.text or not message.text.isdigit() or int(message.text) < 18:
        await state.clear()
        return await message.answer("⚠️ Мы работаем только с совершеннолетними (18+). Заявка отклонена.", reply_markup=main_menu())
    await state.update_data(age=int(message.text))
    await state.set_state(DevForm.lang)
    await message.answer("💻 <b>Шаг 3/7:</b> На каких языках программирования пишете?", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.lang)
async def process_lang(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(lang=message.text.strip())
    await state.set_state(DevForm.projects)
    await message.answer("📂 <b>Шаг 4/7:</b> Есть ли у вас готовые проекты или портфолио? (ссылки или описание)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.projects)
async def process_projects(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(projects=message.text.strip())
    await state.set_state(DevForm.hours)
    await message.answer("⏱ <b>Шаг 5/7:</b> Сколько часов в день/неделю вы готовы уделять работе?", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.hours)
async def process_hours(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(hours=message.text.strip())
    await state.set_state(DevForm.goal)
    await message.answer("🎯 <b>Шаг 6/7:</b> Какова ваша цель? (Напишите: Заработок или Опыт/Портфолио)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.goal)
async def process_goal(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(goal=message.text.strip())
    await state.set_state(DevForm.sam)
    await message.answer("📄 <b>Шаг 7/7:</b> Вы самозанятый (НПД)? (Напишите Да или Нет)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.sam)
async def process_sam(message: Message, state: FSMContext):
    try:
        if await _check_cancel(message, state): return
        if not message.text:
            return await message.answer("⚠️ Пожалуйста, напишите Да или Нет текстом.", reply_markup=cancel_kb())
            
        is_sam = 1 if message.text.lower() in ["да", "yes", "1"] else 0
        data = await state.get_data()
        await state.clear()

        user_id = message.from_user.id
        username = message.from_user.username
        user_link = f"<a href=\"tg://user?id={user_id}\">{username or 'Профиль'}</a>"

        referrer_text = (
            f"Имя: {data.get('name')}\n"
            f"Возраст: {data.get('age')}\n"
            f"Языки: {data.get('lang')}\n"
            f"Портфолио: {data.get('projects')}\n"
            f"Часы: {data.get('hours')}\n"
            f"Цель: {data.get('goal')}\n"
            f"Самозанятый: {'Да' if is_sam else 'Нет'}"
        )

        await db.upsert_role(user_id, "dev", "pending", level="junior", referrer_text=referrer_text)
        
        await message.answer(
            "✅ <b>Ваша заявка на разработчика отправлена!</b>\n\n"
            "Менеджер SYNTH рассмотрит её в ближайшее время.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

        notification = (
            f"🆕 <b>Новая заявка на разработчика!</b>\n\n"
            f"👤 <b>Пользователь:</b> {user_link} (<code>{user_id}</code>)\n"
            f"📝 <b>Имя:</b> {data.get('name')} | 🎂 <b>Возраст:</b> {data.get('age')}\n"
            f"💻 <b>Языки:</b> {data.get('lang')}\n"
            f"📂 <b>Портфолио:</b> {data.get('projects')}\n"
            f"⏱ <b>Часы:</b> {data.get('hours')} | 🎯 <b>Цель:</b> {data.get('goal')}\n"
            f"📄 <b>Самозанятый:</b> {'Да' if is_sam else 'Нет'}"
        )
        
        try:
            await message.bot.send_message(
                config.admin_group_id, 
                notification, 
                parse_mode="HTML", 
                reply_markup=dev_moderation_kb(user_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки заявки dev в группу: {e}")
            await message.bot.send_message(config.owner_id, notification + "\n\n⚠️ Бот не смог написать в группу админов!", parse_mode="HTML")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В DEV: {e}")
        await message.answer("❌ Произошла техническая ошибка. Попробуйте позже.", reply_markup=main_menu())
