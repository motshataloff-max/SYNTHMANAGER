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

async def check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and message.text.lower() in ["отмена", "cancel", "отменить"]:
        await state.clear()
        await message.answer("❌ Заявка отменена.", reply_markup=main_menu())
        return True
    return False

@router.message(DevForm.name)
async def process_name(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(name=message.text.strip())
    await state.set_state(DevForm.age)
    await message.answer("🎂 <b>Шаг 2/5:</b> Сколько вам полных лет? (только число)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.age)
async def process_age(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    if not message.text.isdigit() or int(message.text) < 18:
        await state.clear()
        return await message.answer("⚠️ Мы работаем только с совершеннолетними (18+). Заявка отклонена.", reply_markup=main_menu())
    await state.update_data(age=int(message.text))
    await state.set_state(DevForm.lang)
    await message.answer("💻 <b>Шаг 3/5:</b> На каких языках программирования пишете?", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.lang)
async def process_lang(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(lang=message.text.strip())
    await state.set_state(DevForm.projects)
    await message.answer("📂 <b>Шаг 4/5:</b> Есть ли у вас готовые проекты или портфолио? (ссылки или описание)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.projects)
async def process_projects(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(projects=message.text.strip())
    await state.set_state(DevForm.sam)
    await message.answer("📄 <b>Шаг 5/5:</b> Вы самозанятый (НПД)? (Да/Нет)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DevForm.sam)
async def process_sam(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    is_sam = 1 if message.text.lower() in ["да", "yes", "1"] else 0
    data = await state.get_data()
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username or "нет username"

    try:
        await db.upsert_role(user_id, "dev", "pending", level="junior", referrer_text=f"Имя: {data['name']}, Языки: {data['lang']}, Портфолио: {data['projects']}, Самозанятый: {is_sam}")
        await message.answer("✅ <b>Ваша заявка на разработчика отправлена!</b>\nМенеджер SYNTH рассмотрит её в ближайшее время.", parse_mode="HTML", reply_markup=main_menu())

        notification = (
            f"🆕 <b>Новая заявка на разработчика!</b>\n\n"
            f"👤 <b>Пользователь:</b> <code>{user_id}</code> (@{username})\n"
            f"📝 <b>Имя:</b> {data['name']} | 🎂 <b>Возраст:</b> {data['age']}\n"
            f"💻 <b>Языки:</b> {data['lang']}\n"
            f"📂 <b>Портфолио:</b> {data['projects']}\n"
            f"📄 <b>Самозанятый:</b> {'Да' if is_sam else 'Нет'}"
        )
        # TODO: Добавить message_thread_id для темы "Заявки разработчиков"
        await message.bot.send_message(config.admin_group_id, notification, parse_mode="HTML", reply_markup=dev_moderation_kb(user_id))
    except Exception as e:
        logger.error(f"Ошибка обработки заявки dev: {e}")
        await message.answer("❌ Произошла ошибка при отправке заявки.", reply_markup=main_menu())
