from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

import db
import texts
from keyboards import client_main_menu, admin_main_menu, cancel_kb, manage_teams_kb
from states import ClientForm, DevForm, PartnerForm, SupportForm
from config import config

router = Router()

# ==========================================
# ТЕКСТЫ МЕНЮ (ПОЛНЫЕ)
# ==========================================
USER_COMMANDS = (
    "📌 <b>Что я умею:</b>\n\n"
    "• 🛒 <b>Заказать разработку</b> — оформить заявку на создание бота/сайта\n"
    "• 👨‍💻 <b>Стать разработчиком</b> — подать заявку в нашу команду\n"
    "• 🤝 <b>Стать партнёром</b> — сотрудничать с нами\n"
    "• 🔗 <b>Моя реферальная ссылка</b> — получить персональную ссылку со скидкой\n"
    "• 📂 <b>Мои заявки</b> — посмотреть список ваших обращений\n"
    "• 🔍 <b>Проверить статус заявки</b> — узнать статус по номеру тикета\n"
    "• ℹ️ <b>О нас</b> — информация о студии SYNTH\n"
    "• 🆘 <b>Поддержка</b> — связаться с менеджером"
)

MANAGER_COMMANDS = (
    "💼 <b>Меню менеджера:</b>\n\n"
    "• 📋 <b>Все заявки (Тикеты)</b> — список активных заявок\n"
    "• 👥 <b>Управление командами</b> — изменить статусы команд\n"
    "• 👨‍💻 <b>Разработчики</b> — список активных разработчиков\n"
    "• 🛡️ <b>Модерация</b> — проверка заявок на роли\n"
    "• 📊 <b>Статистика</b> — общая статистика бота\n"
    "• 🚫 <b>Баны</b> — управление банами"
)

BOSS_COMMANDS = (
    "👑 <b>Меню CEO:</b>\n\n"
    "👥 <b>Персонал:</b>\n"
    "• <code>/add_manager &lt;telegram_id&gt;</code> — назначить менеджера\n"
    "• <code>/add_helper &lt;telegram_id&gt;</code> — назначить хелпера\n"
    "• <code>/ban &lt;telegram_id&gt; [причина]</code> — забанить пользователя\n"
    "• <code>/unban &lt;telegram_id&gt;</code> — разбанить пользователя\n\n"
    "⚙️ <b>Система:</b>\n"
    "• <code>/backup_db</code> — скачать бэкап базы данных\n"
    "• <code>/stats</code> — полная статистика\n"
    "• <code>/ticket &lt;номер&gt;</code> — карточка тикета"
)

# ==========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
async def _welcome_text(uid: int) -> str:
    """Возвращает текст приветствия в зависимости от роли"""
    if uid == config.owner_id:
        return "👑 <b>Добро пожаловать, босс!</b>\n\n" + BOSS_COMMANDS
    if await db.has_active_role(uid, "manager"):
        return "💼 <b>Добро пожаловать, менеджер!</b>\n\n" + MANAGER_COMMANDS
    return texts.WELCOME + "\n\n" + USER_COMMANDS

async def _welcome_kb(uid: int):
    """Возвращает клавиатуру в зависимости от роли"""
    if uid == config.owner_id or await db.has_active_role(uid, "manager"):
        return admin_main_menu()
    return client_main_menu()

