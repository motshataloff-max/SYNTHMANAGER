from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import texts
from keyboards import main_menu, admin_menu
from states import ClientForm, DevForm, PartnerForm, SupportForm
from config import config

router = Router()


# ---------- Текст команд для разных ролей ----------

USER_COMMANDS = (
    "📌 <b>Что я умею:</b>\n\n"
    "• 🛒 <b>Заказать разработку</b> — оставьте заявку\n"
    "• 👨‍💻 <b>Стать разработчиком</b> — заполните анкету\n"
    "• 🤝 <b>Стать партнёром</b> — заявка на партнёрство\n"
    "• 🔗 <b>Моя ссылка на скидку</b> — +1% за каждого клиента\n"
    "• 📊 <b>Моя статистика</b> — ваши данные\n"
    "• ℹ️ <b>О нас</b> — информация о SYNTH\n"
    "• 🆘 <b>Поддержка</b> — написать хелперу\n\n"
    "<i>Нажмите на кнопку внизу экрана 👇</i>"
)

MANAGER_COMMANDS = (
    "📌 <b>Что я умею (менеджер):</b>\n\n"
    "• 📋 <b>Список проектов</b>\n"
    "• 👨‍💻 <b>Разработчики</b>\n"
    "• 📈 <b>Статистика бота</b>\n"
    "• 💬 <code>/msg &lt;id&gt; &lt;текст&gt;</code> — написать клиенту\n\n"
    "<i>Нажмите на кнопку внизу экрана 👇</i>"
)

BOSS_COMMANDS = (
    "📌 <b>Что я умею (CEO):</b>\n\n"
    "👥 <b>Персонал:</b>\n"
    "• <code>/add_pr &lt;id&gt;</code> — пиарщик\n"
    "• <code>/add_manager &lt;id&gt;</code> — менеджер\n\n"
    "📊 <b>Статистика:</b>\n"
    "• <code>/stats</code> — общая\n"
    "• <code>/ref_stats &lt;id&gt;</code> — по рефералу\n\n"
    "⚙️ <b>Проекты:</b>\n"
    "• <code>/assign &lt;id&gt;</code> — назначить команду\n"
    "• <code>/complete &lt;id&gt;</code> — завершить проект\n"
    "• <code>/status &lt;id&gt; done|unpaid|new|delete</code>\n\n"
    "💬 <b>Связь:</b>\n"
    "• <code>/msg &lt;id&gt; &lt;текст&gt;</code> — сообщение клиенту\n\n"
    "💾 <b>База данных:</b>\n"
    "• <code>/backup_db</code> — бэкап в канал\n"
    "• <code>/restore_db</code> — восстановить из файла\n\n"
    "🤖 <b>Бот:</b>\n"
    "• <code>/set_about &lt;текст&gt;</code>\n"
    "• <code>/restart_bot</code>\n\n"
    "<i>Напишите /help для полного списка</i>"
)


async def _welcome_text(uid: int) -> str:
    """Возвращает приветствие в зависимости от роли."""
    if uid == config.owner_id:
        return "👑 <b>Добро пожаловать, босс!</b>\n\n" + BOSS_COMMANDS
    if await db.has_active_role(uid, "manager"):
        return "💼 <b>Добро пожаловать, менеджер!</b>\n\n" + MANAGER_COMMANDS
    return texts.WELCOME + "\n\n" + USER_COMMANDS


async def _welcome_kb(uid: int):
    if uid == config.owner_id or await db.has_active_role(uid, "manager"):
        return admin_menu()
    return main_menu()


# ---------- /start с рефералкой ----------

