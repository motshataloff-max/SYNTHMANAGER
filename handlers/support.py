import logging
import re
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import SupportForm
from keyboards import main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Обращение в поддержку отменено.", reply_markup=main_menu())
        return True
    return False

# ==========================================
# 1. КЛИЕНТ ПИШЕТ В ПОДДЕРЖКУ
# ==========================================

@router.message(SupportForm.waiting_message)
async def process_message(message: Message, state: FSMContext):
    try:
        if await _check_cancel(message, state): return
        if not message.text:
            return await message.answer("⚠️ Пожалуйста, опишите проблему текстом.", reply_markup=cancel_kb())
        
        user_id = message.from_user.id
        username = message.from_user.username or "Нет username"
        user_link = f"<a href=\"tg://user?id={user_id}\">{username}</a>"
        
        await state.clear()
        
        # Отвечаем клиенту
        await message.answer(
            f"✅ <b>Сообщение принято!</b>\n\n"
            f"Оператор SYNTH ответит вам в личных сообщениях.\n"
            f"<i>Чтобы продолжить диалог, просто пишите боту.</i>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

        # Формируем сообщение для группы поддержки с ID клиента в конце
        support_text = (
            f"🆘 <b>Новое сообщение в поддержку!</b>\n\n"
            f"👤 <b>От:</b> {user_link} (<code>{user_id}</code>)\n"
            f"💬 <b>Текст:</b> {message.text.strip()}\n\n"
            f"---\n🆔 USER_ID: {user_id}"
        )
        
        try:
            await message.bot.send_message(config.support_group_id, support_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка отправки в Support группу: {e}")
            await message.bot.send_message(config.owner_id, support_text + "\n\n⚠️ Не удалось отправить в группу Support!", parse_mode="HTML")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В SUPPORT: {e}")
        await message.answer("❌ Произошла техническая ошибка.", reply_markup=main_menu())

# ==========================================
# 2. ХЕЛПЕР/МЕНЕДЖЕР ОТВЕЧАЕТ В ГРУППЕ (МОСТ)
# ==========================================

@router.message(F.chat.id == config.support_group_id, F.reply_to_message)
async def support_reply_bridge(message: Message, bot: Bot):
    """Перехватывает ответ хелпера на сообщение бота и отправляет его клиенту."""
    # Проверяем, что ответ идет на сообщение от бота
    if not message.reply_to_message.from_user or message.reply_to_message.from_user.id != bot.id:
        return
    
    # Ищем ID клиента в тексте исходного сообщения
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    if not original_text or "🆔 USER_ID:" not in original_text:
        return

    # Извлекаем ID (берем число после "🆔 USER_ID:")
    match = re.search(r"🆔 USER_ID:\s*(\d+)", original_text)
    if not match:
        return
    
    target_user_id = int(match.group(1))

    try:
        await bot.send_message(
            target_user_id,
            f"💬 <b>Ответ от поддержки SYNTH:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        # Ставим реакцию или просто молча подтверждаем (чтобы не спамить в чат)
    except Exception as e:
        logger.error(f"Ошибка отправки ответа клиенту {target_user_id}: {e}")
        await message.answer(f"❌ Не удалось доставить сообщение пользователю <code>{target_user_id}</code>. Возможно, он заблокировал бота.", parse_mode="HTML")
