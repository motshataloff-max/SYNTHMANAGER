import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import db
from states import PartnerForm
from keyboards import cancel_kb, client_main_menu, inline_skip_and_cancel
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🤝 Стать партнером")
async def start_partner(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(PartnerForm.name)
    await message.answer("🤝 <b>Стать партнером</b>\n\n1️⃣ <b>Как к вам обращаться?</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PartnerForm.username)
    await message.answer("2️⃣ <b>Telegram username</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.username)
async def process_username(message: Message, state: FSMContext):
    await state.update_data(username=f"@{message.text.strip().lstrip('@')}")
    await state.set_state(PartnerForm.phone)
    await message.answer("3️⃣ <b>Номер телефона</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await db.update_user_phone(message.from_user.id, message.text.strip())
    await state.set_state(PartnerForm.email)
    await message.answer("4️⃣ <b>Email</b> (или нажмите 'Пропустить')", parse_mode="HTML", reply_markup=inline_skip_and_cancel("skip_email"))

@router.callback_query(F.data == "skip_email")
async def skip_email(callback: CallbackQuery, state: FSMContext):
    await state.update_data(email="Не указан")
    await state.set_state(PartnerForm.project)
    await callback.message.edit_text("5️⃣ <b>Какой у вас проект/аудитория?</b>", parse_mode="HTML")

@router.message(PartnerForm.email)
async def process_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await state.set_state(PartnerForm.project)
    await message.answer("5️⃣ <b>Какой у вас проект/аудитория?</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.project)
async def process_project(message: Message, state: FSMContext):
    await state.update_data(project=message.text.strip())
    await state.set_state(PartnerForm.offer)
    await message.answer("6️⃣ <b>Ваше предложение</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(PartnerForm.offer)
async def process_offer(message: Message, state: FSMContext):
    await state.update_data(offer=message.text.strip())
    await finish_partner(message, state)

@router.callback_query(F.data == "cancel_form")
async def cancel_form_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.", parse_mode="HTML")
    await callback.message.answer("Выберите действие:", reply_markup=client_main_menu())

async def finish_partner(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    desc = f"👤 {data['name']}\n📱 {data['username']}\n📞 {data['phone']}\n📧 {data['email']}\n🎯 {data['project']}\n💼 {data['offer']}"
    ticket = await db.create_ticket(user_id=message.from_user.id, channel="tg", type="partner", title="🤝 Стать партнером", description=desc)
    await message.answer("✅ Заявка отправлена! Менеджер свяжется в течение 24 часов.", parse_mode="HTML", reply_markup=client_main_menu())
    try:
        await message.bot.send_message(config.owner_id, f"🔔 ПАРТНЁРСКАЯ ЗАЯВКА: {ticket['ticket_number']}\n{desc}", parse_mode="HTML")
    except: pass
