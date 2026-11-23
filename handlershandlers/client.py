"""
SYNTH Platform v2.0 - Воронка заказа разработки
================================================
Обработка формы заказа: название → описание → бюджет → контакт → создание тикета.
Все шаги логируются для отладки.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import texts
from states import ClientForm
from keyboards import client_main_menu, cancel_kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# ШАГ 1: ВВОД НАЗВАНИЯ ПРОЕКТА
# ==========================================
@router.message(ClientForm.title)
async def process_title(message: Message, state: FSMContext):
    logger.info(f"[CLIENT] User {message.from_user.id} entered title: {message.text[:50] if message.text else '[no text]'}")
    
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    
    if not message.text or len(message.text) < 5:
        return await message.answer("⚠️ Слишком коротко. Опишите задачу подробнее (минимум 5 символов).", reply_markup=cancel_kb())
    
    await state.update_data(title=message.text)
    await state.set_state(ClientForm.description)
    logger.info(f"[CLIENT] User {message.from_user.id} moved to description step")
    await message.answer(texts.CLIENT_ASK_DESCRIPTION, parse_mode="HTML", reply_markup=cancel_kb())

# ==========================================
# ШАГ 2: ВВОД ОПИСАНИЯ
# ==========================================
@router.message(ClientForm.description)
async def process_description(message: Message, state: FSMContext):
    logger.info(f"[CLIENT] User {message.from_user.id} entered description: {message.text[:50] if message.text else '[no text]'}")
    
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    
    await state.update_data(description=message.text or "[Без описания]")
    await state.set_state(ClientForm.budget)
    logger.info(f"[CLIENT] User {message.from_user.id} moved to budget step")
    await message.answer(texts.CLIENT_ASK_BUDGET, parse_mode="HTML", reply_markup=cancel_kb())

# ==========================================
# ШАГ 3: ВВОД БЮДЖЕТА
# ==========================================
@router.message(ClientForm.budget)
async def process_budget(message: Message, state: FSMContext):
    logger.info(f"[CLIENT] User {message.from_user.id} entered budget: {message.text}")
    
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    
    # Очищаем текст от символов валюты
    budget_text = message.text.replace(" ", "").replace("₽", "").replace("р", "").replace("руб", "").replace(",", "")
    
    if not budget_text.isdigit() or int(budget_text) < 100:
        return await message.answer("⚠️ Укажите число в рублях (минимум 100 ₽).\n\nПример: <code>50000</code>", parse_mode="HTML", reply_markup=cancel_kb())
    
    budget = int(budget_text)
    await state.update_data(budget=budget)
    await state.set_state(ClientForm.contact_info)
    logger.info(f"[CLIENT] User {message.from_user.id} moved to contact step with budget {budget} ₽")
    await message.answer(texts.CLIENT_ASK_CONTACT, parse_mode="HTML", reply_markup=cancel_kb())

# ==========================================
# ШАГ 4: ВВОД КОНТАКТА + СОЗДАНИЕ ТИКЕТА
# ==========================================
@router.message(ClientForm.contact_info)
async def process_contact(message: Message, state: FSMContext, bot: Bot):
    logger.info(f"[CLIENT] User {message.from_user.id} entered contact: {message.text}")
    
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    
    if not message.text or len(message.text) < 3:
        return await message.answer("⚠️ Укажите корректный контакт (минимум 3 символа).", reply_markup=cancel_kb())
    
    contact_info = message.text
    
    try:
        # Получаем все данные из состояния
        data = await state.get_data()
        logger.info(f"[CLIENT] State data: {data}")
        
        # Проверяем, что все данные на месте
        if not data.get('title') or not data.get('description') or not data.get('budget'):
            logger.error(f"[CLIENT] Missing data in state: {data}")
            await state.clear()
            return await message.answer(
                "❌ Произошла ошибка при сохранении данных. Пожалуйста, начните заново: /start",
                reply_markup=client_main_menu()
            )
        
        # Получаем или создаём пользователя
        user = await db.get_or_create_user(message.from_user)
        user_id = user['telegram_id']
        logger.info(f"[CLIENT] User resolved: {user_id}")
        
        # 🔥 Создаём тикет проекта
        ticket = await db.create_ticket(
            user_id=user_id,
            channel='tg',
            type='project',
            title=data['title'],
            description=f"{data['description']}\n\n📱 Контакт: {contact_info}\n💰 Бюджет: {data['budget']} ₽",
            budget=data['budget']
        )
        ticket_number = ticket['ticket_number']
        logger.info(f"[CLIENT] Ticket created: {ticket_number}")
        
        # Очищаем состояние
        await state.clear()
        
        # 🔥 Отправляем подтверждение клиенту (ИСПРАВЛЕНО: убрано ticket['id'])
        response = (
            f"✅ <b>Ваша заявка на разработку успешно создана!</b>\n\n"
            f"🎫 <b>Ваш тикет:</b> <code>{ticket_number}</code>\n\n"
            f"📝 <b>Задача:</b> {data['title']}\n"
            f"💰 <b>Бюджет:</b> {data['budget']} ₽\n"
            f"📱 <b>Контакт:</b> {contact_info}\n\n"
            f"💡 Сохраните номер тикета. Менеджер свяжется с вами в течение 15 минут.\n"
            f"Проверить статус можно командой <code>/status {ticket_number}</code> или просто отправив номер боту."
        )
        await message.answer(response, parse_mode="HTML", reply_markup=client_main_menu())
        
        # 🔥 Уведомление в группу менеджеров
        user_link = f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.username or 'Клиент'}</a>"
        header = (
            f"🛒 <b>Новая заявка на разработку: {ticket_number}</b>\n"
            f"{'─' * 30}\n"
            f"👤 <b>Клиент:</b> {user_link} (<code>{message.from_user.id}</code>)\n"
            f"📝 <b>Задача:</b> {data['title']}\n"
            f"💰 <b>Бюджет:</b> {data['budget']} ₽\n"
            f"📱 <b>Контакт:</b> {contact_info}\n\n"
            f"📄 <b>Описание:</b>\n{data['description']}"
        )
        
        # Определяем, куда слать уведомление
        target_group = None
        if config.admin_group_id and config.admin_group_id != 0:
            target_group = config.admin_group_id
        elif config.ceo_group_id and config.ceo_group_id != 0:
            target_group = config.ceo_group_id
        elif config.owner_id:
            target_group = config.owner_id  # Фоллбэк: шлём CEO в личку
        
        if target_group:
            try:
                await bot.send_message(target_group, header, parse_mode="HTML")
                logger.info(f"[CLIENT] Notification sent to group/user {target_group}")
            except Exception as e:
                logger.error(f"[CLIENT] Failed to send notification to {target_group}: {e}", exc_info=True)
        else:
            logger.warning("[CLIENT] No target group configured for notifications")
        
    except Exception as e:
        logger.error(f"[CLIENT] CRITICAL ERROR in process_contact: {e}", exc_info=True)
        await state.clear()
        await message.answer(
            f"❌ Произошла ошибка при создании заявки.\n\n"
            f"Техническая информация:\n<code>{type(e).__name__}: {e}</code>\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode="HTML",
            reply_markup=client_main_menu()
        )


