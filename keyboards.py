from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def client_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Заказать разработку"), KeyboardButton(text="👨‍💻 Стать разработчиком")],
        [KeyboardButton(text="🤝 Стать партнёром"), KeyboardButton(text="🔗 Моя реферальная ссылка")],
        [KeyboardButton(text="📂 Мои заявки"), KeyboardButton(text="🔍 Проверить статус заявки")],
        [KeyboardButton(text="ℹ️ О нас"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="🏠 Главное меню")], # <-- КНОПКА СПАСЕНИЯ
    ], resize_keyboard=True, input_field_placeholder="Выберите действие 👇")

def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Все заявки (Тикеты)"), KeyboardButton(text="👥 Управление командами")],
        [KeyboardButton(text="👨‍💻 Разработчики"), KeyboardButton(text="🛡️ Модерация")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🚫 Баны")],
        [KeyboardButton(text="🏠 Главное меню (Клиент)")],
    ], resize_keyboard=True, input_field_placeholder="Панель управления 👑")

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отмена"), KeyboardButton(text="🏠 Главное меню")]
    ], resize_keyboard=True)

def manage_teams_kb(teams: list) -> InlineKeyboardMarkup:
    keyboard = []
    status_emoji = {"free": "🟢 Свободна", "busy": "🔴 Занята", "resting": "🟡 Отдыхает", "incomplete": "⚪ Неполная"}
    for t in teams:
        current_status = status_emoji.get(t["status"], t["status"])
        keyboard.append([InlineKeyboardButton(text=f"{t['team_name']}: {current_status}", callback_data=f"team_cycle_{t['team_name']}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
