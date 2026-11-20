from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import Command, CommandStart, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import texts
from keyboards import main_menu, admin_menu, cancel_kb
from states import ClientForm, DevForm, PartnerForm, SupportForm, VacationForm, BroadcastForm
from config import config

router = Router()

# ==========================================
# MIDDLEWARE: ПРОВЕРКА НА БАН
# ==========================================
class BanMiddleware(BaseMiddleware):
    """Блокирует забаненных пользователей на уровне всего роутера."""
    async def __call__(self, handler, event, data):
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id
            if user_id != config.owner_id and await db.is_banned(user_id):
                if hasattr(event, "answer"):
                    try:
                        await event.answer("🚫 Ваш аккаунт заблокирован администрацией SYNTH.")
                    except Exception:
                        pass
                return
        return await handler(event, data)

router.message.middleware(BanMiddleware())
router.callback_query.middleware(BanMiddleware())

# ==========================================
# ТЕКСТЫ КОМАНД
# ==========================================
USER_COMMANDS = (
    "📌 <b>Что я умею:</b>\n\n"
    "• 🛒 <b>Заказать разработку</b> — оставьте заявку\n"
    "• 👨‍💻 <b>Стать разработчиком</b> — заполните анкету\n"
    "• 🤝 <b>Стать партнёром</b> — заявка на партнёрство\n"
    "• 🔗 <b>Моя ссылка на скидку</b> — +15% за каждого клиента от 500 ⭐\n"
    "• 📊 <b>Моя статистика</b> — ваши данные\n"
    "• ℹ️ <b>О нас</b> — информация о SYNTH\n"
    "• 🆘 <b>Поддержка</b> — написать хелперу\n\n"
    "<i>Нажмите на кнопку внизу экрана 👇</i>"
)

MANAGER_COMMANDS = (
    "📌 <b>Что я умею (менеджер):</b>\n\n"
    "• 📋 <b>Список проектов</b>\n"
    "• 👨‍💻 <b>Разработчики</b>\n"
    "• 👥 <b>Менеджеры</b>\n"
    "• 📈 <b>Статистика бота</b>\n"
    "• 🏖 <b>Управление отпусками</b>\n"
    "• 💬 <code>/msg &lt;id&gt; &lt;текст&gt;</code> — написать клиенту\n\n"
    "<i>Нажмите на кнопку внизу экрана 👇</i>"
)

BOSS_COMMANDS = (
    "📌 <b>Что я умею (CEO):</b>\n\n"
    "👥 <b>Персонал:</b>\n"
    "• <code>/add_pr &lt;id&gt;</code> — назначить пиарщика\n"
    "• <code>/add_manager &lt;id&gt;</code> — назначить менеджера\n"
    "• <code>/add_helper &lt;id&gt;</code> — назначить хелпера\n"
    "• <code>/ban &lt;id&gt; [причина]</code> — забанить пользователя\n"
    "• <code>/unban &lt;id&gt;</code> — разбанить пользователя\n\n"
    "📊 <b>Статистика:</b>\n"
    "• <code>/stats</code> — общая сводка\n"
    "• <code>/ref_stats &lt;id&gt;</code> — статистика по рефералу\n\n"
    "⚙️ <b>Проекты:</b>\n"
    "• <code>/assign &lt;id&gt;</code> — назначить команду\n"
    "• <code>/complete &lt;id&gt;</code> — завершить проект\n"
    "• <code>/status &lt;id&gt; done|unpaid|new|delete</code>\n\n"
    "💬 <b>Связь:</b>\n"
    "• <code>/msg &lt;id&gt; &lt;текст&gt;</code> — сообщение клиенту\n\n"
    "💾 <b>База данных:</b>\n"
    "• <code>/backup_db</code> — бэкап БД в канал\n"
    "• <code>/restart_bot</code>\n\n"
    "<i>Напишите /help для полного списка</i>"
)

