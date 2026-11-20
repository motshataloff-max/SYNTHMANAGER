import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import SupportForm
from keyboards import main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

# Счётчик сообщений клиента без ответа хелпера (для защиты от спама)
_user_msg_counter = {}

async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Обращение в поддержку отменено.", reply_markup=main_menu())
        return True
    return False

async def _ensure_topic(message: Message, state: FSMContext, bot: Bot) -> tuple[int, int]:
    """Создаёт или возвращает существующую тему для клиента. Возвращает (ticket_id, topic_id)."""
    user_id = message.from_user.id
    
    # Проверяем, есть ли уже открытый тикет
    ticket = await db.find_open_ticket_by_user(user_id)
    if ticket and ticket["topic_id"]:
        return ticket["id"], ticket["topic_id"]
    
    # Создаём новый тикет
    ticket_id = await db.create_ticket(user_id, message.text or "[вложение]")
    
    # Создаём тему в группе поддержки
    try:
        topic = await bot.create_forum_topic(
            chat_id=config.support_group_id,
            name=f"🎫 #{ticket_id}"
        )
        topic_id = topic.message_thread_id
        await db.set_ticket_topic(ticket_id, topic_id)
        
        # Шапка темы: кто клиент
        user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Профиль'}</a>"
        header = (
            f"🆘 <b>Тикет #{ticket_id}</b>\n"
            f"👤 <b>Клиент:</b> {user_link} (<code>{user_id}</code>)\n"
            f"📅 <b>Создан:</b> {message.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"──────────────────────\n\n"
        )
        await bot.send_message(
            config.support_group_id,
            header,
            message_thread_id=topic_id,
            parse_mode="HTML"
        )
        return ticket_id, topic_id
    except Exception as e:
        logger.error(f"Ошибка создания темы: {e}")
        # Фоллбэк: если не удалось создать тему (например, группа не форум), шлём в общий чат
        return ticket_id, None

async def _forward_to_topic(message: Message, topic_id: int, bot: Bot) -> None:
    """Пересылает сообщение клиента в его тему."""
    try:
        if message.text:
            await bot.send_message(
                config.support_group_id,
                f"💬 <b>Клиент пишет:</b>\n{message.text}",
                message_thread_id=topic_id,
                parse_mode="HTML"
            )
        elif message.photo:
            await bot.send_photo(
                config.support_group_id,
                message.photo[-1].file_id,
                caption=f"📷 Фото от клиента",
                message_thread_id=topic_id
            )
        elif message.document:
            await bot.send_document(
                config.support_group_id,
                message.document.file_id,
                caption=f"📎 Файл от клиента",
                message_thread_id=topic_id
            )
        else:
            await bot.send_message(
                config.support_group_id,
                "📎 [Вложение от клиента]",
                message_thread_id=topic_id
            )
    except Exception as e:
        logger.error(f"Ошибка пересылки в тему: {e}")

