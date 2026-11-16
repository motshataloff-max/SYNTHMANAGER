import os
import sys
import logging
from datetime import datetime

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile

import db
from config import config
from keyboards import main_menu, admin_menu, managers_list_kb, assign_team_kb, manage_teams_kb

logger = logging.getLogger(__name__)
router = Router()

class BroadcastForm(StatesGroup):
    waiting_message = State()

async def is_admin(user_id: int) -> bool:
    return user_id == config.owner_id or await db.has_active_role(user_id, "manager")

async def is_ceo(user_id: int) -> bool:
    return user_id == config.owner_id

# ==========================================
# ГЛОБАЛЬНАЯ РАССЫЛКА
# ==========================================
@router.message(Command("broadcast"))
@router.message(F.text == "📢 Глобальная рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    if not await is_ceo(message.from_user.id): return
    await state.set_state(BroadcastForm.waiting_message)
    await message.answer("📢 <b>Режим рассылки активирован.</b>\n\nОтправьте текст или перешлите сообщение, которое нужно разослать всем пользователям бота.\nДля отмены нажмите /cancel", parse_mode="HTML")

@router.message(BroadcastForm.waiting_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        return await message.answer("❌ Рассылка отменена.", reply_markup=admin_menu())
    
    text_to_send = message.text or message.caption or "Сообщение без текста"
    await state.clear()
    
    await message.answer("⏳ <b>Начинаю рассылку...</b> Это может занять некоторое время.", parse_mode="HTML")
    
    users = await db.get_all_users()
    success = 0
    failed = 0
    
    for uid in users:
        try:
            if message.photo:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=text_to_send)
            elif message.document:
                await bot.send_document(uid, message.document.file_id, caption=text_to_send)
            else:
                await bot.send_message(uid, text_to_send)
            success += 1
        except Exception:
            failed += 1
            
    await message.answer(f"✅ <b>Рассылка завершена!</b>\n\n📤 Доставлено: {success}\n❌ Ошибок (бот заблокирован): {failed}", parse_mode="HTML", reply_markup=admin_menu())

# ==========================================
# УПРАВЛЕНИЕ КОМАНДАМИ (CEO)
# ==========================================
@router.message(F.text == "👥 Управление командами")
async def manage_teams_btn(message: Message):
    if not await is_ceo(message.from_user.id): return
    teams = await db.get_all_teams()
    await message.answer("👥 <b>Управление статусами команд:</b>\nНажмите на команду, чтобы изменить её статус.", parse_mode="HTML", reply_markup=manage_teams_kb(teams))

@router.callback_query(F.data.startswith("team_cycle_"))
async def cycle_team_status(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id): return await callback.answer()
    team_name = callback.data.split("_")[2]
    teams = await db.get_all_teams()
    current = next((t["status"] for t in teams if t["team_name"] == team_name), "free")
    
    # Цикл статусов: free -> busy -> resting -> incomplete -> free
    cycle = {"free": "busy", "busy": "resting", "resting": "incomplete", "incomplete": "free"}
    new_status = cycle.get(current, "free")
    
    await db.update_team_status(team_name, new_status)
    await callback.message.edit_text(f"✅ Статус команды <b>{team_name}</b> изменен на: <b>{new_status}</b>", parse_mode="HTML", reply_markup=manage_teams_kb(await db.get_all_teams()))
    await callback.answer()

@router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id): return await callback.answer()
    await callback.message.edit_text("Админ-панель:", reply_markup=admin_menu())
    await callback.answer()

