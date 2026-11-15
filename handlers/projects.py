import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import AssignForm

logger = logging.getLogger(__name__)
router = Router()

async def _is_admin(user_id: int) -> bool:
    return user_id == config.owner_id or await db.has_active_role(user_id, "manager")

def _parse_uid(text: str) -> int | None:
    raw = text.strip()
    return int(raw) if raw.isdigit() else None

async def _notify(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception:
        pass

# ==========================================
# НАЗНАЧЕНИЕ КОМАНДЫ (/assign)
# ==========================================

@router.message(Command("assign"))
async def assign_start(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/assign &lt;project_id&gt;</code>", parse_mode="HTML")
    
    project_id = int(parts[1])
    project = await db.get_project(project_id)
    if not project:
        return await message.answer("❌ Проект не найден.")
    if project["status"] == "done":
        return await message.answer("⚠️ Проект уже завершён.")

    await state.update_data(project_id=project_id)
    await state.set_state(AssignForm.senior)
    await message.answer(
        f"📌 <b>Назначение команды на проект #{project_id}</b>\n\n"
        f"1/3 — Введите числовой ID <b>Senior</b> разработчика:",
        parse_mode="HTML"
    )

@router.message(AssignForm.senior)
async def assign_senior(message: Message, state: FSMContext):
    uid = _parse_uid(message.text)
    if not uid:
        return await message.answer("⚠️ Введите числовой Telegram ID.")
    if not await db.has_active_role(uid, "dev"):
        return await message.answer("⚠️ Этот пользователь не является активным разработчиком.")
    
    await state.update_data(senior=uid)
    await state.set_state(AssignForm.medium1)
    await message.answer("2/3 — Введите числовой ID <b>первого Medium</b>:", parse_mode="HTML")

@router.message(AssignForm.medium1)
async def assign_medium1(message: Message, state: FSMContext):
    uid = _parse_uid(message.text)
    if not uid:
        return await message.answer("⚠️ Введите числовой Telegram ID.")
    if not await db.has_active_role(uid, "dev"):
        return await message.answer("⚠️ Этот пользователь не является активным разработчиком.")
    
    data = await state.get_data()
    if uid == data.get("senior"):
        return await message.answer("⚠️ Этот пользователь уже назначен Senior. Введите другого.")
    
    await state.update_data(medium1=uid)
    await state.set_state(AssignForm.medium2)
    await message.answer("3/3 — Введите числовой ID <b>второго Medium</b>:", parse_mode="HTML")

@router.message(AssignForm.medium2)
async def assign_medium2(message: Message, state: FSMContext, bot: Bot):
    uid = _parse_uid(message.text)
    if not uid:
        return await message.answer("⚠️ Введите числовой Telegram ID.")
    if not await db.has_active_role(uid, "dev"):
        return await message.answer("⚠️ Этот пользователь не является активным разработчиком.")
    
    data = await state.get_data()
    if uid in (data.get("senior"), data.get("medium1")):
        return await message.answer("⚠️ Этот пользователь уже назначен. Введите другого.")
    
    await state.clear()
    project_id = data["project_id"]

    # Сохраняем команду в БД (Senior 30%, Medium1 25%, Medium2 25%)
    members = [
        (data["senior"], "senior", 30),
        (data["medium1"], "medium", 25),
        (data["medium2"], "medium", 25),
    ]
    
    await db.set_team(project_id, members)
    await db.set_project_status(project_id, "assigned")

    await message.answer(
        f"✅ Команда успешно назначена на проект <b>#{project_id}</b>.\n"
        f"👑 Senior: <code>{data['senior']}</code> (30%)\n"
        f"💻 Medium 1: <code>{data['medium1']}</code> (25%)\n"
        f"💻 Medium 2: <code>{data['medium2']}</code> (25%)",
        parse_mode="HTML"
    )

    # Уведомляем разработчиков в личку
    await _notify(bot, data["senior"], f"📌 Вас назначили <b>Senior</b> на проект #{project_id}. Ваша доля: 30%.")
    await _notify(bot, data["medium1"], f"📌 Вас назначили <b>Medium</b> на проект #{project_id}. Ваша доля: 25%.")
    await _notify(bot, data["medium2"], f"📌 Вас назначили <b>Medium</b> на проект #{project_id}. Ваша доля: 25%.")
