"""
SYNTH Platform v2.0 - Заказать разработку
"""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
from states import ClientOrderForm
from keyboards import cancel_kb, client_main_menu
from config import config

logger = logging.getLogger(__name__)
router = Router()

WARNING_START = (
    "⚠️ <b>Внимание!</b>\n"
    "Пожалуйста, заполняйте все поля корректно. Менеджер свяжется с вами по указанным контактам.\n\n"
    "Для отмены нажмите <b>❌ Отмена</b> или введите /cancel"
)

SUCCESS_MESSAGE = (
    "✅ <b>Заявка отправлена!</b>\n\n"
    "Менеджер свяжется с вами в течение 24 часов.\n\n"
    "⚠️ Если не получили ответ — напишите в поддержку и укажите свой @username."
)

@router.message(F.text == "🛒 Заказать разработку")
async def start_order(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ClientOrderForm.name)
    await message.answer(
        f"🛒 <b>Заказать разработку</b>\n\n{WARNING_START}\n\n"
        "1️⃣ <b>Как к вам обращаться?</b>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(ClientOrderForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ClientOrderForm.username)
    hint = f"\n💡 Ваш username: @{message.from_user.username}" if message.from_user.username else ""
    await message.answer(
        f"2️⃣ <b>Telegram username</b>{hint}\n(Например: ivan_dev)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(ClientOrderForm.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    await state.update_data(username=f"@{username}")
    await state.set_state(ClientOrderForm.phone)
    await message.answer(
        "3️⃣ <b>Номер телефона</b>\n(Например: +7 999 123-45-67)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(ClientOrderForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(ClientOrderForm.task)
    await message.answer(
        "4️⃣ <b>Кратко опишите задачу</b>\n(Что нужно сделать?)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(ClientOrderForm.task)
async def process_task(message: Message, state: FSMContext):
    await state.update_data(task=message.text.strip())
    await state.set_state(ClientOrderForm.wishes)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_wishes")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ])
    await message.answer(
        "5️⃣ <b>Дополнительные пожелания</b> (опционально)",
        parse_mode="HTML",
        reply_markup=skip_kb
    )

@router.callback_query(F.data == "skip_wishes")
async def skip_wishes(callback: Message, state: FSMContext):
    await state.update_data(wishes="Нет")
    await finish_order(callback.message, state)

@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: Message, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменен.", reply_markup=client_main_menu())

@router.message(ClientOrderForm.wishes)
async def process_wishes(message: Message, state: FSMContext):
    await state.update_data(wishes=message.text.strip())
    await finish_order(message, state)

async def finish_order(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    description = (
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Telegram:</b> {data['username']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Задача:</b>\n{data['task']}\n"
        f"💬 <b>Пожелания:</b> {data['wishes']}"
    )
    
    ticket = await db.create_ticket(
        user_id=message.from_user.id,
        channel="tg",
        type="project",
        title="🛒 Заказать разработку",
        description=description,
        budget=0
    )
    
    logger.info(f"[CLIENT] User {message.from_user.id} created ticket {ticket['ticket_number']}")
    
    await message.answer(SUCCESS_MESSAGE, parse_mode="HTML", reply_markup=client_main_menu())
    
    try:
        admin_msg = (
            f"🔔 <b>НОВАЯ ЗАЯВКА: {ticket['ticket_number']}</b>\n"
            f"🛒 Тип: Заказать разработку\n\n{description}\n\n📅 {ticket['created_at']}"
        )
        target_chat = config.admin_group_id or config.ceo_group_id
        if target_chat:
            await message.bot.send_message(target_chat, admin_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
