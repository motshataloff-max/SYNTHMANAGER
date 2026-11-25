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

# ==========================================
# 1. БАЗОВЫЕ КОМАНДЫ
# ==========================================
@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_or_create_user(message.from_user)
    if not user.get('client_code'):
        code = await db.ensure_client_code(message.from_user.id)
        await message.answer(
            f"🎫 <b>Ваш код клиента:</b> <code>{code}</code>\n\n"
            f"💡 Используйте его в VK Mini App для входа.",
            parse_mode="HTML"
        )
    
    if message.from_user.id == config.owner_id:
        await message.answer("👑 <b>Добро пожаловать, босс!</b>", reply_markup=admin_main_menu(), parse_mode="HTML")
    else:
        await message.answer("👋 <b>Добро пожаловать в SYNTH!</b>", reply_markup=client_main_menu(), parse_mode="HTML")

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == config.owner_id:
        await message.answer("❌ Действие отменено.", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ Действие отменено.", reply_markup=client_main_menu())

# ==========================================
# 2. КНОПКА "ОТМЕНА"
# ==========================================
@router.message(F.text == "❌ Отмена")
async def cancel_button(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == config.owner_id:
        await message.answer("❌ Действие отменено.", reply_markup=admin_main_menu())
    else:
        await message.answer("❌ Действие отменено.", reply_markup=client_main_menu())

# ==========================================
# 3. АДМИНСКИЕ КНОПКИ
# ==========================================
@router.message(F.text == "📊 Статистика")
async def admin_stats_button(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id:
        return
    await state.clear()
    s = await db.general_stats()
    text = (
        f"<b>📊 Статистика SYNTH</b>\n"
        f"──────────────────────\n"
        f"👥 Клиентов: <b>{s['clients']}</b>\n"
        f"🎫 Активных тикетов: <b>{s['active_tickets']}</b>\n"
        f"🔒 Закрытых тикетов: <b>{s['closed_tickets']}</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=admin_main_menu())

@router.message(F.text == "👤 Режим клиента")
async def switch_to_client(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id:
        return
    await state.clear()
    await message.answer(
        "👤 <b>Вы переключились в режим клиента</b>\n\n"
        "Теперь вы видите клиентское меню.\n"
        "Для возврата в админку нажмите /start",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

# ==========================================
# 4. FALLBACK (ловит всё нераспознанное)
# ==========================================
@router.message(F.text, F.chat.type == "private")
async def catch_all_text(message: Message, state: FSMContext):
    if await state.get_state():
        return
    if message.from_user.id == config.owner_id:
        await message.answer("🤔 Используйте кнопки меню.", reply_markup=admin_main_menu())
    else:
        await message.answer("🤔 Используйте кнопки меню.", reply_markup=client_main_menu())
