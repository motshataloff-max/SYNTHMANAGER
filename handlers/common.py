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

class BanMiddleware(BaseMiddleware):
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

USER_COMMANDS = (
    "📌 <b>Что я умею:</b>\n\n"
    "• 🛒 <b>Заказать разработку</b>\n• 👨‍💻 <b>Стать разработчиком</b>\n"
    "• 🤝 <b>Стать партнёром</b>\n• 🔗 <b>Моя ссылка на скидку</b>\n"
    "• 📊 <b>Моя статистика</b>\n• ℹ️ <b>О нас</b>\n• 🆘 <b>Поддержка</b>"
)
MANAGER_COMMANDS = "💼 <b>Меню менеджера:</b>\n• 📋 Проекты\n• 👨‍💻 Разработчики\n• 👥 Менеджеры\n• 📈 Статистика\n• 🏖 Отпуска"
BOSS_COMMANDS = (
    "👑 <b>Меню CEO:</b>\n\n"
    "👥 <code>/add_manager &lt;id&gt;</code> | <code>/add_helper &lt;id&gt;</code>\n"
    "🚫 <code>/ban &lt;id&gt;</code> | <code>/unban &lt;id&gt;</code>\n"
    "⚙️ <code>/assign &lt;id&gt;</code> | <code>/complete &lt;id&gt;</code>\n"
    "💾 <code>/backup_db</code> | <code>/restart_bot</code>"
)

MENU_BUTTONS = {
    "🛒 Заказать разработку", "👨‍💻 Стать разработчиком", "🤝 Стать партнёром",
    "🔗 Моя ссылка на скидку", "📊 Моя статистика", "ℹ️ О нас", "🆘 Поддержка",
    "🔙 Главное меню", "📈 Статистика бота", "📋 Список проектов", "👨‍💻 Разработчики",
    "👥 Менеджеры", "🏖 Управление отпусками", "👥 Управление командами",
    "📢 Глобальная рассылка", "⚙️ Настройки",
}

async def _welcome_text(uid: int) -> str:
    if uid == config.owner_id: return "👑 <b>Добро пожаловать, босс!</b>\n\n" + BOSS_COMMANDS
    if await db.has_active_role(uid, "manager"): return "💼 <b>Добро пожаловать, менеджер!</b>\n\n" + MANAGER_COMMANDS
    return texts.WELCOME + "\n\n" + USER_COMMANDS

async def _welcome_kb(uid: int):
    if uid == config.owner_id or await db.has_active_role(uid, "manager"): return admin_menu()
    return main_menu()

@router.message(CommandStart(deep_link=True))
async def start_with_link(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    ref_code = (command.args or "").strip()
    ref_message = ""
    
    if ref_code.startswith("ref_"):
        referrer_user = await db.find_by_ref_code(ref_code)
        if referrer_user:
            referrer_uid = referrer_user["telegram_id"]
            if referrer_uid == uid:
                ref_message = "⚠️ Вы не можете использовать свою собственную ссылку.\n\n"
            else:
                existing_user = await db.get_user(uid)
                if existing_user and existing_user.get("referrer_id"):
                    ref_message = "⚠️ Вы уже зарегистрированы по реферальной ссылке.\n\n"
                elif existing_user:
                    ref_message = "⚠️ Вы уже зарегистрированы в боте.\n\n"
                else:
                    ref_message = "🎁 Вы перешли по приглашению. Ваш реферер получит бонус при заказе от 500 ⭐!\n\n"
        else:
            ref_message = "⚠️ Неверная реферальная ссылка.\n\n"

    await db.get_or_create_user(message.from_user, referrer_id=(referrer_uid if ref_code.startswith("ref_") and ref_message.startswith("🎁") else None))
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

@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    existing_ticket = await db.find_open_ticket_by_user(message.from_user.id)
    if existing_ticket:
        return await message.answer(f"🆘 <b>У вас уже есть открытый тикет #{existing_ticket['id']}.</b>\nПросто напишите сообщение сюда.", parse_mode="HTML", reply_markup=main_menu())
    await message.answer(texts.SUPPORT_ASK_MSG, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(F.text == "📢 Глобальная рассылка")
async def start_broadcast_btn(message: Message, state: FSMContext):
    if message.from_user.id != config.owner_id: return
    await state.set_state(BroadcastForm.waiting_message)
    await message.answer("📢 <b>Режим рассылки активирован.</b>\nОтправьте текст. Для отмены: /cancel", parse_mode="HTML")

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.from_user.id != config.owner_id: return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit(): return await message.answer("⚠️ <code>/ban &lt;id&gt; [причина]</code>", parse_mode="HTML")
    user_id, reason = int(parts[1]), parts[2] if len(parts) > 2 else "Не указана"
    if user_id == config.owner_id: return await message.answer("⚠️ Нельзя забанить CEO.")
    await db.ban_user(user_id, reason)
    await message.answer(f"🚫 Пользователь <code>{user_id}</code> забанен.", parse_mode="HTML")
    try: await message.bot.send_message(user_id, f"🚫 Аккаунт заблокирован. Причина: {reason}", parse_mode="HTML")
    except Exception: pass

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.from_user.id != config.owner_id: return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return await message.answer("⚠️ <code>/unban &lt;id&gt;</code>", parse_mode="HTML")
    user_id = int(parts[1])
    await db.unban_user(user_id)
    await message.answer(f"✅ Пользователь <code>{user_id}</code> разбанен.", parse_mode="HTML")

# АВТО-ВОЗВРАТ В ПОДДЕРЖКУ (ИСПРАВЛЕННЫЙ ФИЛЬТР)
@router.message(F.text, ~F.text.startswith("/"), StateFilter(None))
async def auto_support_forward(message: Message, bot: Bot):
    user_id = message.from_user.id
    if user_id == config.owner_id or await db.has_active_role(user_id, "manager"): return
    if message.text in MENU_BUTTONS: return
    
    ticket = await db.find_open_ticket_by_user(user_id)
    if not ticket or not ticket["topic_id"]: return
    
    try:
        await bot.send_message(config.support_group_id, f"💬 <b>Клиент пишет:</b>\n{message.text}", message_thread_id=ticket["topic_id"], parse_mode="HTML")
        await message.answer("📨 Сообщение передано хелперу.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")
