import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
from states import SupportForm
from keyboards import cancel_kb, client_main_menu
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🆘 Поддержка")
async def start_support(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SupportForm.name)
    await message.answer("🆘 <b>Поддержка</b>\n\n1️⃣ <b>Как к вам обращаться?</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(SupportForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(SupportForm.username)
    await message.answer("2️⃣ <b>Telegram username</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(SupportForm.username)
async def process_username(message: Message, state: FSMContext):
    await state.update_data(username=f"@{message.text.strip().lstrip('@')}")
    await state.set_state(SupportForm.phone)
    await message.answer("3️⃣ <b>Номер телефона</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(SupportForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await db.update_user_phone(message.from_user.id, message.text.strip())
    await state.set_state(SupportForm.description)
    await message.answer("4️⃣ <b>Описание проблемы</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(SupportForm.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await finish_support(message, state)

async def finish_support(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    desc = f"👤 {data['name']}\n📱 {data['username']}\n📞 {data['phone']}\n❓ {data['description']}"
    ticket = await db.create_ticket(user_id=message.from_user.id, channel="tg", type="support", title="🆘 Поддержка", description=desc)
    await message.answer("✅ Заявка отправлена! Менеджер свяжется в течение 24 часов.", parse_mode="HTML", reply_markup=client_main_menu())
    try:
        await message.bot.send_message(config.ceo_group_id, f"🔔 ПОДДЕРЖКА: {ticket['ticket_number']}\n{desc}", parse_mode="HTML")
    except: pass
