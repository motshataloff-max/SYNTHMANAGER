import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
from states import ClientOrderForm
from keyboards import cancel_kb, client_main_menu, skip_button
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🛒 Заказать разработку")
async def start_order(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ClientOrderForm.name)
    await message.answer("🛒 <b>Заказать разработку</b>\n\n1️⃣ <b>Как к вам обращаться?</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientOrderForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ClientOrderForm.username)
    hint = f"\n💡 Ваш: @{message.from_user.username}" if message.from_user.username else ""
    await message.answer(f"2️⃣ <b>Telegram username</b>{hint}", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientOrderForm.username)
async def process_username(message: Message, state: FSMContext):
    await state.update_data(username=f"@{message.text.strip().lstrip('@')}")
    await state.set_state(ClientOrderForm.phone)
    await message.answer("3️⃣ <b>Номер телефона</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientOrderForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await db.update_user_phone(message.from_user.id, message.text.strip())
    await state.set_state(ClientOrderForm.task)
    await message.answer("4️⃣ <b>Кратко опишите задачу</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientOrderForm.task)
async def process_task(message: Message, state: FSMContext):
    await state.update_data(task=message.text.strip())
    await state.set_state(ClientOrderForm.wishes)
    await message.answer("5️⃣ <b>Доп. пожелания</b> (или нажмите Пропустить)", parse_mode="HTML", reply_markup=skip_button("skip_wishes"))

@router.callback_query(F.data == "skip_wishes")
async def skip_wishes(callback: Message, state: FSMContext):
    await state.update_data(wishes="Нет")
    await finish_order(callback.message, state)

@router.message(ClientOrderForm.wishes)
async def process_wishes(message: Message, state: FSMContext):
    await state.update_data(wishes=message.text.strip())
    await finish_order(message, state)

async def finish_order(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    desc = f"👤 {data['name']}\n📱 {data['username']}\n📞 {data['phone']}\n📝 {data['task']}\n💬 {data['wishes']}"
    ticket = await db.create_ticket(user_id=message.from_user.id, channel="tg", type="project", title="🛒 Заказать разработку", description=desc)
    await message.answer("✅ Заявка отправлена! Менеджер свяжется в течение 24 часов.", parse_mode="HTML", reply_markup=client_main_menu())
    try:
        await message.bot.send_message(config.ceo_group_id, f"🔔 НОВАЯ ЗАЯВКА: {ticket['ticket_number']}\n{desc}", parse_mode="HTML")
    except: pass
