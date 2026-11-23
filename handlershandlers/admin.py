"""
SYNTH Platform v2.0 - Админ-панель
===================================
Обработчики команд и кнопок для CEO и менеджеров.
Все действия логируются для аудита.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

import db
from config import config
from keyboards import admin_main_menu, manage_teams_kb

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# ПРОВЕРКА ПРАВ ДОСТУПА
# ==========================================
async def _is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь CEO или менеджером"""
    return user_id == config.owner_id or await db.has_active_role(user_id, "manager")

async def _is_ceo(user_id: int) -> bool:
    """Проверяет, является ли пользователь CEO"""
    return user_id == config.owner_id

# ==========================================
# КНОПКА: 🛡️ МОДЕРАЦИЯ
# ==========================================
@router.message(F.text == "🛡️ Модерация")
async def menu_moderation(message: Message):
    """Показывает список заявок на роли (разработчики, партнёры)"""
    logger.info(f"[MODERATION] User {message.from_user.id} opened moderation panel")
    
    if not await _is_admin(message.from_user.id):
        logger.warning(f"[MODERATION] Access denied for user {message.from_user.id}")
        return await message.answer("⚠️ Доступ только для менеджеров и CEO.")
    
    try:
        pending = await db.get_pending_roles()
        logger.info(f"[MODERATION] Found {len(pending)} pending applications")
        
        if not pending:
            return await message.answer(
                "✅ <b>Все заявки обработаны!</b>\n\n"
                "Новых заявок на роли (разработчик/партнёр) нет.",
                parse_mode="HTML",
                reply_markup=admin_main_menu()
            )
        
        lines = [f"🛡️ <b>Заявки на модерации ({len(pending)}):</b>", ""]
        keyboard = []
        
        for i, p in enumerate(pending, 1):
            role_name = {
                "dev": "👨‍💻 Разработчик",
                "partner": "🤝 Партнёр",
                "helper": "🆘 Хелпер"
            }.get(p['role'], p['role'])
            
            name = p.get('full_name') or p.get('username') or 'Неизвестно'
            level = p.get('level') or '—'
            
            lines.append(f"{i}. <b>{role_name}</b>")
            lines.append(f"   👤 {name} (<code>{p['telegram_id']}</code>)")
            lines.append(f"   📋 {level}")
            lines.append(f"   📅 {p['created_at'][:16]}")
            lines.append("")
            
            # Кнопки одобрения/отклонения
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ {name[:15]}", 
                    callback_data=f"approve_{p['telegram_id']}_{p['role']}"
                ),
                InlineKeyboardButton(
                    text=f"❌ {name[:15]}", 
                    callback_data=f"reject_{p['telegram_id']}_{p['role']}"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb)
        
    except Exception as e:
        logger.error(f"[MODERATION] CRITICAL ERROR: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при загрузке заявок:\n<code>{e}</code>", parse_mode="HTML")

