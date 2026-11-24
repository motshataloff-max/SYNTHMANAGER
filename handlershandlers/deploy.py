"""
SYNTH Platform v2.0 - Обработчики: Поднять код на сервера
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

import db
from states import DeployForm
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

@router.message(F.text == "🚀 Поднять код на сервера")
async def start_deploy(message: Message, state: FSMContext):
    logger.info(f"[DEPLOY] User {message.from_user.id} started deploy flow")
    await state.clear()
    await state.set_state(DeployForm.name)
    await message.answer(
        f"🚀 <b>Поднять код на сервера</b>\n\n{WARNING_START}\n\n"
        "1️⃣ <b>Как к вам обращаться?</b>\n(Введите ваше имя или никнейм)",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(DeployForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(DeployForm.username)
    
    current_un = message.from_user.username
    hint = f"\n\n💡 Ваш текущий юзернейм: @{current_un}" if current_un else ""
    
    await message.answer(
        f"2️⃣ <b>Ваш Telegram username</b>{hint}\n"
        "(Например: @ivan_dev). Это обязательно для связи!",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(DeployForm.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    await state.update_data(username=f"@{username}")
    await state.set_state(DeployForm.phone)
    
    await message.answer(
        "3️⃣ <b>Ваш номер телефона</b>\n"
        "(Например: +7 999 123-45-67). Обязательно для оперативной связи!",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

@router.message(DeployForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(DeployForm.repo)
    
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_repo_deploy")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_deploy")]
    ])
    
    await message.answer(
        "4️⃣ <b>Ссылка на код</b> (опционально)\n"
        "(GitHub или другой репозиторий. Если нет, нажмите 'Пропустить')",
        parse_mode="HTML",
        reply_markup=skip_kb
    )

@router.callback_query(F.data == "skip_repo_deploy")
async def skip_repo(callback: Message, state: FSMContext):
    await state.update_data(repo="Нет")
    await state.set_state(DeployForm.hosting)
    await callback.message.edit_text(
        "5️⃣ <b>Какой хостинг нужен?</b>\n"
        "Выберите вариант:",
        parse_mode="HTML",
        reply_markup=hosting_kb()
    )

@router.callback_query(F.data == "cancel_deploy")
async def cancel_deploy(callback: Message, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Заявка отменена.",
        reply_markup=client_main_menu()
    )

@router.message(DeployForm.repo)
async def process_repo(message: Message, state: FSMContext):
    await state.update_data(repo=message.text.strip())
    await state.set_state(DeployForm.hosting)
    
    await message.answer(
        "5️⃣ <b>Какой хостинг нужен?</b>\n"
        "Выберите вариант:",
        parse_mode="HTML",
        reply_markup=hosting_kb()
    )

def hosting_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚂 Railway", callback_data="hosting_Railway")],
        [InlineKeyboardButton(text="💻 VPS (свой сервер)", callback_data="hosting_VPS")],
        [InlineKeyboardButton(text="🌐 Другой хостинг", callback_data="hosting_Другой")],
        [InlineKeyboardButton(text="❓ Не знаю", callback_data="hosting_Не знаю")]
    ])

@router.callback_query(F.data.startswith("hosting_"))
async def select_hosting(callback: Message, state: FSMContext):
    hosting = callback.data.replace("hosting_", "")
    await state.update_data(hosting=hosting)
    await state.set_state(DeployForm.domain)
    
    await callback.message.edit_text(
        "6️⃣ <b>Есть ли домен?</b>\n"
        "Выберите вариант:",
        parse_mode="HTML",
        reply_markup=domain_kb()
    )

def domain_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, есть", callback_data="domain_Да")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="domain_Нет")]
    ])

@router.callback_query(F.data.startswith("domain_"))
async def select_domain(callback: Message, state: FSMContext):
    domain = callback.data.replace("domain_", "")
    await state.update_data(domain=domain)
    await state.set_state(DeployForm.requirements)
    
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_requirements_deploy")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_deploy")]
    ])
    
    await callback.message.edit_text(
        "7️⃣ <b>Дополнительные требования</b> (опционально)\n"
        "(Особые настройки, SSL, базы данных и т.д. Если нет, нажмите 'Пропустить')",
        parse_mode="HTML",
        reply_markup=skip_kb
    )

@router.callback_query(F.data == "skip_requirements_deploy")
async def skip_requirements(callback: Message, state: FSMContext):
    await state.update_data(requirements="Нет")
    await finish_deploy(callback.message, state)

@router.message(DeployForm.requirements)
async def process_requirements(message: Message, state: FSMContext):
    await state.update_data(requirements=message.text.strip())
    await finish_deploy(message, state)

async def finish_deploy(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    description = (
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Telegram:</b> {data['username']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Репозиторий:</b> {data['repo']}\n"
        f"🖥️ <b>Хостинг:</b> {data['hosting']}\n"
        f"🌐 <b>Домен:</b> {data['domain']}\n"
        f"💬 <b>Доп. требования:</b> {data['requirements']}"
    )
    
    ticket = await db.create_ticket(
        user_id=message.from_user.id,
        channel="tg",
        type="deploy",
        title="🚀 Поднять код на сервера",
        description=description,
        budget=0
    )
    
    logger.info(f"[DEPLOY] User {message.from_user.id} created deploy ticket {ticket['ticket_number']}")
    
    await message.answer(
        SUCCESS_MESSAGE,
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )
    
    try:
        admin_msg = (
            f"🔔 <b>НОВАЯ ЗАЯВКА: {ticket['ticket_number']}</b>\n"
            f"🚀 Тип: Поднять код на сервера\n\n"
            f"{description}\n\n"
            f"📅 {ticket['created_at']}"
        )
        target_chat = config.admin_group_id or config.ceo_group_id
        if target_chat:
            await message.bot.send_message(target_chat, admin_msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")
