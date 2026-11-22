"""
SYNTH Platform v2.0 - Клавиатуры
=================================
Все Reply и Inline клавиатуры для бота.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# КЛИЕНТСКОЕ МЕНЮ
# ==========================================
def client_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Заказать разработку"), KeyboardButton(text="👨‍💻 Стать разработчиком")],
        [KeyboardButton(text="🤝 Стать партнёром"), KeyboardButton(text="🔗 Моя реферальная ссылка")],
        [KeyboardButton(text="📂 Мои заявки"), KeyboardButton(text="🔍 Проверить статус заявки")],
        [KeyboardButton(text="ℹ️ О нас"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="🏠 Главное меню")],
    ], resize_keyboard=True, input_field_placeholder="Выберите действие 👇")

# ==========================================
# АДМИНСКОЕ МЕНЮ (С КНОПКОЙ ПЕРЕКЛЮЧЕНИЯ В КЛИЕНТСКИЙ РЕЖИМ)
# ==========================================
def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Все заявки (Тикеты)"), KeyboardButton(text="👥 Управление командами")],
        [KeyboardButton(text="👨‍💻 Разработчики"), KeyboardButton(text="🛡️ Модерация")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🚫 Баны")],
        [KeyboardButton(text="👤 Режим клиента"), KeyboardButton(text="🏠 Главное меню")],
    ], resize_keyboard=True, input_field_placeholder="Панель управления 👑")

# ==========================================
# КЛАВИАТУРА ОТМЕНЫ (С КНОПКОЙ ГЛАВНОГО МЕНЮ)
# ==========================================
def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отмена"), KeyboardButton(text="🏠 Главное меню")]
    ], resize_keyboard=True)

# ==========================================
# УПРАВЛЕНИЕ КОМАНДАМИ (INLINE)
# ==========================================
def manage_teams_kb(teams: list) -> InlineKeyboardMarkup:
    keyboard = []
    status_emoji = {
        "free": "🟢 Свободна", 
        "busy": "🔴 Занята", 
        "resting": "🟡 Отдыхает", 
        "incomplete": "⚪ Неполная"
    }
    for t in teams:
        current_status = status_emoji.get(t["status"], t["status"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{t['team_name']}: {current_status}", 
                callback_data=f"team_cycle_{t['team_name']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==========================================
# МОДЕРАЦИЯ РАЗРАБОТЧИКОВ (INLINE)
# ==========================================
def dev_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"dev_approve_{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"dev_reject_{user_id}")
    ]])

# ==========================================
# МОДЕРАЦИЯ ПАРТНЁРОВ (INLINE)
# ==========================================
def partner_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить партнёра", callback_data=f"partner_approve_{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"partner_reject_{user_id}")
    ]])

# ==========================================
# СПИСОК МЕНЕДЖЕРОВ (INLINE, ДЛЯ ОТПУСКОВ)
# ==========================================
def managers_list_kb(managers: list) -> InlineKeyboardMarkup:
    keyboard = []
    for m in managers:
        name = m.get("username") or m.get("full_name") or str(m["telegram_id"])
        keyboard.append([
            InlineKeyboardButton(text=f"👤 {name}", callback_data=f"vacation_select_{m['telegram_id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="vacation_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==========================================
# НАЗНАЧЕНИЕ КОМАНДЫ НА ПРОЕКТ (INLINE)
# ==========================================
def assign_team_kb(teams: list) -> InlineKeyboardMarkup:
    keyboard = []
    status_emoji = {"free": "🟢", "busy": "🔴", "resting": "🟡", "incomplete": "⚪"}
    for t in teams:
        emoji = status_emoji.get(t["status"], "⚪")
        if t["status"] == "free":
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{emoji} {t['team_name']}", 
                    callback_data=f"assign_team_{t['team_name']}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{emoji} {t['team_name']} ({t['status']})", 
                    callback_data="ignore"
                )
            ])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена назначения", callback_data="assign_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
