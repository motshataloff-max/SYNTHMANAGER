"""
SYNTH Platform v2.0 - Обработчики: Поддержка
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

import db
from states import SupportForm
from keyboards import cancel_kb, client_main_menu
from config import config

logger = logging.getLogger(__name__)
router = Router()

# Тексты предупреждений
WARNING_START = (
    "⚠️ <b>Внимание!</b>\n"
    "Пожалуйста, заполняйте все поля корректно. Менеджер свяжется с вами по указанным контактам.\n\n"
    "Для отмены в любой момент нажмите кнопку <b>❌ Отмена</b> или введите /cancel"
)

SUCCESS_MESSAGE = (
    "✅ <b>Заявка успешно отправлена!</b>\n\n"
    "Менеджер свяжется с вами в течение 24 часов.\n\n"
    "⚠️ <b>Важно:</b> Если вы не получили ответ, напишите в поддержку и <b>обязательно укажите свой @username</b>."
)

@router.message(F.text == "🆘 Поддержка")
async def start_support(message: Message, state: FSMContext):
    logger.info(f"[SUPPORT] User {message.from_user.id} started support flow")
    await state.clear()
    await state.set_state(SupportForm.name)
    await message.answer(
        f"🆘 <b>Поддержка</b>\n\n{WARNING_START}\n\n"
        "1️⃣ <b>Как к вам обращаться?</b>\n(Введите ваше имя или никнейм)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(SupportForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(SupportForm.username)
    
    current_un = message.from_user.username
    hint = f"\n\n💡 Ваш текущий юзернейм: @{current_un}" if current_un else ""
    
    await message.answer(
        f"2️⃣ <b>Ваш Telegram username</b>{hint}\n"
        "(Например: @ivan_dev). Это обязательно для связи!",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(SupportForm.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    await state.update_data(username=f"@{username}")
    await state.set_state(SupportForm.phone)
    
    await message.answer(
        "3️⃣ <b>Ваш номер телефона</b>\n"
        "(Например: +7 999 123-45-67). Обязательно для оперативной связи!",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(SupportForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(SupportForm.description)
    
    await message.answer(
        "4️⃣ <b>Описание проблемы</b>\n"
        "(Подробно опишите, что произошло или что нужно сделать)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(SupportForm.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await finish_support(message, state)

async def finish_support(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    description = (
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Telegram:</b> {data['username']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>Проблема:</b>\n{data['description']}"
    )
    
    ticket = await db.create_ticket(
        user_id=message.from_user.id,
        channel="tg",
        type="support",
        title="🆘 Поддержка",
        description=description,
        budget=0
    )
    
    logger.info(f"[SUPPORT] User {message.from_user.id} created support ticket {ticket['ticket_number']}")
    
    await message.answer(
        SUCCESS_MESSAGE,
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    
    try:
        admin_msg = (
            f"🔔 <b>НОВАЯ ЗАЯВКА: {ticket['ticket_number']}</b>\n"
            f"🆘 Тип: Поддержка\n\n"
            f"{description}\n\n"
            f"📅 {ticket['created_at']}"
        )
        target_chat = config.support_group_id or config.admin_group_id or config.ceo_group_id
        if target_chat:
            await message.bot.send_message(target_chat, admin_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