@router.message(CommandStart(deep_link=True))
async def start_with_link(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = message.from_user.id

    ref_code = (command.args or "").strip()
    referrer_id = None
    if ref_code.startswith("ref_"):
        referrer_user = await db.find_by_ref_code(ref_code)
        if referrer_user:
            referrer_id = referrer_user["telegram_id"]

    await db.get_or_create_user(message.from_user, referrer_id=referrer_id)

    extra = ""
    if referrer_id:
        extra = f"🎁 Вы перешли по приглашению от <code>{referrer_id}</code>\n\n"

    await message.answer(extra + await _welcome_text(uid), reply_markup=await _welcome_kb(uid), parse_mode="HTML")


# ---------- Обычный /start ----------

@router.message(CommandStart())
async def start_plain(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    await db.get_or_create_user(message.from_user)
    await message.answer(await _welcome_text(uid), reply_markup=await _welcome_kb(uid), parse_mode="HTML")


# ---------- /cancel ----------

@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Диалог сброшен.", reply_markup=main_menu())


# ---------- /help ----------

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(await _welcome_text(message.from_user.id), parse_mode="HTML")


# ==========================================
# КНОПКИ ГЛАВНОГО МЕНЮ
# ==========================================

@router.message(F.text == "🛒 Заказать разработку")
async def menu_order(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ClientForm.title)
    await message.answer(texts.CLIENT_ASK_TITLE, parse_mode="HTML", reply_markup=cancel_kb_safe())


@router.message(F.text == "👨‍💻 Стать разработчиком")
async def menu_dev(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "dev")
    if role and role["status"] == "active":
        return await message.answer(f"Вы уже разработчик. Уровень: <b>{role['level']}</b>.", parse_mode="HTML")
    if role and role["status"] == "pending":
        return await message.answer("Ваша заявка на модерации. Мы свяжемся с вами.")
    await state.set_state(DevForm.name)
    await message.answer(texts.DEV_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb_safe())


@router.message(F.text == "🤝 Стать партнёром")
async def menu_partner(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    role = await db.get_role(uid, "partner")
    if role and role["status"] == "active":
        return await message.answer("Вы уже партнёр SYNTH.")
    if role and role["status"] == "pending":
        return await message.answer("Ваша заявка на партнёрство отправлена CEO на рассмотрение.")
    await state.set_state(PartnerForm.name)
    await message.answer(texts.PARTNER_ASK_NAME, parse_mode="HTML", reply_markup=cancel_kb_safe())


@router.message(F.text == "🔗 Моя ссылка на скидку")
async def menu_ref_link(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    await db.get_or_create_user(message.from_user)
    code = f"ref_{uid}"
    await db.set_ref_code(uid, code)
    link = f"https://t.me/{config.bot_username}?start={code}"
    await message.answer(texts.PR_LINK_TEXT.format(link=link), parse_mode="HTML")


@router.message(F.text == "ℹ️ О нас")
async def about(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await db.get_setting("about"), parse_mode="HTML")


@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    await message.answer(texts.SUPPORT_ASK_MSG, parse_mode="HTML", reply_markup=cancel_kb_safe())


@router.message(F.text == "📊 Моя статистика")
async def my_stats(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    discount = await db.get_user_discount(uid)
    lines = [
        f"<b>Ваш ID:</b> <code>{uid}</code>",
        f"🎁 <b>Ваша скидка:</b> <b>{discount}%</b> (1% за каждого клиента)",
    ]
    if await db.has_active_role(uid, "pr"):
        s = await db.pr_stats(uid)
        lines += [
            "", "<b>📣 Статистика пиарщика:</b>",
            f"Клиентов: <b>{s['clients']}</b>",
            f"Заказов: <b>{s['orders']}</b>",
            f"Оборот: <b>{s['total']} ⭐</b>",
        ]
    await message.answer("\n".join(lines), parse_mode="HTML")


# ==========================================
# АДМИНСКИЕ КНОПКИ (только для owner/manager)
# ==========================================

@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu())


@router.message(F.text == "📈 Статистика бота")
async def admin_stats_button(message: Message):
    uid = message.from_user.id
    if not (uid == config.owner_id or await db.has_active_role(uid, "manager")):
        return  # молча игнорируем
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
    lines = ["<b>👨‍💻 Разработчики:</b>"]
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


@router.message(F.text == "⚙️ Настройки")
async def admin_settings_button(message: Message):
    if message.from_user.id != config.owner_id:
        return
    await message.answer(
        "<b>⚙️ Настройки</b>\n\n"
        "• <code>/set_about &lt;текст&gt;</code>\n"
        "• <code>/add_manager &lt;id&gt;</code>\n"
        "• <code>/add_pr &lt;id&gt;</code>\n"
        "• <code>/backup_db</code> — бэкап БД\n"
        "• <code>/restart_bot</code>",
        parse_mode="HTML",
    )


# ---------- Вспомогательная кнопка отмены ----------

def cancel_kb_safe():
    from keyboards import cancel_kb
    return cancel_kb()
