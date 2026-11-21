import os, sys, logging
from datetime import datetime
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

import db
from config import config
from keyboards import main_menu, admin_menu, managers_list_kb, assign_team_kb, manage_teams_kb
from states import BroadcastForm

logger = logging.getLogger(__name__)
router = Router()

async def is_admin(user_id: int) -> bool:
    return user_id == config.owner_id or await db.has_active_role(user_id, "manager")

async def is_ceo(user_id: int) -> bool:
    return user_id == config.owner_id

@router.message(BroadcastForm.waiting_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        return await message.answer("❌ Рассылка отменена.", reply_markup=admin_menu())
    
    text_to_send = message.text or message.caption or "Сообщение без текста"
    await state.clear()
    await message.answer("⏳ <b>Начинаю рассылку...</b>", parse_mode="HTML")
    
    users = await db.get_all_users()
    success, failed = 0, 0
    for uid in users:
        try:
            if message.photo: await bot.send_photo(uid, message.photo[-1].file_id, caption=text_to_send)
            elif message.document: await bot.send_document(uid, message.document.file_id, caption=text_to_send)
            else: await bot.send_message(uid, text_to_send)
            success += 1
        except Exception: failed += 1
            
    await message.answer(f"✅ <b>Рассылка завершена!</b>\n📤 Доставлено: {success}\n❌ Ошибок: {failed}", parse_mode="HTML", reply_markup=admin_menu())

@router.callback_query(F.data.startswith("team_cycle_"))
async def cycle_team_status(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id): return await callback.answer()
    team_name = callback.data.split("_")[2]
    teams = await db.get_all_teams()
    current = next((t["status"] for t in teams if t["team_name"] == team_name), "free")
    cycle = {"free": "busy", "busy": "resting", "resting": "incomplete", "incomplete": "free"}
    new_status = cycle.get(current, "free")
    
    await db.update_team_status(team_name, new_status)
    await callback.message.edit_text(f"✅ Статус <b>{team_name}</b> изменен на: <b>{new_status}</b>", parse_mode="HTML", reply_markup=manage_teams_kb(await db.get_all_teams()))
    await callback.answer()

@router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id): return await callback.answer()
    await callback.message.edit_text("Админ-панель:", reply_markup=admin_menu())
    await callback.answer()

@router.callback_query(F.data.startswith("proj_assign_"))
async def start_assign_team(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return await callback.answer()
    project_id = int(callback.data.split("_")[2])
    await state.update_data(project_id=project_id)
    teams = await db.get_all_teams()
    await callback.message.edit_text(f"⚙️ <b>Выберите команду для проекта #{project_id}:</b>", parse_mode="HTML", reply_markup=assign_team_kb(teams))
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
        return await callback.message.edit_text(f"⚠️ Для команды <b>{team_name}</b> не указан ID чата!", parse_mode="HTML")

    project = await db.get_project(project_id)
    notification = f"🔥 <b>Новый проект для команды {team_name}!</b>\n\n📌 <b>ID:</b> #{project_id}\n📝 <b>ТЗ:</b> {project['title']}\n{project['description']}\n💰 <b>Бюджет:</b> {project['budget']} ⭐\n📞 <b>Контакт:</b> {project['contact_info']}"
    
    try:
        await bot.send_message(team_chat_id, notification, parse_mode="HTML")
        invite_link = None
        try:
            link_obj = await bot.create_chat_invite_link(chat_id=team_chat_id, creates_join_request=False)
            invite_link = link_obj.invite_link
        except Exception: pass

        await db.update_team_status(team_name, "busy")
        await db.set_project_status(project_id, "assigned", team_name=team_name)
        await callback.message.edit_text(f"✅ Проект #{project_id} передан в <b>{team_name}</b>.", parse_mode="HTML")
        
        client_msg = f"✅ <b>Проект #{project_id} передан в работу!</b>\nКоманда <b>{team_name}</b> изучает ТЗ.\n\n"
        if invite_link:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Войти в чат с командой", url=invite_link)]])
            await bot.send_message(project["client_id"], client_msg + "Нажмите кнопку, чтобы присоединиться к чату:", parse_mode="HTML", reply_markup=kb)
        else:
            await bot.send_message(project["client_id"], client_msg + "Менеджер скоро свяжется с вами.", parse_mode="HTML")
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

@router.message(Command("complete"))
async def complete_project(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return await message.answer("⚠️ <code>/complete &lt;id&gt;</code>", parse_mode="HTML")
    
    project_id = int(parts[1])
    project = await db.get_project(project_id)
    if not project: return await message.answer("Проект не найден.")
    if project["status"] == "done": return await message.answer("Проект уже завершён.")

    budget = project["budget"]
    company_share = budget * 20 // 100
    await db.add_company_delta(company_share, "project_completion", project_id)
    
    if project["referrer_id"] and budget >= 500:
        new_discount = await db.increment_discount_by_user_id(project["referrer_id"])
        try: await bot.send_message(project["referrer_id"], f"🎉 Реферал завершил проект #{project_id}!\nВаша скидка теперь: <b>{new_discount}%</b>", parse_mode="HTML")
        except Exception: pass

    await db.set_project_status(project_id, "done")
    if project.get("assigned_team"): await db.update_team_status(project["assigned_team"], "free")
    await message.answer(f"✅ Проект #{project_id} завершён. Компания получила {company_share} ⭐.")

@router.message(Command("add_manager"))
async def add_manager(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return
    await db.upsert_role(int(parts[1]), "manager", "active")
    await message.answer(f"✅ <code>{parts[1]}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_helper"))
async def add_helper(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return
    await db.upsert_role(int(parts[1]), "helper", "active")
    await message.answer(f"✅ <code>{parts[1]}</code> назначен хелпером.", parse_mode="HTML")

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
        await message.answer("✅ Бэкап отправлен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
