import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
from config import config
from states import ClientForm
from keyboards import main_menu, cancel_kb

logger = logging.getLogger(__name__)
router = Router()

async def check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and message.text.lower() in ["отмена", "cancel", "отменить"]:
        await state.clear()
        await message.answer("❌ Заказ отменен.", reply_markup=main_menu())
        return True
    return False

@router.message(ClientForm.title)
async def process_title(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(title=message.text.strip())
    await state.set_state(ClientForm.description)
    await message.answer("📝 <b>Шаг 2/7:</b> Кратко опишите, что нужно сделать (ТЗ):", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.description)
async def process_description(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(description=message.text.strip())
    await state.set_state(ClientForm.budget)
    await message.answer("💰 <b>Шаг 3/7:</b> Бюджет в Telegram Stars (только число):", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.budget)
async def process_budget(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    if not message.text.isdigit() or int(message.text) < 50:
        return await message.answer("⚠️ Бюджет должен быть числом и не меньше 50 ⭐. Попробуйте еще раз:", reply_markup=cancel_kb())
    await state.update_data(budget=int(message.text))
    await state.set_state(ClientForm.contact)
    await message.answer("📞 <b>Шаг 4/7:</b> Как с вами связаться? (Ваш @username или номер телефона):", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.contact)
async def process_contact(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    await state.update_data(contact=message.text.strip())
    await state.set_state(ClientForm.country)
    await message.answer("🌍 <b>Шаг 5/7:</b> Из какой вы страны?", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.country)
async def process_country(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    country = message.text.strip().lower()
    forbidden = ["сша", "usa", "украина", "ukraine", "великобритания", "uk", "евросоюз", "eu"]
    if any(f in country for f in forbidden):
        await state.clear()
        return await message.answer("🇷🇺 Извините, SYNTH не работает с представителями недружественных стран. Заявка отклонена.", reply_markup=main_menu())
    
    await state.update_data(country=message.text.strip())
    await state.set_state(ClientForm.age)
    await message.answer("🎂 <b>Шаг 6/7:</b> Сколько вам полных лет? (только число)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.age)
async def process_age(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    if not message.text.isdigit() or int(message.text) < 18:
        await state.clear()
        return await message.answer("⚠️ Мы работаем только с совершеннолетними (18+). Заявка отклонена.", reply_markup=main_menu())
    
    await state.update_data(age=int(message.text))
    await state.set_state(ClientForm.sam)
    await message.answer("📄 <b>Шаг 7/7:</b> Вы самозанятый (НПД)? (Напишите Да или Нет)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.sam)
async def process_sam(message: Message, state: FSMContext):
    if await check_cancel(message, state): return
    is_sam = 1 if message.text.lower() in ["да", "yes", "1"] else 0
    data = await state.get_data()
    await state.clear()

    client_id = message.from_user.id
    user = await db.get_user(client_id)
    referrer_id = user["referrer_id"] if user else None
    manager_id = await db.next_recipient(config.owner_id)

    try:
        project_id = await db.create_project(
            client_id=client_id, title=data["title"], description=data["description"],
            budget=data["budget"], contact_info=data["contact"], country=data["country"],
            is_samozanyat=is_sam, referrer_id=referrer_id, manager_id=manager_id
        )
        
        await message.answer(f"✅ <b>Ваша заявка #{project_id} успешно создана!</b>\nМенеджер SYNTH свяжется с вами в ближайшее время.", parse_mode="HTML", reply_markup=main_menu())

        # Уведомление в группу администраторов
        # TODO: Добавить message_thread_id для темы "Новые заказы", когда получим ID тем
        notification = (
            f"🆕 <b>Новый заказ!</b>\n\n"
            f"📌 <b>ID:</b> <code>{project_id}</code>\n"
            f"👤 <b>Клиент:</b> <code>{client_id}</code> (@{message.from_user.username})\n"
            f"📝 <b>ТЗ:</b> {data['title']}\n{data['description']}\n"
            f"💰 <b>Бюджет:</b> {data['budget']} ⭐\n"
            f"🌍 <b>Страна:</b> {data['country']} | 🎂 <b>Возраст:</b> {data['age']}\n"
            f"📞 <b>Контакт:</b> {data['contact']}\n"
            f"📄 <b>Самозанятый:</b> {'Да' if is_sam else 'Нет'}"
        )
        await message.bot.send_message(config.admin_group_id, notification, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка создания проекта: {e}")
        await message.answer("❌ Произошла ошибка при создании заказа.", reply_markup=main_menu())
