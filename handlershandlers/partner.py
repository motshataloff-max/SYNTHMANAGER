"""
SYNTH Platform v2.0 - Обработчики: Стать партнером
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

import db
from states import PartnerForm
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

@router.message(F.text == "🤝 Стать партнером")
async def start_partner(message: Message, state: FSMContext):
    logger.info(f"[PARTNER] User {message.from_user.id} started partner flow")
    await state.clear()
    await state.set_state(PartnerForm.name)
    await message.answer(
        f"🤝 <b>Стать партнером</b>\n\n{WARNING_START}\n\n"
        "1️⃣ <b>Как к вам обращаться?</b>\n(Введите ваше имя или никнейм)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(PartnerForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(PartnerForm.username)
    
    current_un = message.from_user.username
    hint = f"\n\n💡 Ваш текущий юзернейм: @{current_un}" if current_un else ""
    
    await message.answer(
        f"2️⃣ <b>Ваш Telegram username</b>{hint}\n"
        "(Например: @ivan_dev). Это обязательно для связи!",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(PartnerForm.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    await state.update_data(username=f"@{username}")
    await state.set_state(PartnerForm.phone)
    
    await message.answer(
        "3️⃣ <b>Ваш номер телефона</b>\n"
        "(Например: +7 999 123-45-67). Обязательно для оперативной связи!",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(PartnerForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(PartnerForm.email)
    
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_email_partner")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_partner")]
    ])
    
    await message.answer(
        "4️⃣ <b>Email</b> (опционально)\n"
        "(Если хотите получать уведомления на почту. Нажмите 'Пропустить', если не нужен)",
        parse_mode="HTML",
        reply_markup=skip_kb
    )

@router.callback_query(F.data == "skip_email_partner")
async def skip_email(callback: Message, state: FSMContext):
    await state.update_data(email="Не указан")
    await state.set_state(PartnerForm.project)
    await callback.message.edit_text(
        "5️⃣ <b>Какой у вас проект/аудитория?</b>\n"
        "(Расскажите о себе: канал, сайт, сообщество, сфера деятельности)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.callback_query(F.data == "cancel_partner")
async def cancel_partner(callback: Message, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Заявка отменена.",
        reply_markup=client_main_menu()
    )

@router.message(PartnerForm.email)
async def process_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await state.set_state(PartnerForm.project)
    
    await message.answer(
        "5️⃣ <b>Какой у вас проект/аудитория?</b>\n"
        "(Расскажите о себе: канал, сайт, сообщество, сфера деятельности)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(PartnerForm.project)
async def process_project(message: Message, state: FSMContext):
    await state.update_data(project=message.text.strip())
    await state.set_state(PartnerForm.offer)
    
    await message.answer(
        "6️⃣ <b>Ваше предложение</b>\n"
        "(Что вы хотите взамен? Как видите сотрудничество?)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(PartnerForm.offer)
async def process_offer(message: Message, state: FSMContext):
    await state.update_data(offer=message.text.strip())
    await finish_partner(message, state)

async def finish_partner(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    description = (
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Telegram:</b> {data['username']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"📧 <b>Email:</b> {data['email']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Проект/Аудитория:</b>\n{data['project']}\n"
        f"💼 <b>Предложение:</b>\n{data['offer']}"
    )
    
    ticket = await db.create_ticket(
        user_id=message.from_user.id,
        channel="tg",
        type="partner",
        title="🤝 Стать партнером",
        description=description,
        budget=0
    )
    
    logger.info(f"[PARTNER] User {message.from_user.id} created partner ticket {ticket['ticket_number']}")
    
    await message.answer(
        SUCCESS_MESSAGE,
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    
    try:
        admin_msg = (
            f"🔔 <b>НОВАЯ ЗАЯВКА: {ticket['ticket_number']}</b>\n"
            f"🤝 Тип: Стать партнером\n\n"
            f"{description}\n\n"
            f"📅 {ticket['created_at']}"
        )
        target_chat = config.admin_group_id or config.ceo_group_id
        if target_chat:
            await message.bot.send_message(target_chat, admin_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
