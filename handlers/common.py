from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import texts
from keyboards import client_main_menu, admin_main_menu, cancel_kb
from states import ClientForm, DevForm, PartnerForm
from config import config

router = Router()

# ==========================================
# ТЕКСТЫ МЕНЮ
# ==========================================
USER_COMMANDS = (
    "📌 <b>Что я умею:</b>\n\n"
    "• 🛒 <b>Заказать разработку</b>\n"
    "• 👨‍💻 <b>Стать разработчиком</b>\n"
    "• 🤝 <b>Стать партнёром</b>\n"
    "• 🔗 <b>Моя реферальная ссылка</b>\n"
    "• 📂 <b>Мои заявки</b>\n"
    "• 🔍 <b>Проверить статус заявки</b>\n"
    "• ℹ️ <b>О нас</b>\n"
    "• 🆘 <b>Поддержка</b>"
)

MANAGER_COMMANDS = (
    "💼 <b>Меню менеджера:</b>\n\n"
    "• 📋 <b>Все заявки (Тикеты)</b>\n"
    "• 👥 <b>Управление командами</b>\n"
    "• 👨‍💻 <b>Разработчики</b>\n"
    "• 🛡️ <b>Модерация</b>\n"
    "• 📊 <b>Статистика</b>\n"
    "• 🚫 <b>Баны</b>"
)

BOSS_COMMANDS = (
    "👑 <b>Меню CEO:</b>\n\n"
    "👥 <b>Персонал:</b>\n"
    "• <code>/add_manager &lt;id&gt;</code>\n"
    "• <code>/add_helper &lt;id&gt;</code>\n"
    "• <code>/ban &lt;id&gt;</code>\n"
    "• <code>/unban &lt;id&gt;</code>\n\n"
    "⚙️ <b>Система:</b>\n"
    "• <code>/backup_db</code>\n"
    "• <code>/restart_bot</code>"
)

async def _welcome_text(uid: int) -> str:
    if uid == config.owner_id:
        return "👑 <b>Добро пожаловать, босс!</b>\n\n" + BOSS_COMMANDS
    if await db.has_active_role(uid, "manager"):
        return "💼 <b>Добро пожаловать, менеджер!</b>\n\n" + MANAGER_COMMANDS
    return texts.WELCOME + "\n\n" + USER_COMMANDS

async def _welcome_kb(uid: int):
    if uid == config.owner_id or await db.has_active_role(uid, "manager"):
        return admin_main_menu()
    return client_main_menu()

# ==========================================
# БАЗОВЫЕ КОМАНДЫ
# ==========================================
@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    await state.clear()
    await db.get_or_create_user(message.from_user)
    await message.answer(await _welcome_text(message.from_user.id), reply_markup=await _welcome_kb(message.from_user.id), parse_mode="HTML")

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=await _welcome_kb(message.from_user.id))

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(await _welcome_text(message.from_user.id), parse_mode="HTML", reply_markup=await _welcome_kb(message.from_user.id))

# ==========================================
# КНОПКИ ГЛАВНОГО МЕНЮ (БЕЗОПАСНЫЕ ФИЛЬТРЫ)
# ==========================================
@router.message(F.text.in_({"🔙 Главное меню", "🔙 Главное меню (Клиент)"}))
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=await _welcome_kb(message.from_user.id))

@router.message(F.text == "🛒 Заказать разработку")
async def menu_order(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ClientForm.title)
    await message.answer(texts.CLIENT_ASK_TITLE, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "👨‍💻 Стать разработчиком")
async def menu_dev(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "dev")
    if role and role["status"] == "active":
        return await message.answer(f"✅ Вы уже разработчик. Уровень: <b>{role['level']}</b>.", parse_mode="HTML")
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на модерации.")
    await state.set_state(DevForm.name)
    await message.answer(texts.DEV_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "🤝 Стать партнёром")
async def menu_partner(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "partner")
    if role and role["status"] == "active":
        return await message.answer("✅ Вы уже партнёр SYNTH.")
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на рассмотрении у CEO.")
    await state.set_state(PartnerForm.name)
    await message.answer(texts.PARTNER_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text.in_({"🔗 Моя реферальная ссылка", "🔗 Моя ссылка на скидку"}))
async def menu_ref_link(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    await db.get_or_create_user(message.from_user)
    code = f"ref_{uid}"
    await db.set_ref_code(uid, code)
    link = f"https://t.me/{config.bot_username}?start={code}"
    await message.answer(texts.PR_LINK_TEXT.format(link=link), parse_mode="HTML")

@router.message(F.text == "ℹ️ О нас")
async def about(message: Message, state: FSMContext):
    await state.clear()
    about_text = await db.get_setting("about")
    await message.answer(about_text or "🇷🇺 SYNTH — российская команда разработчиков.", parse_mode="HTML")

# ==========================================
# УМНАЯ ЛОВУШКА (FALLBACK)
# ==========================================
@router.message(F.text)
async def catch_all_text(message: Message, state: FSMContext):
    """Если сообщение не попало ни в один обработчик выше"""
    current_state = await state.get_state()
    if current_state:
        await message.answer("⚠️ Сейчас я не могу обработать этот ввод. Нажмите '❌ Отмена' и попробуйте снова.", reply_markup=cancel_kb())
        return

    await message.answer(
        "🤔 Я не распознал команду. Пожалуйста, используйте кнопки меню ниже 👇",
        reply_markup=await _welcome_kb(message.from_user.id)
    )