@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    """Главный обработчик: клиент пишет в бота → бот пересылает в его тему."""
    if await _check_cancel(message, state): return
    if not message.text and not message.photo and not message.document:
        return await message.answer("⚠️ Пожалуйста, отправьте текст, фото или файл.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    
    # Проверка на бан
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Ваш аккаунт заблокирован администрацией SYNTH.", reply_markup=main_menu())
    
    # Создаём или находим тему
    ticket_id, topic_id = await _ensure_topic(message, state, bot)
    
    # Если тема создана — пересылаем сообщение
    if topic_id:
        await _forward_to_topic(message, topic_id, bot)
    else:
        # Фоллбэк: шлём в общий чат группы
        user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Профиль'}</a>"
        try:
            await bot.send_message(
                config.support_group_id,
                f"🆘 <b>Тикет #{ticket_id}</b> от {user_link} (<code>{user_id}</code>):\n{message.text or '[вложение]'}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки в группу поддержки: {e}")
    
    # Считаем сообщения без ответа (защита от спама)
    _user_msg_counter[user_id] = _user_msg_counter.get(user_id, 0) + 1
    count = _user_msg_counter[user_id]
    
    if count == 3:
        await message.answer(
            "⏳ <b>Мы получили ваши сообщения.</b>\n\n"
            "Хелпер уже изучает их и скоро ответит. Пожалуйста, ожидайте.\n\n"
            "<i>Если хотите вернуться в главное меню, нажмите кнопку ниже.</i>",
            parse_mode="HTML",
            reply_markup=cancel_kb()
        )
    elif count > 3 and count % 3 == 0:
        await message.answer("⏳ Хелпер скоро ответит. Пожалуйста, подождите.")
    
    # Отвечаем клиенту (только на первое сообщение)
    if count == 1:
        await message.answer(
            f"✅ <b>Ваше обращение #{ticket_id} принято!</b>\n\n"
            "Хелпер SYNTH ответит вам в этом чате в ближайшее время.\n"
            "<i>Просто продолжайте писать сюда — всё будет переслано хелперу.</i>\n"
            "<i>Чтобы вернуться в меню, нажмите /cancel</i>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    
    # НЕ сбрасываем состояние — клиент продолжает писать в бота, и мы пересылаем

# ==========================================
# ОТВЕТ ХЕЛПЕРА В ТЕМЕ → КЛИЕНТУ В ЛИЧКУ
# ==========================================
@router.message(F.chat.id == config.support_group_id & F.reply_to_message & F.message_thread_id)
async def support_reply_in_topic(message: Message, bot: Bot):
    """Хелпер отвечает на сообщение в теме → бот пересылает клиенту."""
    # Проверяем, что пишет админ или хелпер
    is_admin = message.from_user.id == config.owner_id
    is_helper = await db.has_active_role(message.from_user.id, "helper")
    is_manager = await db.has_active_role(message.from_user.id, "manager")
    if not (is_admin or is_helper or is_manager):
        return
    
    topic_id = message.message_thread_id
    ticket = await db.find_ticket_by_topic(topic_id)
    if not ticket:
        return
    
    user_id = ticket["user_id"]
    
    # Пересылаем ответ клиенту
    try:
        if message.text:
            await bot.send_message(
                user_id,
                f"💬 <b>Ответ поддержки SYNTH (тикет #{ticket['id']}):</b>\n\n{message.text}",
                parse_mode="HTML"
            )
        elif message.photo:
            await bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=f"💬 Ответ поддержки SYNTH (тикет #{ticket['id']})"
            )
        elif message.document:
            await bot.send_document(
                user_id,
                message.document.file_id,
                caption=f"💬 Ответ поддержки SYNTH (тикет #{ticket['id']})"
            )
        
        # Сбрасываем счётчик сообщений клиента
        if user_id in _user_msg_counter:
            _user_msg_counter[user_id] = 0
        
        await message.answer(f"✅ Ответ доставлен клиенту.")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки клиенту: {e}. Возможно, бот заблокирован.")

# ==========================================
# ЗАКРЫТИЕ ТИКЕТА (КОГДА ХЕЛПЕР РЕШИЛ ПРОБЛЕМУ)
# ==========================================
@router.message(F.chat.id == config.support_group_id & F.text & F.text.startswith("/close"))
async def close_ticket_cmd(message: Message, bot: Bot):
    """Хелпер закрывает тикет командой /close в теме."""
    if not message.message_thread_id:
        return
    
    ticket = await db.find_ticket_by_topic(message.message_thread_id)
    if not ticket:
        return await message.answer("⚠️ Тикет не найден.")
    
    await db.close_ticket(ticket["id"])
    
    # Закрываем тему в группе
    try:
        await bot.close_forum_topic(config.support_group_id, message.message_thread_id)
    except Exception:
        pass
    
    # Уведомляем клиента
    try:
        await bot.send_message(
            ticket["user_id"],
            f"✅ <b>Ваш тикет #{ticket['id']} закрыт.</b>\n\n"
            "Если проблема не решена, напишите в поддержку снова.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await message.answer(f"🔒 Тикет #{ticket['id']} закрыт.")
