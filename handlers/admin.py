import os
import sys
import logging
from datetime import datetime

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

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
@router.callback_query(F.data.startswith("team_cycle_"))
async def cycle_team_status(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id): return await callback.answer()
    team_name = callback.data.split("_")[2]
    teams = await db.get_all_teams()
    current = next((t["status"] for t in teams if t["team_name"] == team_name), "free")
    
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

    teams = await db.get_all_teams()
    team_chat_id = next((t["chat_id"] for t in teams if t["team_name"] == team_name), None)
    
    if not team_chat_id or team_chat_id == 0:
        return await callback.message.edit_text(f"⚠️ Для команды <b>{team_name}</b> не указан ID чата! CEO должен настроить команды.", parse_mode="HTML")

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
        # 1. Отправляем в чат команды
        await bot.send_message(team_chat_id, notification, parse_mode="HTML")
        
        # 2. Генерируем ссылку-приглашение для клиента
        invite_link = None
        try:
            link_obj = await bot.create_chat_invite_link(chat_id=team_chat_id, creates_join_request=False)
            invite_link = link_obj.invite_link
        except Exception as e:
            logger.error(f"Не удалось создать ссылку-приглашение: {e}")

        # 3. Меняем статусы в БД
        await db.update_team_status(team_name, "busy")
        await db.set_project_status(project_id, "assigned", team_name=team_name)
        
        await callback.message.edit_text(f"✅ Проект #{project_id} передан в команду <b>{team_name}</b>.\nКоманда помечена как 🔴 Занята.", parse_mode="HTML")
        
        # 4. Отправляем клиенту уведомление и ссылку
        client_id = project["client_id"]
        client_msg = f"✅ <b>Ваш проект #{project_id} передан в работу!</b>\n\n"
        client_msg += f"Команда <b>{team_name}</b> уже изучает ваше ТЗ.\n\n"
        if invite_link:
            client_msg += f"🔗 <b>Мы добавили вас в закрытый чат с разработчиками.</b>\nНажмите кнопку ниже, чтобы присоединиться и обсуждать детали напрямую:"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Войти в чат с командой", url=invite_link)]])
            await bot.send_message(client_id, client_msg, parse_mode="HTML", reply_markup=kb)
        else:
            client_msg += "Менеджер скоро свяжется с вами для уточнения деталей."
            await bot.send_message(client_id, client_msg, parse_mode="HTML")
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}", parse_mode="HTML")
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
# УПРАВЛЕНИЕ ПРОЕКТАМИ И СТАТУСАМИ
# ==========================================
@router.message(Command("complete"))
async def complete_project(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/complete &lt;project_id&gt;</code>", parse_mode="HTML")
    
    project_id = int(parts[1])
    project = await db.get_project(project_id)
    if not project: return await message.answer("Проект не найден.")

    if message.from_user.id != config.owner_id:
        if project["status"] in ["assigned", "in_progress", "in_team_heavy", "in_team_medium", "in_team_fast"]:
            return await message.answer("⛔ Этот проект уже в работе. Завершить его может только CEO.")

    if project["status"] == "done":
        return await message.answer("Проект уже завершён.")

    budget = project["budget"]
    company_share = budget * 20 // 100
    await db.add_company_delta(company_share, "project_completion", project_id)
    
    # ПРОВЕРКА РЕФЕРАЛЬНОЙ СИСТЕМЫ (15% от 500 ⭐)
    if project["referrer_id"] and budget >= 500:
        new_discount = await db.increment_discount_by_user_id(project["referrer_id"])
        try:
            await bot.send_message(
                project["referrer_id"], 
                f"🎉 Ваш реферал завершил проект #{project_id} на сумму {budget} ⭐!\nВаша скидка теперь: <b>{new_discount}%</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await db.set_project_status(project_id, "done")
    
    # Освобождаем команду, если она была назначена
    if project.get("assigned_team"):
        await db.update_team_status(project["assigned_team"], "free")
        
    await message.answer(f"✅ Проект #{project_id} завершён. Компания получила {company_share} ⭐. Команда освобождена.")

@router.message(Command("status"))
async def set_status(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/status &lt;id&gt; done|unpaid|new|delete</code>", parse_mode="HTML")
    
    project_id = int(parts[1])
    value = parts[2].lower()
    project = await db.get_project(project_id)
    
    if message.from_user.id != config.owner_id and project and project["status"] in ["assigned", "in_progress", "in_team_heavy", "in_team_medium", "in_team_fast"]:
        return await message.answer("⛔ Проект в работе. Изменение статуса доступно только CEO.")

    if value == "delete":
        await db.delete_project(project_id)
        return await message.answer(f"🗑 Проект #{project_id} полностью удалён из базы данных.")
    
    await db.set_project_status(project_id, value)
    await message.answer(f"✅ Статус проекта #{project_id} изменён на: <b>{value}</b>", parse_mode="HTML")

# ==========================================
# ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ CEO
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
