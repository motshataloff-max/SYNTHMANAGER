from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

def client_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 Заказать разработку")],
        [KeyboardButton(text="🔧 Починить код")],
        [KeyboardButton(text="🚀 Поднять код на сервера")],
        [KeyboardButton(text="🤝 Стать партнером")],
        [KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="📂 Мои заявки")],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)

def admin_main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🎫 Все заявки")],
        [KeyboardButton(text="💾 Ручной бэкап")],
        [KeyboardButton(text="👤 Режим клиента")]
    ], resize_keyboard=True)

def urgency_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Обычно", callback_data="urgency_Обычно")],
        [InlineKeyboardButton(text="🟡 Срочно", callback_data="urgency_Срочно")],
        [InlineKeyboardButton(text="🔴 Горит", callback_data="urgency_Горит")]
    ])

def hosting_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚂 Railway", callback_data="hosting_Railway")],
        [InlineKeyboardButton(text="💻 VPS", callback_data="hosting_VPS")],
        [InlineKeyboardButton(text="🌐 Другой", callback_data="hosting_Другой")],
        [InlineKeyboardButton(text="❓ Не знаю", callback_data="hosting_Не знаю")]
    ])

def domain_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="domain_Да")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="domain_Нет")]
    ])

def skip_button(callback_data: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=callback_data)]
    ])
