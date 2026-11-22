"""
SYNTH Platform v2.0 - Служба поддержки
=======================================
Обработка обращений в поддержку, создание тикетов и уведомление группы менеджеров.
Включает детальное логирование для диагностики проблем с доставкой.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import db
from config import config
from states import SupportForm
from keyboards import client_main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# 1. ЗАПУСК ПОДДЕРЖКИ
# ==========================================
@router.message(F.text == "🆘 Поддержка")
async def menu_support(message: Message, state: FSMContext):
    logger.info(f"[SUPPORT] User {message.from_user.id} opened support")
    await state.clear()
    await state.set_state(SupportForm.waiting_message)
    await message.answer(
        "🆘 <b>Служба поддержки SYNTH</b>\n\n"
        "Опишите вашу проблему или вопрос максимально подробно. Наш менеджер ответит вам в этом чате.\n\n"
        "<i>Для отмены введите: Отмена</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

# ==========================================
# 2. ОБРАБОТКА СООБЩЕНИЯ И СОЗДАНИЕ ТИКЕТА
# ==========================================
@router.message(SupportForm.waiting_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    logger.info(f"[SUPPORT] User {message.from_user.id} sent support message: {message.text[:50] if message.text else '[Media]'}")
    
    # 1. Проверка на отмену
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Обращение отменено.", reply_markup=client_main_menu())
    
    # 2. Проверка на пустое сообщение
    if not message.text and not message.photo:
        return await message.answer("⚠️ Пожалуйста, отправьте текстовое сообщение или фото.", reply_markup=cancel_kb())
    
    user_id = message.from_user.id
    
    # 3. Проверка на бан
    if await db.is_banned(user_id):
        await state.clear()
        return await message.answer("🚫 Ваш аккаунт заблокирован.", reply_markup=client_main_menu())
    
    # 4. Получение или создание пользователя
    user = await db.get_user(user_id)
    if not user:
        user = await db.get_or_create_user(message.from_user)
    
    # 5. Создание тикета в БД
    try:
        ticket = await db.create_ticket(
            user_id=user['telegram_id'],
            channel='tg',
            type='support',
            title='Обращение в поддержку',
            description=message.text or "[Отправлено фото/медиа]"
        )
        ticket_number = ticket['ticket_number']
        logger.info(f"[SUPPORT] Ticket {ticket_number} created for user {user_id}")
    except Exception as db_err:
        logger.error(f"[SUPPORT] DB ERROR creating ticket: {db_err}", exc_info=True)
        return await message.answer("❌ Произошла системная ошибка при создании тикета. Попробуйте позже.", reply_markup=client_main_menu())
    
    # 6. Ответ пользователю (Гарантированный)
    response_text = (
        f"✅ <b>Ваше обращение успешно принято!</b>\n\n"
        f"🎫 <b>Ваш тикет:</b> <code>{ticket_number}</code>\n\n"
        f"Мы уже получили ваше сообщение. Менеджер свяжется с вами в этом чате в ближайшее время.\n"
        f"Вы также можете проверить статус командой: <code>/status {ticket_number}</code>"
    )
    await message.answer(response_text, parse_mode="HTML", reply_markup=client_main_menu())
    await state.clear()
    
    # 7. 🔥 ОТПРАВКА УВЕДОМЛЕНИЯ В ГРУППУ ПОДДЕРЖКИ (С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ)
    user_link = f"<a href=\"tg://user?id={user_id}\">{message.from_user.username or 'Клиент'}</a>"
    header = (
        f"🆘 <b>Новый тикет поддержки: {ticket_number}</b>\n"
        f"{'─' * 35}\n"
        f"👤 <b>Клиент:</b> {user_link} (<code>{user_id}</code>)\n"
        f"💬 <b>Сообщение:</b>\n{message.text or '[Медиа вложение]'}"
    )
    
    # Кнопки для менеджера в группе
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Взять в работу", callback_data=f"ticket_status_{ticket_number}_in_progress")],
        [InlineKeyboardButton(text="✅ Решено / Закрыть", callback_data=f"ticket_status_{ticket_number}_closed")]
    ])
    
    target_group = config.support_group_id
    
    # Проверка: указан ли ID группы корректно
    if not target_group or target_group == 0:
        logger.warning("[SUPPORT] support_group_id не настроен (равен 0 или пуст). Уведомление в группу не отправлено.")
        # Фоллбэк: отправим CEO в личку, чтобы не потерять заявку
        try:
            await bot.send_message(config.owner_id, f"⚠️ <b>Внимание!</b> support_group_id не настроен.\nНовый тикет: {ticket_number}\nКлиент: {user_link}", parse_mode="HTML")
        except:
            pass
        return

    try:
        await bot.send_message(target_group, header, parse_mode="HTML", reply_markup=kb)
        logger.info(f"[SUPPORT] ✅ SUCCESS: Notification sent to support group {target_group}")
    except Exception as e:
        # 🔥 ЗДЕСЬ МЫ УВИДИМ ТОЧНУЮ ПРИЧИНУ, ПОЧЕМУ НЕ РАБОТАЛО РАНЬШЕ
        error_msg = str(e)
        logger.error(f"[SUPPORT] ❌ FAILED to send to group {target_group}. Error: {error_msg}", exc_info=True)
        
        # Если ошибка в том, что бот не админ или ID неверный, мы об этом узнаем из лога.
        # Типичные ошибки: "Chat not found" (неверный ID) или "Forbidden: bot is not a member" (нет прав админа)
