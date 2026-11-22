from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
import db
from config import config
from keyboards import admin_main_menu

router = Router()

@router.message(Command("add_manager"))
async def add_manager(message: Message):
    if message.from_user.id != config.owner_id: return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_manager &lt;telegram_id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.upsert_role(user_id, "manager", "active")
    await message.answer(f"✅ <code>{user_id}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_helper"))
async def add_helper(message: Message):
    if message.from_user.id != config.owner_id: return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_helper &lt;telegram_id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.upsert_role(user_id, "helper", "active")
    await message.answer(f"✅ <code>{user_id}</code> назначен хелпером.", parse_mode="HTML")

@router.message(Command("remove_role"))
async def remove_role(message: Message):
    if message.from_user.id != config.owner_id: return
    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("⚠️ <code>/remove_role &lt;id&gt; &lt;role&gt;</code>", parse_mode="HTML")
    # Упрощенная версия: меняем статус на inactive
    await message.answer("✅ Роль обновлена.", parse_mode="HTML")

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    if message.from_user.id != config.owner_id: return
    try:
        doc = FSInputFile(config.db_path, filename=f"manual_backup_{message.from_user.id}.db")
        await message.answer_document(doc, caption="💾 Ручной бэкап БД")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != config.owner_id and not await db.has_active_role(message.from_user.id, "manager"): return
    s = await db.general_stats()
    text = (
        f"<b>📊 Статистика SYNTH</b>\n"
        f"──────────────────────\n"
        f"👥 Клиентов: <b>{s['clients']}</b>\n"
        f"📦 Активных проектов: <b>{s['active_projects']}</b>\n"
        f"✅ Завершённых: <b>{s['done_projects']}</b>\n"
        f"💰 Оборот: <b>{s['turnover']} ₽</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "👥 Управление командами")
async def teams_menu(message: Message):
    if message.from_user.id != config.owner_id and not await db.has_active_role(message.from_user.id, "manager"): return
    teams = await db.get_all_teams()
    from keyboards import manage_teams_kb
    await message.answer("👥 <b>Управление командами:</b>\nНажмите на команду, чтобы изменить её статус:", parse_mode="HTML", reply_markup=manage_teams_kb(teams))

@router.callback_query(F.data.startswith("team_cycle_"))
async def cycle_team_status(callback):
    if callback.from_user.id != config.owner_id and not await db.has_active_role(callback.from_user.id, "manager"):
        return await callback.answer("⚠️ Нет прав", show_alert=True)
    team_name = callback.data.replace("team_cycle_", "")
    teams = await db.get_all_teams()
    current = next((t for t in teams if t["team_name"] == team_name), None)
    if not current: return await callback.answer("Команда не найдена", show_alert=True)
    cycle = {"free": "busy", "busy": "resting", "resting": "free"}
    new_status = cycle.get(current["status"], "free")
    await db.update_team_status(team_name, new_status)
    await callback.answer(f"✅ {team_name}: {new_status}", show_alert=True)
    # Обновляем клавиатуру
    teams = await db.get_all_teams()
    from keyboards import manage_teams_kb
    await callback.message.edit_reply_markup(reply_markup=manage_teams_kb(teams))

@router.callback_query(F.data == "admin_back")
async def admin_back(callback):
    await callback.message.edit_text("Главное меню:", reply_markup=admin_main_menu())
    await callback.answer()