MENU_BUTTONS = {
    "🛒 Заказать разработку", "👨‍💻 Стать разработчиком", "🤝 Стать партнёром",
    "🔗 Моя ссылка на скидку", "📊 Моя статистика", "ℹ️ О нас", "🆘 Поддержка",
    "🔙 Главное меню", "📈 Статистика бота", "📋 Список проектов", "👨‍💻 Разработчики",
    "👥 Менеджеры", "🏖 Управление отпусками", "👥 Управление командами",
    "📢 Глобальная рассылка", "⚙️ Настройки",
}


async def _welcome_text(uid: int) -> str:
    if uid == config.owner_id:
        return "👑 <b>Добро пожаловать, босс!</b>\n\n" + BOSS_COMMANDS
    if await db.has_active_role(uid, "manager"):
        return "💼 <b>Добро пожаловать, менеджер!</b>\n\n" + MANAGER_COMMANDS
    return texts.WELCOME + "\n\n" + USER_COMMANDS


async def _welcome_kb(uid: int):
    if uid == config.owner_id or await db.has_active_role(uid, "manager"):
        return admin_menu()
    return main_menu()


# ==========================================
# /START, /HELP, /CANCEL
# ==========================================
@router.message(CommandStart(deep_link=True))
async def start_with_link(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    ref_code = (command.args or "").strip()
    referrer_id = None
    ref_message = ""
    
    if ref_code.startswith("ref_"):
        referrer_user = await db.find_by_ref_code(ref_code)
        if referrer_user:
            referrer_uid = referrer_user["telegram_id"]
            if referrer_uid == uid:
                ref_message = "⚠️ Вы не можете использовать свою собственную реферальную ссылку.\n\n"
            else:
                existing_user = await db.get_user(uid)
                if existing_user and existing_user.get("referrer_id"):
                    ref_message = "⚠️ Вы уже были зарегистрированы по реферальной ссылке. Повторное использование невозможно.\n\n"
                elif existing_user:
                    ref_message = "⚠️ Вы уже зарегистрированы в боте. Реферальная ссылка не может быть применена к существующему аккаунту.\n\n"
                else:
                    referrer_id = referrer_uid
                    ref_message = "🎁 Вы перешли по приглашению. Ваш реферер получит бонус при вашем первом заказе от 500 ⭐!\n\n"
        else:
            ref_message = "⚠️ Неверная реферальная ссылка.\n\n"

    await db.get_or_create_user(message.from_user, referrer_id=referrer_id)
    await message.answer(ref_message + await _welcome_text(uid), reply_markup=await _welcome_kb(uid), parse_mode="HTML")


@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    await state.clear()
    await db.get_or_create_user(message.from_user)
    await message.answer(await _welcome_text(message.from_user.id), reply_markup=await _welcome_kb(message.from_user.id), parse_mode="HTML")


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Диалог сброшен.", reply_markup=await _welcome_kb(message.from_user.id))


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(await _welcome_text(message.from_user.id), parse_mode="HTML")


# ==========================================
# КНОПКИ ГЛАВНОГО МЕНЮ
# ==========================================
async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Действие отменено.", reply_markup=await _welcome_kb(message.from_user.id))
        return True
    return False


@router.message(F.text == "🛒 Заказать разработку")
async def menu_order(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    await state.clear()
    await state.set_state(ClientForm.title)
    await message.answer(texts.CLIENT_ASK_TITLE, parse_mode="HTML", reply_markup=cancel_kb())


@router.message(F.text == "👨‍💻 Стать разработчиком")
async def menu_dev(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "dev")
    if role and role["status"] == "active":
        return await message.answer(f"✅ Вы уже разработчик. Уровень: <b>{role['level']}</b>.", parse_mode="HTML")
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на модерации. Мы свяжемся с вами.")
    await state.set_state(DevForm.name)
    await message.answer(texts.DEV_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())


@router.message(F.text == "🤝 Стать партнёром")
async def menu_partner(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "partner")
    if role and role["status"] == "active":
        return await message.answer("✅ Вы уже партнёр SYNTH.")
    if role and role["status"] == "pending":
        return await message.answer("⏳ Ваша заявка на партнёрство отправлена CEO на рассмотрение.")
    await state.set_state(PartnerForm.name)
    await message.answer(texts.PARTNER_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb())


@router.message(F.text == "🔗 Моя ссылка на скидку")
async def menu_ref_link(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    await state.clear()
    uid = message.from_user.id
    await db.get_or_create_user(message.from_user)
    code = f"ref_{uid}"
    await db.set_ref_code(uid, code)
    link = f"https://t.me/{config.bot_username}?start={code}"
    await message.answer(texts.PR_LINK_TEXT.format(link=link), parse_mode="HTML")


@router.message(F.text == "ℹ️ О нас")
async def about(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    await state.clear()
    await message.answer(await db.get_setting("about"), parse_mode="HTML")


@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext, bot: Bot):
    if await _check_cancel(message, state): return
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    
    existing_ticket = await db.find_open_ticket_by_user(message.from_user.id)
    if existing_ticket:
        return await message.answer(
            f"🆘 <b>У вас уже есть открытый тикет #{existing_ticket['id']}.</b>\n\n"
            "Просто напишите сообщение сюда — оно будет переслано хелперу.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    
    await message.answer(texts.SUPPORT_ASK_MSG, parse_mode="HTML", reply_markup=cancel_kb())


@router.message(F.text == "📊 Моя статистика")
async def my_stats(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    await state.clear()
    uid = message.from_user.id
    discount = await db.get_user_discount(uid)
    lines = [
        f"<b>Ваш ID:</b> <code>{uid}</code>",
        f"🎁 <b>Ваша скидка:</b> <b>{discount}%</b> (15% за каждого клиента от 500 ⭐)",
    ]
    if await db.has_active_role(uid, "pr"):
        s = await db.pr_stats(uid)
        lines += [
            "", "<b>📣 Статистика пиарщика:</b>",
            f"Клиентов: <b>{s['clients']}</b>",
            f"Заказов: <b>{s['orders']}</b>",
            f"Оборот: <b>{s['total']} ⭐</b>",
            f"Заработано: <b>{s['earned']} ⭐</b>",
        ]
    await message.answer("\n".join(lines), parse_mode="HTML")


# ==========================================
# АДМИНСКИЕ КНОПКИ
# ==========================================
@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu())


@router.message(F.text == "📈 Статистика бота")
async def admin_stats_button(message: Message):
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
        f"💰 Оборот: <b>{s['turnover']} ⭐</b>",
        f"🏦 Счёт компании: <b>{s['company']} ⭐</b>",
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "📋 Список проектов")
async def admin_projects_button(message: Message):
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    rows = await db.list_projects(limit=20)
    if not rows:
        return await message.answer("📭 Проектов нет.")
    lines = ["<b>📋 Проекты:</b>"]
    for r in rows:
        emoji = {"new": "🆕", "assigned": "👥", "in_progress": "🔨", "done": "✅"}.get(r["status"], "⚪")
        lines.append(f"{emoji} #{r['id']} | <b>{r['budget']}⭐</b> | {r['status']} | {r['title'][:30]}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "👨‍💻 Разработчики")
async def admin_devs_button(message: Message):
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return
    devs = await db.list_active_by_role("dev")
    if not devs:
        return await message.answer("📭 Разработчиков нет.")
    lines = ["<b>👨‍💻 Активные разработчики:</b>"]
    for d in devs:
        lines.append(f"• <code>{d['telegram_id']}</code> — {d['level']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "👥 Менеджеры")
async def admin_managers_button(message: Message):
    if message.from_user.id != config.owner_id:
        return
    rows = await db.list_managers()
    if not rows:
        return await message.answer("📭 Менеджеров нет.")
    lines = ["<b>👥 Менеджеры:</b>"]
    for r in rows:
        emoji = {"active": "🟢", "suspended": "🟡", "rejected": "🔴"}.get(r.get("status"), "⚪")
        lines.append(f"{emoji} <code>{r['telegram_id']}</code> — {r['status']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "🏖 Управление отпусками")
async def admin_vacation_button(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id:
        return
    await state.clear()
    managers = await db.list_managers()
    if not managers:
        return await message.answer("📭 Менеджеров нет.")
    
    from keyboards import managers_list_kb
    await state.set_state(VacationForm.select_manager)
    await message.answer("👤 <b>Выберите менеджера для управления отпуском:</b>", reply_markup=managers_list_kb(managers), parse_mode="HTML")


@router.message(F.text == "👥 Управление командами")
async def manage_teams_btn(message: Message):
    if message.from_user.id != config.owner_id:
        return
    teams = await db.get_all_teams()
    from keyboards import manage_teams_kb
    await message.answer("👥 <b>Управление статусами команд:</b>\nНажмите на команду, чтобы изменить её статус.", parse_mode="HTML", reply_markup=manage_teams_kb(teams))


@router.message(F.text == "📢 Глобальная рассылка")
async def start_broadcast_btn(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id:
        return
    await state.set_state(BroadcastForm.waiting_message)
    await message.answer("📢 <b>Режим рассылки активирован.</b>\n\nОтправьте текст или перешлите сообщение.\nДля отмены нажмите /cancel", parse_mode="HTML")


@router.message(F.text == "⚙️ Настройки")
async def admin_settings_button(message: Message):
    if message.from_user.id != config.owner_id:
        return
    await message.answer(
        "<b>⚙️ Настройки CEO</b>\n\n"
        "• <code>/set_about &lt;текст&gt;</code>\n"
        "• <code>/add_manager &lt;id&gt;</code>\n"
        "• <code>/add_pr &lt;id&gt;</code>\n"
        "• <code>/add_helper &lt;id&gt;</code>\n"
        "• <code>/ban &lt;id&gt;</code> / <code>/unban &lt;id&gt;</code>\n"
        "• <code>/backup_db</code> — бэкап БД\n"
        "• <code>/restart_bot</code>",
        parse_mode="HTML",
    )


# ==========================================
# БАН / РАЗБАН (CEO)
# ==========================================
@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/ban &lt;user_id&gt; [причина]</code>", parse_mode="HTML")
    
    user_id = int(parts[1])
    reason = parts[2] if len(parts) > 2 else "Не указана"
    
    if user_id == config.owner_id:
        return await message.answer("⚠️ Нельзя забанить самого CEO.")
    
    await db.ban_user(user_id, reason)
    await message.answer(f"🚫 Пользователь <code>{user_id}</code> забанен.\nПричина: {reason}", parse_mode="HTML")
    
    try:
        await message.bot.send_message(user_id, f"🚫 <b>Ваш аккаунт заблокирован администрацией SYNTH.</b>\nПричина: {reason}", parse_mode="HTML")
    except Exception:
        pass


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id != config.owner_id:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("⚠️ Использование: <code>/unban &lt;user_id&gt;</code>", parse_mode="HTML")
    
    user_id = int(parts[1])
    await db.unban_user(user_id)
    await message.answer(f"✅ Пользователь <code>{user_id}</code> разбанен.", parse_mode="HTML")
    
    try:
        await message.bot.send_message(user_id, "✅ Ваш аккаунт разблокирован администрацией SYNTH. Добро пожаловать обратно!")
    except Exception:
        pass


# ==========================================
# АВТО-ВОЗВРАТ В ПОДДЕРЖКУ
# ==========================================
@router.message(F.text, ~F.text.startswith("/"), StateFilter(None))
async def auto_support_forward(message: Message, bot: Bot):
    """Если у клиента есть открытый тикет и он пишет произвольный текст — пересылаем в тему."""
    user_id = message.from_user.id
    
    # Пропускаем админов и менеджеров
    if user_id == config.owner_id or await db.has_active_role(user_id, "manager"):
        return
    
    # Пропускаем, если это кнопка меню
    if message.text in MENU_BUTTONS:
        return
    
    ticket = await db.find_open_ticket_by_user(user_id)
    if not ticket or not ticket["topic_id"]:
        return
    
    try:
        await bot.send_message(
            config.support_group_id,
            f"💬 <b>Клиент пишет:</b>\n{message.text}",
            message_thread_id=ticket["topic_id"],
            parse_mode="HTML"
        )
        await message.answer("📨 Сообщение передано хелперу.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка пересылки: {e}")
