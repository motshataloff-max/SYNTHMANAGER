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
from keyboards import main_menu, yes_no_kb

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# ПРОВЕРКИ ПРАВ
# ==========================================

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
# ОПАСНЫЕ ДЕЙСТВИЯ (Управление проектами)
# ==========================================

@router.message(Command("complete"))
async def complete_project(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/complete &lt;project_id&gt;</code>", parse_mode="HTML")
    
    project_id = int(parts[1])
    project = await db.get_project(project_id)
    if not project or project["status"] == "done":
        return await message.answer("Проект не найден или уже завершён.")

    # Распределение бюджета (упрощённая логика)
    budget = project["budget"]
    company_share = budget * 20 // 100
    await db.add_company_delta(company_share, "project_completion", project_id)
    
    # Начисление скидки рефереру (1%)
    if project["referrer_id"]:
        await db.increment_discount_by_user_id(project["referrer_id"])
        await bot.send_message(project["referrer_id"], f"🎉 Ваш реферал завершил проект #{project_id}! Ваша скидка увеличена на 1%.")

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

    if value == "delete":
        await db.delete_project(project_id)
        await message.answer(f"🗑 Проект #{project_id} полностью удалён из базы данных.")
        return
    
    await db.set_project_status(project_id, value)
    await message.answer(f"✅ Статус проекта #{project_id} изменён на: <b>{value}</b>", parse_mode="HTML")

# ==========================================
# БЭКАП И ВОССТАНОВЛЕНИЕ
# ==========================================

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
