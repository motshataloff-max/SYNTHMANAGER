from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# ==========================================
# ГЛАВНЫЕ МЕНЮ
# ==========================================

def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню для всех пользователей."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛒 Заказать разработку"),
                KeyboardButton(text="👨‍💻 Стать разработчиком"),
            ],
            [
                KeyboardButton(text="🤝 Стать партнёром"),
                KeyboardButton(text="🔗 Моя ссылка на скидку"),
            ],
            [
                KeyboardButton(text="📊 Моя статистика"),
                KeyboardButton(text="ℹ️ О нас"),
            ],
            [
                KeyboardButton(text="🆘 Поддержка"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие 👇",
    )


def admin_menu() -> ReplyKeyboardMarkup:
    """Админское меню (CEO и менеджеры)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Список проектов"),
                KeyboardButton(text="👥 Менеджеры"),
            ],
            [
                KeyboardButton(text="📈 Статистика бота"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
            [
                KeyboardButton(text="🔙 Главное меню"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Админ-панель SYNTH 👑",
    )


# ==========================================
# INLINE КЛАВИАТУРЫ (Кнопки под сообщениями)
# ==========================================

def project_actions_kb(project_id: int) -> InlineKeyboardMarkup:
    """Действия с проектом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Назначить", callback_data=f"proj_assign_{project_id}"),
                InlineKeyboardButton(text="✅ Завершить", callback_data=f"proj_complete_{project_id}"),
            ],
            [
                InlineKeyboardButton(text="💸 Неоплачено", callback_data=f"proj_unpaid_{project_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"proj_cancel_{project_id}"),
            ],
        ]
    )


def dev_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"dev_approve_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"dev_reject_{user_id}"),
            ]
        ]
    )


def pr_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"pr_approve_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"pr_reject_{user_id}"),
            ]
        ]
    )


def partner_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    """Кнопки для одобрения партнёра (только для CEO)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить партнёра", callback_data=f"partner_approve_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"partner_reject_{user_id}"),
            ]
        ]
    )


def yes_no_kb(action: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура Да/Нет для подтверждений."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{action}_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{action}_no"),
            ],
        ]
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    """Кнопка отмены для анкет."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
