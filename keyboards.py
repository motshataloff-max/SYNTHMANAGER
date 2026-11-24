"""
SYNTH Platform v2.0 - Клавиатуры
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def cancel_kb():
    """Кнопка отмены для форм"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def client_main_menu():
    """Главное меню клиента (5 основных услуг)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Заказать разработку")],
            [KeyboardButton(text="🔧 Починить код")],
            [KeyboardButton(text="🚀 Поднять код на сервера")],
            [KeyboardButton(text="🤝 Стать партнером")],
            [KeyboardButton(text="🆘 Поддержка")]
        ],
        resize_keyboard=True
    )

def admin_main_menu():
    """Главное меню администратора"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="📦 Проекты")],
            [KeyboardButton(text="🎫 Заявки")],
            [KeyboardButton(text="🚫 Бан")],
            [KeyboardButton(text="📢 Рассылка")]
        ],
        resize_keyboard=True
    )

def dev_main_menu():
    """Главное меню разработчика"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Мои задачи")],
            [KeyboardButton(text="📊 Моя статистика")],
            [KeyboardButton(text="💰 Баланс")]
        ],
        resize_keyboard=True
    )

def yes_no_kb():
    """Кнопки Да/Нет для подтверждений"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="no")]
    ])

def confirm_kb(action: str):
    """Кнопка подтверждения действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Подтвердить", callback_data=f"confirm_{action}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])
