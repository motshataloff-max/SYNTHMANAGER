import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
from keyboards import client_main_menu, admin_main_menu
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_or_create_user(message.from_user)
    if not user.get('client_code'):
        code = await db.ensure_client_code(message.from_user.id)
        await message.answer(f"🎫 Ваш код клиента: <code>{code}</code>\nИспользуйте его в VK Mini App.", parse_mode="HTML")
    if message.from_user.id == config.owner_id:
        await message.answer("👑 <b>Меню CEO:</b>", reply_markup=admin_main_menu(), parse_mode="HTML")
    else:
        await message.answer("👋 <b>Добро пожаловать в SYNTH!</b>", reply_markup=client_main_menu(), parse_mode="HTML")

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == config.owner_id:
        await message.answer("❌ Действие отменено.", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ Действие отменено.", reply_markup=client_main_menu())

@router.message(F.text == "❌ Отмена")
async def cancel_button(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == config.owner_id:
        await message.answer("❌ Действие отменено.", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ Действие отменено.", reply_markup=client_main_menu())

@router.message(F.text, F.chat.type == "private")
async def catch_all_text(message: Message, state: FSMContext):
    if await state.get_state(): return
    if message.from_user.id == config.owner_id:
        await message.answer("🤔 Используйте кнопки меню.", reply_markup=admin_main_menu())
    else:
        await message.answer("🤔 Используйте кнопки меню.", reply_markup=client_main_menu())
