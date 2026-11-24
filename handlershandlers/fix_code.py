"""
SYNTH Platform v2.0 - Починить код
"""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
from states import FixCodeForm
from keyboards import cancel_kb, client_main_menu, urgency_kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

WARNING_START = (
    "⚠️ <b>Внимание!</b>\n"
    "Пожалуйста, заполняйте все поля корректно.\n\n"
    "Для отмены нажмите <b>❌ Отмена</b> или введите /cancel"
)

SUCCESS_MESSAGE = (
    "✅ <b>Заявка отправлена!</b>\n\n"
    "Менеджер свяжется с вами в течение 24 часов.\n\n"
    "⚠️ Если не получили ответ — напишите в поддержку и укажите свой @username."
)

@router.message(F.text == "🔧 Починить код")
async def start_fix(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(FixCodeForm.name)
    await message.answer(
        f"🔧 <b>Починить код</b>\n\n{WARNING_START}\n\n"
        "1️⃣ <b>Как к вам обращаться?</b>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(FixCodeForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(FixCodeForm.username)
    hint = f"\n💡 Ваш username: @{message.from_user.username}" if message.from_user.username else ""
    await message.answer(
        f"2️⃣ <b>Telegram username</b>{hint}",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(FixCodeForm.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    await state.update_data(username=f"@{username}")
    await state.set_state(FixCodeForm.phone)
    await message.answer("3️⃣ <b>Номер телефона</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(FixCodeForm.repo)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_repo_fix")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fix")]
    ])
    await message.answer(
        "4️⃣ <b>Ссылка на код</b> (GitHub, опционально)",
        parse_mode="HTML",
        reply_markup=skip_kb
    )

@router.callback_query(F.data == "skip_repo_fix")
async def skip_repo(callback: Message, state: FSMContext):
    await state.update_data(repo="Нет")
    await state.set_state(FixCodeForm.problem)
    await callback.message.edit_text(
        "5️⃣ <b>Описание проблемы</b>\n(Что не работает?)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.callback_query(F.data == "cancel_fix")
async def cancel_fix(callback: Message, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заявка отменена.", reply_markup=client_main_menu())

@router.message(FixCodeForm.repo)
async def process_repo(message: Message, state: FSMContext):
    await state.update_data(repo=message.text.strip())
    await state.set_state(FixCodeForm.problem)
    await message.answer("5️⃣ <b>Описание проблемы</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(FixCodeForm.problem)
async def process_problem(message: Message, state: FSMContext):
    await state.update_data(problem=message.text.strip())
    await state.set_state(FixCodeForm.expected)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_expected_fix")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_fix")]
    ])
    await message.answer(
        "6️⃣ <b>Ожидаемый результат</b> (опционально)",
        parse_mode="HTML",
        reply_markup=skip_kb
    )

@router.callback_query(F.data == "skip_expected_fix")
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
    urgency = callback.data.replace("urgency_", "")
    await state.update_data(urgency=urgency)
    await finish_fix(callback.message, state)

async def finish_fix(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    description = (
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Telegram:</b> {data['username']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Репозиторий:</b> {data['repo']}\n"
        f"❌ <b>Проблема:</b>\n{data['problem']}\n"
        f"✅ <b>Ожидаемый результат:</b> {data['expected']}\n"
        f"⚡ <b>Срочность:</b> {data['urgency']}"
    )
    
    ticket = await db.create_ticket(
        user_id=message.from_user.id,
        channel="tg",
        type="fix_code",
        title="🔧 Починить код",
        description=description,
        budget=0
    )
    
    logger.info(f"[FIX_CODE] User {message.from_user.id} created ticket {ticket['ticket_number']}")
    await message.answer(SUCCESS_MESSAGE, parse_mode="HTML", reply_markup=client_main_menu())
    
    try:
        admin_msg = (
            f"🔔 <b>НОВАЯ ЗАЯВКА: {ticket['ticket_number']}</b>\n"
            f"🔧 Тип: Починить код\n\n{description}\n\n📅 {ticket['created_at']}"
        )
        target_chat = config.admin_group_id or config.ceo_group_id
        if target_chat:
            await message.bot.send_message(target_chat, admin_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
