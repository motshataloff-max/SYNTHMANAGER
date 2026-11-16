import os
import sys
import logging
from datetime import datetime

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile

import db
from config import config
from keyboards import main_menu, yes_no_kb, managers_list_kb
from states import AssignForm, VacationForm

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# ПРОВЕРКИ ПРАВ
# ==========================================


# ==========================================
# МАССОВАЯ РАССЫЛКА
# ==========================================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Массовая рассылка всем пользователям бота."""
    if message.from_user.id != config.owner_id:
        return
    
    # Разделяем команду и текст (поддерживает переносы строк)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("⚠️ Использование: <code>/broadcast &lt;текст рассылки&gt;</code>", parse_mode="HTML")
    
    text_to_send = parts[1]
    
    await message.answer("⏳ Запуск рассылки... Это может занять время.")
    
    # Получаем всех пользователей из БД
    async with db._conn() as conn:
        import aiosqlite
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT telegram_id FROM users")
        users = await cur.fetchall()
    
    sent = 0
    failed = 0
    
    for u in users:
        try:
            await message.bot.send_message(u["telegram_id"], text_to_send, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
            
    await message.answer(f"✅ <b>Рассылка завершена!</b>\n\n📤 Отправлено: <b>{sent}</b>\n❌ Ошибок (заблокировали бота): <b>{failed}</b>", parse_mode="HTML")
async def is_admin(user_id: int) -> bool:
    return user_id == config.owner_id or await db.has_active_role(user_id, "manager")

async def is_ceo(user_id: int) -> bool:
    return user_id == config.owner_id

# ==========================================
# КОМАНДЫ УПРАВЛЕНИЯ
# ==========================================

@router.message(Command("msg"))
async def cmd_msg(message: Message, bot: Bot):
    """Отправить сообщение клиенту от имени бота."""
    if not await is_admin(message.from_user.id):
        return  # Молча игнорируем
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/msg &lt;user_id&gt; &lt;текст&gt;</code>", parse_mode="HTML")
    
    target_id = int(parts[1])
    text = parts[2]
    
    try:
        await bot.send_message(
            target_id, 
            f"💬 <b>Сообщение от поддержки SYNTH:</b>\n\n{text}", 
            parse_mode="HTML"
        )
        await message.answer(f"✅ Сообщение доставлено пользователю <code>{target_id}</code>.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}. Возможно, бот заблокирован пользователем.")

@router.message(Command("add_manager"))
async def add_manager(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/add_manager &lt;id&gt;</code>", parse_mode="HTML")
    await db.upsert_role(int(parts[1]), "manager", "active")
    await message.answer(f"✅ Пользователь <code>{parts[1]}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_pr"))
async def add_pr(message: Message):
    if not await is_ceo(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/add_pr &lt;id&gt;</code>", parse_mode="HTML")
    uid = int(parts[1])
    await db.upsert_role(uid, "pr", "active")
    await db.set_ref_code(uid, f"ref_{uid}")
    await message.answer(f"✅ Пользователь <code>{uid}</code> назначен пиарщиком.", parse_mode="HTML")

@router.message(Command("restart_bot"))
async def restart_bot(message: Message):
    if not await is_ceo(message.from_user.id): return
    await message.answer("🔄 Перезапуск бота...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    if not await is_ceo(message.from_user.id): return
    db_path = db.DB_PATH
    if not os.path.exists(db_path):
        return await message.answer("❌ Файл базы данных не найден.")
    try:
        await message.answer("⏳ Отправляю базу данных в канал...")
        doc = FSInputFile(db_path)
        await message.bot.send_document(
            chat_id=config.ping_chat_id,
            document=doc,
            caption=f"📦 <b>Бэкап БД SYNTH</b>\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        await message.answer("✅ База данных успешно отправлена в канал!")
    except Exception as e:
        logger.error(f"Ошибка отправки бэкапа: {e}")
        await message.answer(f"❌ Ошибка при отправке: {e}")

# ==========================================
# МОДЕРАЦИЯ ЗАЯВОК (INLINE КНОПКИ)
# ==========================================

@router.callback_query(F.data.startswith("dev_approve_"))
async def callback_dev_approve(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()  # Молча игнорируем
    
    user_id = int(callback.data.split("_")[2])
    await db.upsert_role(user_id, "dev", "active", level="junior")
    await callback.message.edit_text(f"✅ <code>{user_id}</code> одобрен как разработчик.", parse_mode="HTML")
    await callback.answer("Одобрено!")
    await callback.message.bot.send_message(user_id, "✅ Ваша заявка на разработчика в SYNTH одобрена!")

@router.callback_query(F.data.startswith("dev_reject_"))
async def callback_dev_reject(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    
    user_id = int(callback.data.split("_")[2])
    await db.upsert_role(user_id, "dev", "rejected")
    await callback.message.edit_text(f"❌ <code>{user_id}</code> отклонён.", parse_mode="HTML")
    await callback.answer("Отклонено!")

@router.callback_query(F.data.startswith("partner_approve_"))
async def callback_partner_approve(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id):
        return await callback.answer()
    
    user_id = int(callback.data.split("_")[2])
    await db.upsert_role(user_id, "partner", "active")
    await callback.message.edit_text(f"✅ Партнёр <code>{user_id}</code> одобрен CEO.", parse_mode="HTML")
    await callback.answer("Одобрено!")
    await callback.message.bot.send_message(user_id, "✅ Ваша заявка на партнёрство с SYNTH одобрена! Мы свяжемся с вами для обсуждения деталей.")

@router.callback_query(F.data.startswith("partner_reject_"))
async def callback_partner_reject(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id):
        return await callback.answer()
    
    user_id = int(callback.data.split("_")[2])
    await db.upsert_role(user_id, "partner", "rejected")
    await callback.message.edit_text(f"❌ Партнёр <code>{user_id}</code> отклонён.", parse_mode="HTML")
    await callback.answer("Отклонено!")

# ==========================================
# УПРАВЛЕНИЕ ОТПУСКАМИ
# ==========================================

@router.callback_query(F.data.startswith("vacation_select_"))
async def vacation_select(callback: CallbackQuery, state: FSMContext):
    if not await is_ceo(callback.from_user.id):
        return await callback.answer()
    
    manager_id = int(callback.data.split("_")[2])
    await state.update_data(manager_id=manager_id)
    await state.set_state(VacationForm.start_date)
    await callback.message.edit_text(
        f"📅 <b>Управление отпуском</b>\n\n"
        f"Выбран менеджер: <code>{manager_id}</code>\n"
        f"Введите дату начала отпуска в формате ГГГГ-ММ-ДД (например, 2026-11-20):",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "vacation_cancel")
async def vacation_cancel(callback: CallbackQuery, state: FSMContext):
    if not await is_ceo(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ Управление отпусками отменено.")
    await callback.answer()

@router.message(VacationForm.start_date)
async def vacation_start(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%Y-%m-%d")
        await state.update_data(start_date=message.text.strip())
        await state.set_state(VacationForm.end_date)
        await message.answer("📅 Введите дату конца отпуска в формате ГГГГ-ММ-ДД (например, 2026-11-25):")
    except ValueError:
        await message.answer("⚠️ Неверный формат даты. Используйте ГГГГ-ММ-ДД.")

@router.message(VacationForm.end_date)
async def vacation_end(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(), "%Y-%m-%d")
        data = await state.get_data()
        manager_id = data["manager_id"]
        start_date = data["start_date"]
        end_date = message.text.strip()
        
        await db.add_vacation(manager_id, start_date, end_date)
        await state.clear()
        await message.answer(
            f"✅ Отпуск для менеджера <code>{manager_id}</code> установлен с {start_date} по {end_date}.\n"
            f"Теперь бот не будет назначать ему новые заявки.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except ValueError:
        await message.answer("⚠️ Неверный формат даты. Используйте ГГГГ-ММ-ДД.")

# ==========================================
# УПРАВЛЕНИЕ ПРОЕКТАМИ
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

    # ЗАЩИТА: Менеджеры не могут завершать проекты в работе без разрешения CEO
    if message.from_user.id != config.owner_id:
        if project["status"] in ["assigned", "in_progress", "in_team_heavy", "in_team_medium", "in_team_fast"]:
            return await message.answer("⛔ Этот проект уже в работе. Завершить его может только CEO.")

    if project["status"] == "done":
        return await message.answer("Проект уже завершён.")

    budget = project["budget"]
    company_share = budget * 20 // 100
    await db.add_company_delta(company_share, "project_completion", project_id)
    
    if project["referrer_id"]:
        new_discount = await db.increment_discount_by_user_id(project["referrer_id"])
        try:
            await bot.send_message(
                project["referrer_id"], 
                f"🎉 Ваш реферал завершил проект #{project_id}!\nВаша скидка теперь: <b>{new_discount}%</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await db.set_project_status(project_id, "done")
    await message.answer(f"✅ Проект #{project_id} завершён. Компания получила {company_share} ⭐.")

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