# ==========================================
# АБСОЛЮТНЫЙ СБРОС (РАБОТАЕТ ИЗ ЛЮБОГО МЕСТА)
# ==========================================
@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    """Команда /start — полный сброс и возврат в главное меню"""
    await state.clear()
    await db.get_or_create_user(message.from_user)
    await message.answer(
        await _welcome_text(message.from_user.id), 
        reply_markup=await _welcome_kb(message.from_user.id), 
        parse_mode="HTML"
    )

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Команда /cancel — отмена текущего действия"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено.", 
        reply_markup=await _welcome_kb(message.from_user.id)
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help — показать справку"""
    await message.answer(
        await _welcome_text(message.from_user.id), 
        parse_mode="HTML", 
        reply_markup=await _welcome_kb(message.from_user.id)
    )

# ==========================================
# КНОПКИ ГЛАВНОГО МЕНЮ (СБРОС ИЗ ЛЮБОГО СОСТОЯНИЯ)
# ==========================================
@router.message(F.text.in_({"🔙 Главное меню", "🔙 Главное меню (Клиент)", "🏠 Главное меню"}))
async def back_to_main(message: Message, state: FSMContext):
    """Кнопка возврата в главное меню — работает из любого состояния"""
    await state.clear()
    await message.answer(
        "🏠 <b>Главное меню:</b>", 
        reply_markup=await _welcome_kb(message.from_user.id),
        parse_mode="HTML"
    )

@router.message(F.text == "❌ Отмена")
async def cancel_button(message: Message, state: FSMContext):
    """Кнопка отмены — работает из любого состояния"""
    await state.clear()
    await message.answer(
        "❌ Действие отменено.", 
        reply_markup=await _welcome_kb(message.from_user.id)
    )

# ==========================================
# КЛИЕНТСКИЕ КНОПКИ
# ==========================================
@router.message(F.text == "🛒 Заказать разработку")
async def menu_order(message: Message, state: FSMContext):
    """Кнопка заказа разработки"""
    await state.clear()
    await state.set_state(ClientForm.title)
    await message.answer(
        texts.CLIENT_ASK_TITLE, 
        parse_mode="HTML", 
        reply_markup=cancel_kb()
    )

@router.message(F.text == "👨‍💻 Стать разработчиком")
async def menu_dev(message: Message, state: FSMContext):
    """Кнопка подачи заявки разработчиком"""
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
    await message.answer(
        texts.DEV_ASK_NAME, 
        parse_mode="HTML", 
        reply_markup=cancel_kb()
    )

@router.message(F.text == "🤝 Стать партнёром")
async def menu_partner(message: Message, state: FSMContext):
    """Кнопка подачи заявки партнёром"""
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "partner")
    if role and role["status"] == "active":
        return await message.answer("✅ Вы уже партнёр SYNTH.")
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на рассмотрении у CEO.")
    await state.set_state(PartnerForm.name)
    await message.answer(
        texts.PARTNER_ASK_NAME, 
        parse_mode="HTML", 
        reply_markup=cancel_kb()
    )

@router.message(F.text.in_({"🔗 Моя реферальная ссылка", "🔗 Моя ссылка на скидку"}))
async def menu_ref_link(message: Message, state: FSMContext):
    """Кнопка получения реферальной ссылки"""
    await state.clear()
    uid = message.from_user.id
    await db.get_or_create_user(message.from_user)
    code = f"ref_{uid}"
    await db.set_ref_code(uid, code)
    link = f"https://t.me/{config.bot_username}?start={code}"
    await message.answer(
        texts.PR_LINK_TEXT.format(link=link), 
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

@router.message(F.text == "📊 Моя статистика" | F.text == "📊 Статистика")
async def my_stats(message: Message, state: FSMContext):
    """Кнопка просмотра статистики"""
    await state.clear()
    uid = message.from_user.id
    discount = await db.get_user_discount(uid)
    lines = [
        f"<b>Ваш ID:</b> <code>{uid}</code>",
        f"🎁 <b>Ваша скидка:</b> <b>{discount}%</b>"
    ]
    if await db.has_active_role(uid, "pr"):
        s = await db.pr_stats(uid)
        lines += [
            "",
            "<b>📣 Статистика пиарщика:</b>",
            f"Клиентов: <b>{s['clients']}</b>",
            f"Заказов: <b>{s['orders']}</b>"
        ]
    await message.answer(
        "\n".join(lines), 
        parse_mode="HTML",
        reply_markup=await _welcome_kb(uid)
    )

@router.message(F.text == "ℹ️ О нас")
async def about(message: Message, state: FSMContext):
    """Кнопка информации о нас"""
    await state.clear()
    about_text = await db.get_setting("about")
    await message.answer(
        about_text or "🇷🇺 SYNTH — российская команда разработчиков. Работаем с РФ и дружественными странами.", 
        parse_mode="HTML",
        reply_markup=client_main_menu()
    )

# ==========================================
# АДМИНСКИЕ КНОПКИ (МЕНЕДЖЕРЫ И CEO)
# ==========================================
@router.message(F.text == "📈 Статистика бота" | F.text == "📊 Статистика")
async def admin_stats_button(message: Message):
    """Кнопка общей статистики для админов"""
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    s = await db.general_stats()
    lines = [
        "<b>📊 Общая статистика SYNTH</b>",
        "──────────────────────",
        f"👥 Пользователей: <b>{s['clients']}</b>",
        f"📦 Активных проектов: <b>{s['active_projects']}</b>",
        f"✅ Завершённых: <b>{s['done_projects']}</b>",
        f"💰 Оборот: <b>{s['turnover']} ₽</b>"
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "📋 Список проектов")
async def admin_projects_button(message: Message):
    """Кнопка списка проектов для админов"""
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    rows = await db.list_projects(limit=20) if hasattr(db, 'list_projects') else []
    if not rows:
        return await message.answer("📭 Проектов нет.")
    lines = ["<b>📋 Проекты:</b>"]
    for r in rows:
        lines.append(f"#{r['id']} | <b>{r['budget']} ₽</b> | {r['status']} | {r['title'][:30]}")
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "👨‍💻 Разработчики")
async def admin_devs_button(message: Message):
    """Кнопка списка разработчиков для админов"""
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    devs = await db.list_active_by_role("dev")
    if not devs:
        return await message.answer("📭 Разработчиков нет.")
    lines = ["<b>👨‍💻 Активные разработчики:</b>"]
    for d in devs:
        lines.append(f"• <code>{d['telegram_id']}</code> — {d.get('level', 'N/A')}")
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "👥 Менеджеры")
async def admin_managers_button(message: Message):
    """Кнопка списка менеджеров для CEO"""
    if message.from_user.id != config.owner_id:
        return
    rows = await db.list_managers()
    if not rows:
        return await message.answer("📭 Менеджеров нет.")
    lines = ["<b>👥 Менеджеры:</b>"]
    for r in rows:
        lines.append(f"• <code>{r['telegram_id']}</code> — {r['status']}")
    await message.answer("\n".join(lines), parse_mode="HTML")

# ==========================================
# КОМАНДЫ CEO (БЕЗ КНОПОК)
# ==========================================
@router.message(Command("add_manager"))
async def add_manager(message: Message):
    """Команда /add_manager — назначить менеджера"""
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_manager &lt;telegram_id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.upsert_role(user_id, "manager", "active") if hasattr(db, 'upsert_role') else None
    await message.answer(f"✅ <code>{user_id}</code> назначен менеджером.", parse_mode="HTML")

@router.message(Command("add_helper"))
async def add_helper(message: Message):
    """Команда /add_helper — назначить хелпера"""
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/add_helper &lt;telegram_id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.upsert_role(user_id, "helper", "active") if hasattr(db, 'upsert_role') else None
    await message.answer(f"✅ <code>{user_id}</code> назначен хелпером.", parse_mode="HTML")

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    """Команда /ban — забанить пользователя"""
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/ban &lt;id&gt; [причина]</code>", parse_mode="HTML")
    user_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else "Без причины"
    if user_id == config.owner_id:
        return await message.answer("⚠️ Нельзя забанить CEO.")
    await db.ban_user(user_id, reason)
    await message.answer(f"🚫 <code>{user_id}</code> забанен.", parse_mode="HTML")

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    """Команда /unban — разбанить пользователя"""
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ <code>/unban &lt;id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.unban_user(user_id)
    await message.answer(f"✅ <code>{user_id}</code> разбанен.", parse_mode="HTML")

@router.message(Command("backup_db"))
async def backup_db(message: Message):
    """Команда /backup_db — скачать бэкап БД"""
    if message.from_user.id != config.owner_id:
        return
    try:
        doc = FSInputFile(config.db_path, filename=f"manual_backup_{message.from_user.id}.db")
        await message.answer_document(doc, caption="💾 Ручной бэкап БД")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("stats"))
async def stats(message: Message):
    """Команда /stats — полная статистика"""
    if message.from_user.id != config.owner_id and not await db.has_active_role(message.from_user.id, "manager"):
        return
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

# ==========================================
# ОБРАБОТКА НЕИЗВЕСТНЫХ КОМАНД (FALLBACK)
# ==========================================
@router.message(F.text)
async def catch_all_text(message: Message, state: FSMContext):
    """Обработчик любого текста, который не попал в другие фильтры"""
    # Проверяем, не находится ли пользователь в каком-то состоянии
    current_state = await state.get_state()
    if current_state:
        # Если да, значит, это часть диалога, и другой роутер это обработает
        return
    
    # Если состояния нет, просто вежливо подсказываем
    await message.answer(
        "🤔 Я не распознал команду. Пожалуйста, используйте кнопки меню ниже 👇",
        reply_markup=await _welcome_kb(message.from_user.id)
    )
