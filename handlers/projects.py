import csv
import io
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile

import db
from states import AssignForm
from config import config

logger = logging.getLogger(__name__)
router = Router()


def _can_manage(user_id: int, is_owner: bool, is_manager: bool) -> bool:
    return is_owner or is_manager


async def _notify(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text)
    except Exception:
        pass


def _parse_uid(message: Message):
    raw = (message.text or "").strip()
    return int(raw) if raw.isdigit() else None


# ==========================================
# 1. НАЗНАЧЕНИЕ КОМАНДЫ (/assign)
# ==========================================

@router.message(Command("assign"))
async def assign_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    is_owner = uid == config.owner_id
    is_manager = await db.has_active_role(uid, "manager")
    
    if not _can_manage(uid, is_owner, is_manager):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/assign &lt;project_id&gt;</code>", parse_mode="HTML")
        return
    
    project_id = int(parts[1])
    project = await db.get_project(project_id)
    if not project:
        await message.answer("Проект не найден.")
        return

    await state.update_data(project_id=project_id)
    await state.set_state(AssignForm.senior)
    await message.answer(
        f"Назначение на проект <b>#{project_id}</b>.\n\n"
        "1/3 — Введите числовой ID <b>Senior</b> разработчика:",
        parse_mode="HTML"
    )


@router.message(AssignForm.senior)
async def assign_senior(message: Message, state: FSMContext):
    uid = _parse_uid(message)
    if not uid:
        await message.answer("Введите числовой Telegram ID.")
        return
    if not await db.has_active_role(uid, "dev"):
        await message.answer("Этот пользователь не является активным разработчиком.")
        return
    
    await state.update_data(senior=uid)
    await state.set_state(AssignForm.medium1)
    await message.answer("2/3 — Введите числовой ID <b>первого Medium</b>:", parse_mode="HTML")


@router.message(AssignForm.medium1)
async def assign_medium1(message: Message, state: FSMContext):
    uid = _parse_uid(message)
    if not uid:
        await message.answer("Введите числовой Telegram ID.")
        return
    if not await db.has_active_role(uid, "dev"):
        await message.answer("Этот пользователь не является активным разработчиком.")
        return
    
    data = await state.get_data()
    if uid == data.get("senior"):
        await message.answer("Этот пользователь уже назначен Senior. Введите другого.")
        return
    
    await state.update_data(medium1=uid)
    await state.set_state(AssignForm.medium2)
    await message.answer("3/3 — Введите числовой ID <b>второго Medium</b>:", parse_mode="HTML")


@router.message(AssignForm.medium2)
async def assign_medium2(message: Message, state: FSMContext, bot: Bot):
    uid = _parse_uid(message)
    if not uid:
        await message.answer("Введите числовой Telegram ID.")
        return
    if not await db.has_active_role(uid, "dev"):
        await message.answer("Этот пользователь не является активным разработчиком.")
        return
    
    data = await state.get_data()
    if uid in (data.get("senior"), data.get("medium1")):
        await message.answer("Этот пользователь уже назначен. Введите другого.")
        return
    
    await state.clear()
    project_id = data["project_id"]

    # Команда без тестировщика: Senior (30%), Medium1 (25%), Medium2 (25%), Компания (20%)
    members = [
        (data["senior"], "senior", 30),
        (data["medium1"], "medium", 25),
        (data["medium2"], "medium", 25),
    ]
    
    await db.set_team(project_id, members)
    await db.set_project_status(project_id, "assigned")

    await message.answer(
        f"✅ Команда успешно назначена на проект <b>#{project_id}</b>.\n"
        f"Senior: <code>{data['senior']}</code>\n"
        f"Medium 1: <code>{data['medium1']}</code>\n"
        f"Medium 2: <code>{data['medium2']}</code>",
        parse_mode="HTML"
    )

    await _notify(bot, data["senior"], f"📌 Вас назначили Senior на проект #{project_id}. Ваша доля: 30%.")
    await _notify(bot, data["medium1"], f"📌 Вас назначили Medium на проект #{project_id}. Ваша доля: 25%.")
    await _notify(bot, data["medium2"], f"📌 Вас назначили Medium на проект #{project_id}. Ваша доля: 25%.")


