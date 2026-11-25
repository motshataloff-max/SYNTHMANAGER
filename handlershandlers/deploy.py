import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import db
from states import DeployForm
from keyboards import cancel_kb, client_main_menu, skip_button, hosting_kb, domain_kb
from config import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🚀 Поднять код на сервера")
async def start_deploy(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(DeployForm.name)
    await message.answer("🚀 <b>Поднять код на сервера</b>\n\n1️⃣ <b>Как к вам обращаться?</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DeployForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(DeployForm.username)
    await message.answer("2️⃣ <b>Telegram username</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DeployForm.username)
async def process_username(message: Message, state: FSMContext):
    await state.update_data(username=f"@{message.text.strip().lstrip('@')}")
    await state.set_state(DeployForm.phone)
    await message.answer("3️⃣ <b>Номер телефона</b>", parse_mode="HTML", reply_markup=cancel_kb())

@router.message(DeployForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await db.update_user_phone(message.from_user.id, message.text.strip())
    await state.set_state(DeployForm.repo)
    await message.answer("4️⃣ <b>Ссылка на код</b> (или нажмите Пропустить)", parse_mode="HTML", reply_markup=skip_button("skip_repo"))

@router.callback_query(F.data == "skip_repo")
async def skip_repo(callback: Message, state: FSMContext):
    await state.update_data(repo="Нет")
    await state.set_state(DeployForm.hosting)
    await callback.message.edit_text("5️⃣ <b>Какой хостинг нужен?</b>", parse_mode="HTML", reply_markup=hosting_kb())

@router.message(DeployForm.repo)
async def process_repo(message: Message, state: FSMContext):
    await state.update_data(repo=message.text.strip())
    await state.set_state(DeployForm.hosting)
    await message.answer("5️⃣ <b>Какой хостинг нужен?</b>", parse_mode="HTML", reply_markup=hosting_kb())

@router.callback_query(F.data.startswith("hosting_"))
async def select_hosting(callback: Message, state: FSMContext):
    await state.update_data(hosting=callback.data.replace("hosting_", ""))
    await state.set_state(DeployForm.domain)
    await callback.message.edit_text("6️⃣ <b>Есть ли домен?</b>", parse_mode="HTML", reply_markup=domain_kb())

@router.callback_query(F.data.startswith("domain_"))
async def select_domain(callback: Message, state: FSMContext):
    await state.update_data(domain=callback.data.replace("domain_", ""))
    await state.set_state(DeployForm.requirements)
    await callback.message.edit_text("7️⃣ <b>Доп. требования</b> (или Пропустить)", parse_mode="HTML", reply_markup=skip_button("skip_req"))

@router.callback_query(F.data == "skip_req")
async def skip_requirements(callback: Message, state: FSMContext):
    await state.update_data(requirements="Нет")
    await finish_deploy(callback.message, state)

@router.message(DeployForm.requirements)
async def process_requirements(message: Message, state: FSMContext):
    await state.update_data(requirements=message.text.strip())
    await finish_deploy(message, state)

async def finish_deploy(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    desc = f"👤 {data['name']}\n📱 {data['username']}\n📞 {data['phone']}\n🔗 {data['repo']}\n🖥️ {data['hosting']}\n🌐 {data['domain']}\n💬 {data['requirements']}"
    ticket = await db.create_ticket(user_id=message.from_user.id, channel="tg", type="deploy", title="🚀 Поднять код на сервера", description=desc)
    await message.answer("✅ Заявка отправлена! Менеджер свяжется в течение 24 часов.", parse_mode="HTML", reply_markup=client_main_menu())
    try:
        await message.bot.send_message(config.ceo_group_id, f"🔔 ЗАЯВКА: {ticket['ticket_number']}\n{desc}", parse_mode="HTML")
    except: pass
