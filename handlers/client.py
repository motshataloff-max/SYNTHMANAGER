from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
import texts
from states import ClientForm
from keyboards import client_main_menu, cancel_kb
from config import config

router = Router()

@router.message(ClientForm.title)
async def process_title(message: Message, state: FSMContext):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    if not message.text or len(message.text) < 5:
        return await message.answer("⚠️ Слишком коротко. Опишите задачу подробнее.", reply_markup=cancel_kb())
    await state.update_data(title=message.text)
    await state.set_state(ClientForm.description)
    await message.answer(texts.CLIENT_ASK_DESCRIPTION, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.description)
async def process_description(message: Message, state: FSMContext):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    await state.update_data(description=message.text or "[Без описания]")
    await state.set_state(ClientForm.budget)
    await message.answer(texts.CLIENT_ASK_BUDGET, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.budget)
async def process_budget(message: Message, state: FSMContext):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    budget_text = message.text.replace(" ", "").replace("₽", "").replace("р", "").replace("руб", "")
    if not budget_text.isdigit() or int(budget_text) < 100:
        return await message.answer("⚠️ Укажите число в рублях (минимум 100 ₽).", reply_markup=cancel_kb())
    await state.update_data(budget=int(budget_text))
    await state.set_state(ClientForm.contact_info)
    await message.answer(texts.CLIENT_ASK_CONTACT, parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.contact_info)
async def process_contact(message: Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() in ["отмена", "cancel", "❌ отмена"]:
        await state.clear()
        return await message.answer("❌ Заявка отменена.", reply_markup=client_main_menu())
    if not message.text or len(message.text) < 3:
        return await message.answer("⚠️ Укажите корректный контакт.", reply_markup=cancel_kb())
    
    data = await state.get_data()
    user = await db.get_or_create_user(message.from_user)
    
    # Создаем тикет проекта
    ticket = await db.create_ticket(
        user_id=user['telegram_id'],
        channel='tg',
        type='project',
        title=data['title'],
        description=f"{data['description']}\n\n📱 Контакт: {message.text}\n💰 Бюджет: {data['budget']} ₽",
        budget=data['budget']
    )
    
    await state.clear()
    
    response = (
        f"✅ <b>Ваша заявка на разработку успешно создана!</b>\n\n"
        f"📋 Номер заявки: {ticket['id']}\n"
        f"🎫 Ваш тикет: <code>{ticket['ticket_number']}</code>\n\n"
        f"📝 <b>Задача:</b> {data['title']}\n"
        f"💰 <b>Бюджет:</b> {data['budget']} ₽\n\n"
        f"Сохраните номер тикета. Менеджер свяжется с вами в течение 15 минут."
    )
    await message.answer(response, parse_mode="HTML", reply_markup=client_main_menu())
    
    # Уведомление в группу менеджеров
    user_link = f"<a href=\"tg://user?id={message.from_user.id}\">{message.from_user.username or 'Клиент'}</a>"
    header = (
        f"🛒 <b>Новая заявка на разработку: {ticket['ticket_number']}</b>\n"
        f"👤 <b>Клиент:</b> {user_link} (<code>{message.from_user.id}</code>)\n"
        f"📝 <b>Задача:</b> {data['title']}\n"
        f"💰 <b>Бюджет:</b> {data['budget']} ₽\n"
        f"📱 <b>Контакт:</b> {message.text}\n\n"
        f"📄 <b>Описание:</b>\n{data['description']}"
    )
    try:
        await bot.send_message(config.admin_group_id or config.ceo_group_id, header, parse_mode="HTML")
    except Exception as e:
        pass