# ==========================================
# ОБРАБОТКА КНОПОК МОДЕРАЦИИ
# ==========================================
@router.callback_query(F.data.startswith("approve_"))
async def callback_approve(callback: CallbackQuery):
    """Одобрение заявки"""
    logger.info(f"[MODERATION] User {callback.from_user.id} clicked APPROVE: {callback.data}")
    
    if not await _is_admin(callback.from_user.id):
        return await callback.answer("⚠️ Нет прав", show_alert=True)
    
    try:
        parts = callback.data.split("_")
        user_id = int(parts[1])
        role = parts[2]
        
        await db.upsert_role(user_id, role, "active")
        logger.info(f"[MODERATION] Approved user {user_id} as {role}")
        
        await callback.message.edit_text(
            f"✅ <b>Заявка одобрена!</b>\n\n"
            f"👤 Пользователь <code>{user_id}</code>\n"
            f"🎖 Роль: <b>{role}</b>\n"
            f"👮 Одобрено: <code>{callback.from_user.id}</code>",
            parse_mode="HTML"
        )
        
        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                user_id,
                f"🎉 <b>Поздравляем!</b>\n\nВаша заявка одобрена. "
                f"Теперь у вас есть роль <b>{role}</b> в команде SYNTH.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"[MODERATION] Could not notify user {user_id}: {e}")
        
        await callback.answer("✅ Одобрено!", show_alert=True)
        
    except Exception as e:
        logger.error(f"[MODERATION] Error approving: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@router.callback_query(F.data.startswith("reject_"))
async def callback_reject(callback: CallbackQuery):
    """Отклонение заявки"""
    logger.info(f"[MODERATION] User {callback.from_user.id} clicked REJECT: {callback.data}")
    
    if not await _is_admin(callback.from_user.id):
        return await callback.answer("⚠️ Нет прав", show_alert=True)
    
    try:
        parts = callback.data.split("_")
        user_id = int(parts[1])
        role = parts[2]
        
        await db.upsert_role(user_id, role, "rejected")
        logger.info(f"[MODERATION] Rejected user {user_id} as {role}")
        
        await callback.message.edit_text(
            f"❌ <b>Заявка отклонена.</b>\n\n"
            f"👤 Пользователь <code>{user_id}</code>\n"
            f"🎖 Роль: <b>{role}</b>\n"
            f"👮 Отклонено: <code>{callback.from_user.id}</code>",
            parse_mode="HTML"
        )
        
        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                user_id,
                "😔 К сожалению, ваша заявка отклонена. "
                "Спасибо за интерес к команде SYNTH!",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"[MODERATION] Could not notify user {user_id}: {e}")
        
        await callback.answer("❌ Отклонено", show_alert=True)
        
    except Exception as e:
        logger.error(f"[MODERATION] Error rejecting: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

# ==========================================
# КНОПКА: 🚫 БАНЫ
# ==========================================
@router.message(F.text == "🚫 Баны")
async def menu_bans(message: Message):
    """Показывает список забаненных пользователей"""
    logger.info(f"[BANS] User {message.from_user.id} opened bans panel")
    
    if not await _is_ceo(message.from_user.id):
        logger.warning(f"[BANS] Access denied for user {message.from_user.id}")
        return await message.answer("⚠️ Управление банами доступно только CEO.")
    
    try:
        banned = await db.get_all_banned_users()
        logger.info(f"[BANS] Found {len(banned)} banned users")
        
        lines = [f"🚫 <b>Забаненные пользователи ({len(banned)}):</b>", ""]
        
        if not banned:
            lines.append("✅ <b>Никого не забанено.</b>")
            lines.append("\n💡 <i>Чтобы забанить пользователя, используйте команду:</i>")
            lines.append("<code>/ban &lt;telegram_id&gt; [причина]</code>")
        else:
            keyboard = []
            for b in banned:
                name = b.get('full_name') or b.get('username') or 'Неизвестно'
                reason = b.get('reason') or 'Без причины'
                lines.append(f"👤 <b>{name}</b> (<code>{b['telegram_id']}</code>)")
                lines.append(f"   📝 Причина: {reason}")
                lines.append(f"   📅 Дата: {b['created_at'][:16]}")
                lines.append("")
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🔓 Разбанить {name[:15]}", 
                        callback_data=f"unban_{b['telegram_id']}"
                    )
                ])
            
            lines.append("💡 <i>Чтобы забанить нового:</i> <code>/ban &lt;id&gt; [причина]</code>")
            
            kb = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
            await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb)
            return
        
        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_main_menu())
        
    except Exception as e:
        logger.error(f"[BANS] CRITICAL ERROR: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при загрузке банов:\n<code>{e}</code>", parse_mode="HTML")

