"""
SYNTH Platform v2.0 - Общие обработчики
========================================
Базовые команды, кнопки меню, навигация.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

import db
import texts
from keyboards import client_main_menu, admin_main_menu, cancel_kb, manage_teams_kb
from states import ClientForm, DevForm, PartnerForm, SupportForm
from config import config

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# ТЕКСТЫ МЕНЮ
# ==========================================
USER_COMMANDS = (
    "📌 <b>Что я умею:</b>\n\n"
    "• 🛒 <b>Заказать разработку</b>\n"
    "• 👨‍💻 <b>Стать разработчиком</b>\n"
    "• 🤝 <b>Стать партнёром</b>\n"
    "• 🔗 <b>Моя реферальная ссылка</b>\n"
    "• 📂 <b>Мои заявки</b>\n"
    "• 🔍 <b>Проверить статус заявки</b>\n"
    "• 🎫 <b>Мой код клиента</b>\n"
    "• ℹ️ <b>О нас</b>\n"
    "• 🆘 <b>Поддержка</b>"
)

MANAGER_COMMANDS = (
    "💼 <b>Меню менеджера:</b>\n\n"
    "• 📋 <b>Все заявки (Тикеты)</b>\n"
    "• 👥 <b>Управление командами</b>\n"
    "• 👨‍💻 <b>Разработчики</b>\n"
    "• 🛡️ <b>Модерация</b>\n"
    "• 📊 <b>Статистика</b>\n"
    "• 🚫 <b>Баны</b>"
)

BOSS_COMMANDS = (
    "👑 <b>Меню CEO:</b>\n\n"
    "👥 <b>Персонал:</b>\n"
    "• <code>/add_manager &lt;id&gt;</code>\n"
    "• <code>/add_helper &lt;id&gt;</code>\n"
    "• <code>/ban &lt;id&gt;</code>\n"
    "• <code>/unban &lt;id&gt;</code>\n\n"
    "⚙️ <b>Система:</b>\n"
    "• <code>/backup_db</code>\n"
    "• <code>/stats</code>"
)

# ==========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
async def _welcome_text(uid: int) -> str:
    if uid == config.owner_id:
        return "👑 <b>Добро пожаловать, босс!</b>\n\n" + BOSS_COMMANDS
    if await db.has_active_role(uid, "manager"):
        return "💼 <b>Добро пожаловать, менеджер!</b>\n\n" + MANAGER_COMMANDS
    return texts.WELCOME + "\n\n" + USER_COMMANDS

async def _welcome_kb(uid: int):
    if uid == config.owner_id or await db.has_active_role(uid, "manager"):
        return admin_main_menu()
    return client_main_menu()

# ==========================================
# 1. БАЗОВЫЕ КОМАНДЫ
# ==========================================
@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    """Команда /start — полный сброс и возврат в главное меню"""
    logger.info(f"[COMMON] User {message.from_user.id} executed /start")
    await state.clear()
    user = await db.get_or_create_user(message.from_user)
    
    # 🔥 Генерируем личный код, если его еще нет
    if not user.get('client_code'):
        code = await db.ensure_client_code(message.from_user.id)
        await message.answer(
            f"🎉 <b>Добро пожаловать!</b>\n\n"
            f"🎫 Ваш личный код клиента: <code>{code}</code>\n\n"
            f"💡 Сохраните его. Используйте для входа в VK Mini App, чтобы все ваши заявки из Telegram и VK были в одном месте.",
            parse_mode="HTML"
        )
    
    await message.answer(
        await _welcome_text(message.from_user.id),
        reply_markup=await _welcome_kb(message.from_user.id),
        parse_mode="HTML"
    )

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=await _welcome_kb(message.from_user.id))

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        await _welcome_text(message.from_user.id),
        parse_mode="HTML",
        reply_markup=await _welcome_kb(message.from_user.id)
    )

# ==========================================
# 2. КНОПКИ НАВИГАЦИИ
# ==========================================
@router.message(F.text.in_({"🏠 Главное меню", "🔙 Главное меню", "🔙 Главное меню (Клиент)"}))
async def force_main_menu(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Главное меню'")
    await state.clear()
    await message.answer(
        "🏠 <b>Главное меню:</b>",
        reply_markup=await _welcome_kb(message.from_user.id),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Режим клиента")
async def switch_to_client_mode(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} switched to CLIENT mode")
    await state.clear()
    await message.answer(
        "👤 <b>Режим клиента активирован</b>\n\n"
        "Теперь вы видите клиентское меню.\n"
        "Для возврата в админ-панель нажмите /start",
        reply_markup=client_main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "❌ Отмена")
async def cancel_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=await _welcome_kb(message.from_user.id)
    )

# ==========================================
# 3. КЛИЕНТСКИЕ КНОПКИ
# ==========================================
@router.message(F.text == "🛒 Заказать разработку")
async def menu_order(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Заказать разработку'")
    await state.clear()
    await state.set_state(ClientForm.title)
    await message.answer(texts.CLIENT_ASK_TITLE, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "👨‍💻 Стать разработчиком")
async def menu_dev(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Стать разработчиком'")
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "dev")
    if role and role["status"] == "active":
        return await message.answer(
            f"✅ Вы уже разработчик. Уровень: <b>{role['level']}</b>.",
            parse_mode="HTML"
        )
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на модерации.")
    await state.set_state(DevForm.name)
    await message.answer(texts.DEV_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "🤝 Стать партнёром")
async def menu_partner(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Стать партнёром'")
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "partner")
    if role and role["status"] == "active":
        return await message.answer("✅ Вы уже партнёр SYNTH.")
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на рассмотрении у CEO.")
    await state.set_state(PartnerForm.name)
    await message.answer(texts.PARTNER_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text.in_({"🔗 Моя реферальная ссылка", "🔗 Моя ссылка на скидку"}))
async def menu_ref_link(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Реферальная ссылка'")
    await state.clear()
    uid = message.from_user.id
    await db.get_or_create_user(message.from_user)
    code = f"ref_{uid}"
    await db.set_ref_code(uid, code)
    link = f"https://t.me/{config.bot_username}?start={code}"
    await message.answer(texts.PR_LINK_TEXT.format(link=link), parse_mode="HTML", reply_markup=client_main_menu())

@router.message(F.text.in_({"📊 Моя статистика", "📊 Статистика"}))
async def my_stats(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Статистика'")
    await state.clear()
    uid = message.from_user.id
    discount = await db.get_user_discount(uid)
    lines = [f"<b>Ваш ID:</b> <code>{uid}</code>", f"🎁 <b>Ваша скидка:</b> <b>{discount}%</b>"]
    if await db.has_active_role(uid, "pr"):
        s = await db.pr_stats(uid)
        lines += ["", "<b>📣 Статистика пиарщика:</b>", f"Клиентов: <b>{s['clients']}</b>", f"Заказов: <b>{s['orders']}</b>"]
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=await _welcome_kb(uid))

@router.message(F.text == "🎫 Мой код клиента")
async def show_client_code(message: Message, state: FSMContext):
    """Показывает личный код клиента"""
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'Мой код клиента'")
    await state.clear()
    user_id = message.from_user.id
    code = await db.ensure_client_code(user_id)
    
    await message.answer(
        f"🎫 <b>Ваш личный код клиента:</b>\n\n"
        f"<code>{code}</code>\n\n"
        f"💡 Используйте этот код для входа в VK Mini App.\n"
        f"Он свяжет ваш Telegram и VK аккаунты, чтобы все заявки были в одном месте.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

@router.message(F.text == "ℹ️ О нас")
async def about(message: Message, state: FSMContext):
    logger.info(f"[COMMON] User {message.from_user.id} clicked 'О нас'")
    await state.clear()
    about_text = await db.get_setting("about")
    await message.answer(
        about_text or "🇷🇺 SYNTH — российская команда разработчиков. Работаем с РФ и дружественными странами.",
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

# ==========================================
# 4. АДМИНСКИЕ КНОПКИ
# ==========================================
@router.message(F.text.in_({"📈 Статистика бота", "📊 Статистика"}))
async def admin_stats_button(message: Message):
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    logger.info(f"[ADMIN] User {uid} clicked 'Статистика'")
    s = await db.general_stats()
    lines = [
        "<b>📊 Общая статистика SYNTH</b>", "──────────────────────",
        f"👥 Пользователей: <b>{s['clients']}</b>",
        f"📦 Активных проектов: <b>{s['active_projects']}</b>",
        f"✅ Завершённых: <b>{s['done_projects']}</b>",
        f"💰 Оборот: <b>{s['turnover']} ₽</b>",
        f"🎫 Активных тикетов: <b>{s.get('active_tickets', 0)}</b>",
        f"🔒 Закрытых тикетов: <b>{s.get('closed_tickets', 0)}</b>"
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "👨‍💻 Разработчики")
async def admin_devs_button(message: Message):
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    logger.info(f"[ADMIN] User {uid} clicked 'Разработчики'")
    devs = await db.list_active_by_role("dev")
    if not devs:
        return await message.answer("📭 Разработчиков нет.")
    lines = ["<b>👨‍💻 Активные разработчики:</b>"]
    for d in devs:
        lines.append(f"• <code>{d['telegram_id']}</code> — {d.get('level', 'N/A')}")
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "👥 Менеджеры")
async def admin_managers_button(message: Message):
    if message.from_user.id != config.owner_id:
        return
    logger.info(f"[ADMIN] CEO {message.from_user.id} clicked 'Менеджеры'")
    rows = await db.list_managers()
    if not rows:
        return await message.answer("📭 Менеджеров нет.")
    lines = ["<b>👥 Менеджеры:</b>"]
    for r in rows:
        lines.append(f"• <code>{r['telegram_id']}</code> — {r['status']}")
    await message.answer("\n".join(lines), parse_mode="HTML")

# ==========================================
# 5. КОМАНДЫ CEO
# ==========================================
@router.message(Command("add_manager"))
async def add_manager(message: Message):
    if message.from_user.id != config.owner_id:
        return
    logger.info(f"[ADMIN] CEO executed /add_manager: {message.text}")
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_manager &lt;id&gt;</code>", parse_mode="HTML")
    if hasattr(db, 'upsert_role'):
        await db.upsert_role(int(parts[1]), "manager", "active")
    await message.answer(f"✅ <code>{parts[1]}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_helper"))
async def add_helper(message: Message):
    if message.from_user.id != config.owner_id:
        return
    logger.info(f"[ADMIN] CEO executed /add_helper: {message.text}")
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_helper &lt;id&gt;</code>", parse_mode="HTML")
    if hasattr(db, 'upsert_role'):
        await db.upsert_role(int(parts[1]), "helper", "active")
    await message.answer(f"✅ <code>{parts[1]}</code> назначен хелпером.", parse_mode="HTML")

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id != config.owner_id:
        return
    logger.info(f"[ADMIN] CEO executed /ban: {message.text}")
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/ban &lt;id&gt; [причина]</code>", parse_mode="HTML")
    user_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else "Без причины"
    if user_id == config.owner_id:
        return await message.answer("⚠️ Нельзя забанить CEO.")
    await db.ban_user(user_id, reason)
    await message.answer(f"🚫 <code>{user_id}</code> забанен.\n📝 Причина: {reason}", parse_mode="HTML")

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id != config.owner_id:
        return
    logger.info(f"[ADMIN] CEO executed /unban: {message.text}")
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/unban &lt;id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.unban_user(user_id)
    await message.answer(f"✅ <code>{user_id}</code> разбанен.", parse_mode="HTML")

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    if message.from_user.id != config.owner_id:
        return
    logger.info(f"[ADMIN] CEO requested manual backup")
    try:
        doc = FSInputFile(config.db_path, filename=f"manual_backup_{message.from_user.id}.db")
        await message.answer_document(doc, caption="💾 Ручной бэкап БД")
    except Exception as e:
        logger.error(f"[ADMIN] Backup error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != config.owner_id and not await db.has_active_role(message.from_user.id, "manager"):
        return
    logger.info(f"[ADMIN] User {message.from_user.id} requested /stats")
    s = await db.general_stats()
    text = (
        f"<b>📊 Статистика SYNTH</b>\n"
        f"──────────────────────\n"
        f"👥 Клиентов: <b>{s['clients']}</b>\n"
        f"📦 Активных: <b>{s['active_projects']}</b>\n"
        f"✅ Завершённых: <b>{s['done_projects']}</b>\n"
        f"💰 Оборот: <b>{s['turnover']} ₽</b>\n"
        f"🎫 Активных тикетов: <b>{s.get('active_tickets', 0)}</b>\n"
        f"🔒 Закрытых тикетов: <b>{s.get('closed_tickets', 0)}</b>"
    )
    await message.answer(text, parse_mode="HTML")

# ==========================================
# 6. FALLBACK
# ==========================================
@router.message(F.text, F.chat.type == "private")
async def catch_all_text(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state:
        logger.info(f"[COMMON] User {message.from_user.id} in state {current_state}, text: {message.text[:50]}")
        return
    
    logger.info(f"[COMMON] User {message.from_user.id} sent unrecognized text: {message.text[:50]}")
    await message.answer(
        "🤔 Я не распознал команду. Пожалуйста, используйте кнопки меню ниже 👇",
        reply_markup=await _welcome_kb(message.from_user.id)
    )



