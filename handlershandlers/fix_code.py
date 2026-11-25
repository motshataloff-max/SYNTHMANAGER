import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
from states import FixCodeForm
from keyboards import cancel_kb, client_main_menu, skip_button, urgency_kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🔧 Починить код")
async def start_fix(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(FixCodeForm.name)
    await message.answer("🔧 <b>Починить код</b>\n\n1️⃣ <b>Как к вам обращаться?</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(FixCodeForm.username)
    await message.answer("2️⃣ <b>Telegram username</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.username)
async def process_username(message: Message, state: FSMContext):
    await state.update_data(username=f"@{message.text.strip().lstrip('@')}")
    await state.set_state(FixCodeForm.phone)
    await message.answer("3️⃣ <b>Номер телефона</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await db.update_user_phone(message.from_user.id, message.text.strip())
    await state.set_state(FixCodeForm.repo)
    await message.answer("4️⃣ <b>Ссылка на код</b> (или нажмите Пропустить)", parse_mode="HTML", reply_markup=skip_button("skip_repo"))

@router.callback_query(F.data == "skip_repo")
async def skip_repo(callback: Message, state: FSMContext):
    await state.update_data(repo="Нет")
    await state.set_state(FixCodeForm.problem)
    await callback.message.edit_text("5️⃣ <b>Описание проблемы</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.repo)
async def process_repo(message: Message, state: FSMContext):
    await state.update_data(repo=message.text.strip())
    await state.set_state(FixCodeForm.problem)
    await message.answer("5️⃣ <b>Описание проблемы</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.problem)
async def process_problem(message: Message, state: FSMContext):
    await state.update_data(problem=message.text.strip())
    await state.set_state(FixCodeForm.expected)
    await message.answer("6️⃣ <b>Ожидаемый результат</b> (или Пропустить)", parse_mode="HTML", reply_markup=skip_button("skip_expected"))

@router.callback_query(F.data == "skip_expected")
async def skip_expected(callback: Message, state: FSMContext):
    await state.update_data(expected="Не указано")
    await state.set_state(FixCodeForm.urgency)
    await callback.message.edit_text("7️⃣ <b>Срочность</b>", parse_mode="HTML", reply_markup=urgency_kb())

@router.message(FixCodeForm.expected)
async def process_expected(message: Message, state: FSMContext):
    await state.update_data(expected=message.text.strip())
    await state.set_state(FixCodeForm.urgency)
    await message.answer("7️⃣ <b>Срочность</b>", parse_mode="HTML", reply_markup=urgency_kb())

@router.callback_query(F.data.startswith("urgency_"))
async def select_urgency(callback: Message, state: FSMContext):
    await state.update_data(urgency=callback.data.replace("urgency_", ""))
    await finish_fix(callback.message, state)

async def finish_fix(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    desc = f"👤 {data['name']}\n📱 {data['username']}\n📞 {data['phone']}\n🔗 {data['repo']}\n❌ {data['problem']}\n✅ {data['expected']}\n⚡ {data['urgency']}"
    ticket = await db.create_ticket(user_id=message.from_user.id, channel="tg", type="fix_code", title="🔧 Починить код", description=desc)
    await message.answer("✅ Заявка отправлена! Менеджер свяжется в течение 24 часов.", parse_mode="HTML", reply_markup=client_main_menu())
    try:
        await message.bot.send_message(config.ceo_group_id, f"🔔 ЗАЯВКА: {ticket['ticket_number']}\n{desc}", parse_mode="HTML")
    except: pass