# ==========================================
# ОБРАБОТКА КНОПКИ РАЗБАНА
# ==========================================
@router.callback_query(F.data.startswith("unban_"))
async def callback_unban(callback: CallbackQuery):
    """Разбан пользователя по кнопке"""
    logger.info(f"[BANS] User {callback.from_user.id} clicked UNBAN: {callback.data}")
    
    if not await _is_ceo(callback.from_user.id):
        return await callback.answer("⚠️ Только CEO может разбанивать", show_alert=True)
    
    try:
        user_id = int(callback.data.split("_")[1])
        await db.unban_user(user_id)
        logger.info(f"[BANS] User {user_id} unbanned by {callback.from_user.id}")
        
        await callback.message.edit_text(
            f"✅ <b>Пользователь разбанен!</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"👮 Разбанил: <code>{callback.from_user.id}</code>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Разбанен!", show_alert=True)
        
    except Exception as e:
        logger.error(f"[BANS] Error unbanning: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

# ==========================================
# КОМАНДЫ CEO
# ==========================================
@router.message(Command("add_manager"))
async def add_manager(message: Message):
    if not await _is_ceo(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} executed /add_manager: {message.text}")
    
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_manager &lt;telegram_id&gt;</code>", parse_mode="HTML")
    
    user_id = int(parts[1])
    await db.upsert_role(user_id, "manager", "active")
    logger.info(f"[ADMIN] User {user_id} added as manager")
    await message.answer(f"✅ <code>{user_id}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_helper"))
async def add_helper(message: Message):
    if not await _is_ceo(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} executed /add_helper: {message.text}")
    
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_helper &lt;telegram_id&gt;</code>", parse_mode="HTML")
    
    user_id = int(parts[1])
    await db.upsert_role(user_id, "helper", "active")
    logger.info(f"[ADMIN] User {user_id} added as helper")
    await message.answer(f"✅ <code>{user_id}</code> назначен хелпером.", parse_mode="HTML")

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await _is_ceo(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} executed /ban: {message.text}")
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/ban &lt;id&gt; [причина]</code>", parse_mode="HTML")
    
    user_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else "Без причины"
    
    if user_id == config.owner_id:
        return await message.answer("⚠️ Нельзя забанить CEO.")
    
    await db.ban_user(user_id, reason)
    logger.info(f"[ADMIN] User {user_id} banned. Reason: {reason}")
    await message.answer(
        f"🚫 <code>{user_id}</code> забанен.\n📝 Причина: {reason}",
        parse_mode="HTML"
    )

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await _is_ceo(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} executed /unban: {message.text}")
    
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/unban &lt;id&gt;</code>", parse_mode="HTML")
    
    user_id = int(parts[1])
    await db.unban_user(user_id)
    logger.info(f"[ADMIN] User {user_id} unbanned")
    await message.answer(f"✅ <code>{user_id}</code> разбанен.", parse_mode="HTML")

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    if not await _is_ceo(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} requested manual backup")
    
    try:
        doc = FSInputFile(config.db_path, filename=f"manual_backup_{message.from_user.id}.db")
        await message.answer_document(doc, caption="💾 Ручной бэкап БД")
        logger.info(f"[ADMIN] Manual backup sent to {message.from_user.id}")
    except Exception as e:
        logger.error(f"[ADMIN] Backup error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("stats"))
async def stats(message: Message):
    if not await _is_admin(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} requested stats")
    
    try:
        s = await db.general_stats()
        text = (
            f"<b>📊 Статистика SYNTH</b>\n"
            f"──────────────────────\n"
            f"👥 Клиентов: <b>{s['clients']}</b>\n"
            f"📦 Активных проектов: <b>{s['active_projects']}</b>\n"
            f"✅ Завершённых: <b>{s['done_projects']}</b>\n"
            f"💰 Оборот: <b>{s['turnover']} ₽</b>\n"
            f"🎫 Активных тикетов: <b>{s['active_tickets']}</b>\n"
            f"🔒 Закрытых тикетов: <b>{s['closed_tickets']}</b>"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"[ADMIN] Stats error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")

# ==========================================
# КНОПКА: 👥 УПРАВЛЕНИЕ КОМАНДАМИ
# ==========================================
@router.message(F.text == "👥 Управление командами")
async def teams_menu(message: Message):
    if not await _is_admin(message.from_user.id): return
    logger.info(f"[ADMIN] User {message.from_user.id} opened teams management")
    
    try:
        teams = await db.get_all_teams()
        await message.answer(
            "👥 <b>Управление командами:</b>\nНажмите на команду, чтобы изменить её статус:",
            parse_mode="HTML",
            reply_markup=manage_teams_kb(teams)
        )
    except Exception as e:
        logger.error(f"[ADMIN] Teams error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")

@router.callback_query(F.data.startswith("team_cycle_"))
async def cycle_team_status(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return await callback.answer("⚠️ Нет прав", show_alert=True)
    
    logger.info(f"[ADMIN] User {callback.from_user.id} clicked team cycle: {callback.data}")
    
    team_name = callback.data.replace("team_cycle_", "")
    teams = await db.get_all_teams()
    current = next((t for t in teams if t["team_name"] == team_name), None)
    
    if not current:
        return await callback.answer("Команда не найдена", show_alert=True)
    
    cycle = {"free": "busy", "busy": "resting", "resting": "free"}
    new_status = cycle.get(current["status"], "free")
    await db.update_team_status(team_name, new_status)
    
    logger.info(f"[ADMIN] Team '{team_name}' status changed: {current['status']} -> {new_status}")
    await callback.answer(f"✅ {team_name}: {new_status}", show_alert=True)
    
    teams = await db.get_all_teams()
    await callback.message.edit_reply_markup(reply_markup=manage_teams_kb(teams))

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=admin_main_menu())
    await callback.answer()