# ==========================================
# НАЗНАЧЕНИЕ ПРОЕКТА НА КОМАНДУ (МЕНЕДЖЕР)
# ==========================================
@router.callback_query(F.data.startswith("proj_assign_"))
async def start_assign_team(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return await callback.answer()
    project_id = int(callback.data.split("_")[2])
    await state.update_data(project_id=project_id)
    
    teams = await db.get_all_teams()
    await callback.message.edit_text(
        f"⚙️ <b>Выберите команду для проекта #{project_id}:</b>\n"
        f"🟢 Свободна | 🔴 Занята | 🟡 Отдыхает | ⚪ Неполная", 
        parse_mode="HTML", 
        reply_markup=assign_team_kb(teams)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("assign_team_"))
async def confirm_assign_team(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not await is_admin(callback.from_user.id): return await callback.answer()
    team_name = callback.data.split("_")[2]
    data = await state.get_data()
    project_id = data["project_id"]
    await state.clear()

    # Получаем chat_id команды из БД
    teams = await db.get_all_teams()
    team_chat_id = next((t["chat_id"] for t in teams if t["team_name"] == team_name), None)
    
    if not team_chat_id or team_chat_id == 0:
        return await callback.message.edit_text(f"⚠️ Для команды <b>{team_name}</b> не указан ID чата! CEO должен настроить команды.", parse_mode="HTML")

    # Пересылаем проект в чат команды
    project = await db.get_project(project_id)
    notification = (
        f"🔥 <b>Новый проект для команды {team_name}!</b>\n\n"
        f"📌 <b>ID:</b> #{project_id}\n"
        f"📝 <b>ТЗ:</b> {project['title']}\n{project['description']}\n"
        f"💰 <b>Бюджет:</b> {project['budget']} ⭐\n"
        f"📞 <b>Контакт клиента:</b> {project['contact_info']}\n\n"
        f"<i>Менеджер назначил вас. Обсудите детали и напишите менеджеру, если есть вопросы.</i>"
    )
    
    try:
        await bot.send_message(team_chat_id, notification, parse_mode="HTML")
        # Меняем статус команды на "Занята" и статус проекта
        await db.update_team_status(team_name, "busy")
        await db.set_project_status(project_id, "assigned", team_name=team_name)
        
        await callback.message.edit_text(f"✅ Проект #{project_id} передан в команду <b>{team_name}</b>.\nКоманда помечена как 🔴 Занята.", parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка отправки в чат команды: {e}", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "assign_cancel")
async def cancel_assign(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Назначение отменено.")
    await callback.answer()

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer("Эта команда сейчас недоступна.", show_alert=True)

# ==========================================
# УМНАЯ ПОДДЕРЖКА (ОТВЕТ В ГРУППЕ)
# ==========================================
@router.message(F.chat.id == config.support_group_id & F.reply_to_message)
async def support_reply_in_group(message: Message, bot: Bot):
    """Если хелпер отвечает на сообщение в группе поддержки, бот пересылает ответ клиенту."""
    if not await is_admin(message.from_user.id) and not await db.has_active_role(message.from_user.id, "helper"):
        return # Отвечать могут только админы и хелперы

    reply_msg = message.reply_to_message
    # Проверяем, что это пересланное от бота сообщение (обычно бот пишет "От: ...")
    if not reply_msg or not reply_msg.from_user or reply_msg.from_user.id != bot.id:
        return

    # Пытаемся вытащить ID пользователя из текста пересланного сообщения
    # Формат был: "🆘 Новый тикет... От: ... (123456789)"
    text = reply_msg.text or reply_msg.caption or ""
    import re
    match = re.search(r"\((\d{5,15})\)", text)
    if not match:
        return await message.answer("⚠️ Не удалось найти ID пользователя в исходном сообщении.")
    
    user_id = int(match.group(1))
    
    try:
        await bot.send_message(user_id, f"💬 <b>Ответ поддержки SYNTH:</b>\n\n{message.text}", parse_mode="HTML")
        await message.answer(f"✅ Ответ доставлен пользователю <code>{user_id}</code>.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

# ==========================================
# СТАРЫЕ КОМАНДЫ (ОСТАВЛЕНЫ ДЛЯ СОВМЕСТИМОСТИ)
# ==========================================
@router.message(Command("msg"))
async def cmd_msg(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id): return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/msg &lt;user_id&gt; &lt;текст&gt;</code>", parse_mode="HTML")
    try:
        await bot.send_message(int(parts[1]), f"💬 <b>Сообщение от SYNTH:</b>\n\n{parts[2]}", parse_mode="HTML")
        await message.answer(f"✅ Доставлено пользователю <code>{parts[1]}</code>.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("add_manager"))
async def add_manager(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return
    await db.upsert_role(int(parts[1]), "manager", "active")
    await message.answer(f"✅ Пользователь <code>{parts[1]}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_helper"))
async def add_helper(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return
    await db.upsert_role(int(parts[1]), "helper", "active")
    await message.answer(f"✅ Пользователь <code>{parts[1]}</code> назначен хелпером.", parse_mode="HTML")

@router.message(Command("restart_bot"))
async def restart_bot(message: Message):
    if not await is_ceo(message.from_user.id): return
    await message.answer("🔄 Перезапуск...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    if not await is_ceo(message.from_user.id): return
    try:
        doc = FSInputFile(db.DB_PATH)
        await message.bot.send_document(config.ping_chat_id, document=doc, caption=f"📦 Бэкап БД {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        await message.answer("✅ Бэкап отправлен в канал!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