# ==========================================
# 2. ЗАВЕРШЕНИЕ ПРОЕКТА (/complete)
# ==========================================

@router.message(Command("complete"))
async def complete(message: Message, bot: Bot):
    uid = message.from_user.id
    is_owner = uid == config.owner_id
    is_manager = await db.has_active_role(uid, "manager")
    
    if not _can_manage(uid, is_owner, is_manager):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/complete &lt;project_id&gt;</code>", parse_mode="HTML")
        return
    project_id = int(parts[1])

    project = await db.get_project(project_id)
    if not project:
        await message.answer("Проект не найден.")
        return
    if project["status"] == "done":
        await message.answer("Проект уже завершён.")
        return

    team = await db.get_team(project_id)
    if not team:
        await message.answer("Сначала назначьте команду: /assign &lt;project_id&gt;", parse_mode="HTML")
        return

    lines = []
    budget = project["budget"]

    # Скидка рефереру +1%
    if project["referrer_id"]:
        try:
            new_discount = await db.increment_discount_by_user_id(project["referrer_id"])
            await _notify(bot, project["referrer_id"], 
                f"🎉 Ваш реферал завершил проект #{project_id}!\n"
                f"Ваша скидка теперь: <b>{new_discount}%</b>")
        except Exception:
            pass

    # CEO получает 10%
    lines.append((config.owner_id, "ceo", budget * 10 // 100))

    # Команда получает свои доли
    for t in team:
        if t["role_in_project"] == "senior":
            lines.append((t["telegram_id"], "senior", budget * 30 // 100))
        elif t["role_in_project"] == "medium":
            lines.append((t["telegram_id"], "medium", budget * 25 // 100))

    # Компания забирает оставшееся (10% CEO + 20% компания = 30%, команда 80%... пересчитаем)
    # Senior 30% + Medium1 25% + Medium2 25% = 80%, CEO 10%, Компания 10%
    company_amount = budget * 10 // 100
    lines.append((None, "company", company_amount))

    await db.insert_payouts(project_id, lines)
    await db.add_company_delta(company_amount, "project_completion", project_id)
    await db.set_project_status(project_id, "done")

    report_lines = [f"✅ Проект <b>#{project_id}</b> завершён. Распределение:"]
    for user_id, role, amount in lines:
        if user_id is None:
            report_lines.append(f"• Компания — <b>{amount} ⭐</b>")
            continue
        report_lines.append(f"• {role} <code>{user_id}</code> — <b>{amount} ⭐</b>")
        await _notify(bot, user_id, f"💰 Проект #{project_id} завершён. Выплата: <b>{amount} ⭐</b>.")

    await message.answer("\n".join(report_lines), parse_mode="HTML")


# ==========================================
# 3. УПРАВЛЕНИЕ СТАТУСОМ (/status)
# ==========================================

@router.message(Command("status"))
async def set_status(message: Message):
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer(
            "Использование: <code>/status &lt;id&gt; done|unpaid|new|delete</code>",
            parse_mode="HTML"
        )
        return
    project_id = int(parts[1])
    value = parts[2].lower()

    if value == "delete":
        await db.delete_project(project_id)
        await message.answer(f"🗑 Проект #{project_id} удалён.")
        return
    
    if value not in ("done", "unpaid", "new"):
        await message.answer("Доступные статусы: done | unpaid | new | delete")
        return
        
    await db.set_project_status(project_id, value)
    await message.answer(f"✅ Статус проекта #{project_id} изменён на: <b>{value}</b>", parse_mode="HTML")


# ==========================================
# 4. ПРОСМОТР ПРОЕКТОВ
# ==========================================

@router.message(Command("table_all"))
async def table_all(message: Message):
    if message.from_user.id != config.owner_id:
        return
    rows = await db.list_projects()
    if not rows:
        await message.answer("Проектов пока нет.")
        return
    
    lines = ["<b>Список всех проектов:</b>"]
    for r in rows:
        lines.append(f"#{r['id']} | {r['status']} | {r['budget']} ⭐ | {r['title']}")
    await message.answer("\n".join(lines), parse_mode="HTML")
