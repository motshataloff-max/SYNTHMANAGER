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

async def _check_cancel(message: Message, state: FSMContext) -> bool:
    if message.text and any(word in message.text.lower() for word in ["отмена", "cancel", "❌ отмена"]):
        await state.clear()
        await message.answer("❌ Заказ отменен.", reply_markup=main_menu())
        return True
    return False

async def _require_text(message: Message, state: FSMContext) -> bool:
    if not message.text:
        await message.answer("⚠️ Пожалуйста, отправьте текстом, а не файлом или стикером.", reply_markup=cancel_kb())
        return True
    return False

@router.message(ClientForm.title)
async def process_title(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(title=message.text.strip())
    await state.set_state(ClientForm.description)
    await message.answer("📝 <b>Шаг 2/7:</b> Кратко опишите, что нужно сделать (ТЗ):", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.description)
async def process_description(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if await _require_text(message, state): return
    await state.update_data(description=message.text.strip())
    await state.set_state(ClientForm.budget)
    await message.answer("💰 <b>Шаг 3/7:</b> Бюджет в Telegram Stars (только число, минимум 50):", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.budget)
async def process_budget(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if not message.text or not message.text.isdigit() or int(message.text) < 50:
        return await message.answer("⚠️ Бюджет должен быть числом и не меньше 50 ⭐. Попробуйте еще раз:", reply_markup=cancel_kb())
    await state.update_data(budget=int(message.text))
    await state.set_state(ClientForm.contact)
    await message.answer("📞 <b>Шаг 4/7:</b> Как с вами связаться? (Напишите ваш @username или номер телефона):", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.contact)
async def process_contact(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if not message.text or len(message.text.strip()) < 3:
        return await message.answer("⚠️ Контакт слишком короткий. Напишите @username или номер телефона:", reply_markup=cancel_kb())
    await state.update_data(contact=message.text.strip())
    await state.set_state(ClientForm.country)
    await message.answer("🌍 <b>Шаг 5/7:</b> Из какой вы страны?", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.country)
async def process_country(message: Message, state: FSMContext):
    if await _check_cancel(message, state): return
    if not message.text: return
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
    if await _check_cancel(message, state): return
    if not message.text or not message.text.isdigit() or int(message.text) < 18:
        await state.clear()
        return await message.answer("⚠️ Мы работаем только с совершеннолетними (18+). Заявка отклонена.", reply_markup=main_menu())
    
    await state.update_data(age=int(message.text))
    await state.set_state(ClientForm.sam)
    await message.answer("📄 <b>Шаг 7/7:</b> Вы самозанятый (НПД)? (Напишите Да или Нет)", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(ClientForm.sam)
async def process_sam(message: Message, state: FSMContext):
    try:
        if await _check_cancel(message, state): return
        if not message.text:
            return await message.answer("⚠️ Пожалуйста, напишите Да или Нет текстом.", reply_markup=cancel_kb())
            
        is_sam = 1 if message.text.lower() in ["да", "yes", "1"] else 0
        data = await state.get_data()
        await state.clear()

        client_id = message.from_user.id
        username = message.from_user.username
        user_link = f"<a href=\"tg://user?id={client_id}\">{username or 'Профиль'}</a>"

        # 1. Создаем/обновляем пользователя
        user = await db.get_or_create_user(message.from_user)
        referrer_id = user["referrer_id"] if user else None
        
        # 2. Назначаем менеджера (используем исправленную функцию next_recipient)
        try:
            manager_id = await db.next_recipient(config.owner_id)
        except Exception as e:
            logger.error(f"Ошибка назначения менеджера: {e}")
            manager_id = config.owner_id # Фоллбэк на CEO

        # 3. Создаем проект в БД
        project_id = await db.create_project(
            client_id=client_id,
            title=data.get("title", "Без названия"),
            description=data.get("description", "Без описания"),
            budget=data.get("budget", 0),
            contact_info=data.get("contact", "Не указан"),
            country=data.get("country", "Не указана"),
            is_samozanyat=is_sam,
            referrer_id=referrer_id,
            manager_id=manager_id
        )
        
        # 4. Отвечаем клиенту (ВСЕГДА, даже если что-то пошло не так с уведомлением админам)
        await message.answer(
            f"✅ <b>Ваша заявка #{project_id} успешно создана!</b>\n\n"
            f"📌 <b>Название:</b> {data.get('title')}\n"
            f"💰 <b>Бюджет:</b> {data.get('budget')} ⭐\n\n"
            f"Менеджер SYNTH свяжется с вами в ближайшее время.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

        # 5. Уведомление в группу администраторов
        notification = (
            f"🆕 <b>Новый заказ!</b>\n\n"
            f"📌 <b>ID:</b> <code>{project_id}</code>\n"
            f"👤 <b>Клиент:</b> {user_link} (<code>{client_id}</code>)\n"
            f"📝 <b>ТЗ:</b> {data.get('title')}\n{data.get('description')}\n"
            f"💰 <b>Бюджет:</b> {data.get('budget')} ⭐\n"
            f"🌍 <b>Страна:</b> {data.get('country')} | 🎂 <b>Возраст:</b> {data.get('age')}\n"
            f"📞 <b>Контакт:</b> {data.get('contact')}\n"
            f"📄 <b>Самозанятый:</b> {'Да' if is_sam else 'Нет'}"
        )
        try:
            await message.bot.send_message(config.admin_group_id, notification, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка отправки в группу админов: {e}")
            # Фоллбэк: если в группу не вышло, шлем лично CEO
            await message.bot.send_message(config.owner_id, notification + "\n\n⚠️ Бот не смог написать в группу админов!", parse_mode="HTML")

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В КЛИЕНТЕ: {e}")
        await message.answer("❌ Произошла техническая ошибка. Мы уже чиним! Попробуйте позже или напишите в поддержку.", reply_markup=main_menu())
