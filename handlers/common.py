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
# АБСОЛЮТНЫЙ СБРОС (РАБОТАЕТ ИЗ ЛЮБОГО МЕСТА)
# ==========================================
@router.message(CommandStart() | F.text == "🏠 Главное меню" | F.text == "🔙 Главное меню" | F.text == "🔙 Главное меню (Клиент)")
async def force_main_menu(message: Message, state: FSMContext):
    # 1. Убиваем любое текущее состояние (форму)
    await state.clear()
    
    # 2. Определяем, какое меню показать
    is_admin = (message.from_user.id == config.owner_id) or await db.has_active_role(message.from_user.id, "manager")
    kb = admin_main_menu() if is_admin else client_main_menu()
    
    # 3. Определяем текст приветствия
    if message.from_user.id == config.owner_id:
        text = "👑 <b>Добро пожаловать, босс!</b>\n\n" + texts.BOSS_COMMANDS if hasattr(texts, 'BOSS_COMMANDS') else "👑 <b>Панель CEO</b>"
    elif is_admin:
        text = "💼 <b>Панель менеджера</b>"
    else:
        text = texts.WELCOME + "\n\n📌 <b>Выберите действие в меню ниже 👇</b>"
        
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(Command("cancel") | F.text == "❌ Отмена")
async def force_cancel(message: Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == config.owner_id) or await db.has_active_role(message.from_user.id, "manager")
    kb = admin_main_menu() if is_admin else client_main_menu()
    await message.answer("❌ Действие отменено. Возврат в главное меню.", reply_markup=kb)

# ==========================================
# ОБЫЧНЫЕ КНОПКИ МЕНЮ (ЕСЛИ СОСТОЯНИЕ CLEAR)
# ==========================================
@router.message(F.text == "🛒 Заказать разработку")
async def menu_order(message: Message, state: FSMContext):
    await state.set_state(ClientForm.title)
    await message.answer(texts.CLIENT_ASK_TITLE, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "👨‍💻 Стать разработчиком")
async def menu_dev(message: Message, state: FSMContext):
    await state.set_state(DevForm.name)
    await message.answer(texts.DEV_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "🤝 Стать партнёром")
async def menu_partner(message: Message, state: FSMContext):
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
    await message.answer(texts.PR_LINK_TEXT.format(link=link), parse_mode="HTML", reply_markup=client_main_menu())

@router.message(F.text == "ℹ️ О нас")
async def about(message: Message, state: FSMContext):
    await state.clear()
    about_text = await db.get_setting("about")
    await message.answer(about_text or "🇷🇺 SYNTH — российская команда разработчиков. Работаем с РФ и дружественными странами.", parse_mode="HTML", reply_markup=client_main_menu())
