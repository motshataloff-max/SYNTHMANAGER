from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
import texts
from states import DevForm
from keyboards import client_main_menu, cancel_kb
from config import config

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
    
    await message.answer(
        f"✅ <b>Ваша заявка принята!</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"💻 Стек: {data['stack']}\n"
        f"📅 Опыт: {message.text} лет\n\n"
        f"Модератор рассмотрит вашу заявку в течение 24 часов.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    
    # Уведомление модераторам
    user_link = f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.username or 'Кандидат'}</a>"
    header = (
        f"👨‍💻 <b>Новая заявка разработчика</b>\n"
        f"👤 {user_link} (<code>{message.from_user.id}</code>)\n"
        f"📝 Имя: {data['name']}\n"
        f"💻 Стек: {data['stack']}\n"
        f"📅 Опыт: {message.text} лет"
    )
    try:
        await bot.send_message(config.admin_group_id or config.ceo_group_id, header, parse_mode="HTML")
    except Exception:
        pass
