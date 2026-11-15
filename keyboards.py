from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# ==========================================
# ГЛАВНЫЕ МЕНЮ (Reply)
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
                KeyboardButton(text="👨‍💻 Разработчики"),
            ],
            [
                KeyboardButton(text="👥 Менеджеры"),
                KeyboardButton(text="📈 Статистика бота"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="🏖 Управление отпусками"),
            ],
            [
                KeyboardButton(text="🔙 Главное меню"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Админ-панель SYNTH 👑",
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    """Кнопка отмены для анкет."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        input_field_placeholder="Нажмите для отмены",
    )


# ==========================================
# INLINE КЛАВИАТУРЫ (Кнопки под сообщениями)
# ==========================================

def dev_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    """Кнопки для одобрения/отклонения разработчика."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"dev_approve_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"dev_reject_{user_id}"),
            ]
        ]
    )


def partner_moderation_kb(user_id: int) -> InlineKeyboardMarkup:
    """Кнопки для одобрения/отклонения партнёра (только для CEO)."""
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


def managers_list_kb(managers: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком менеджеров для выбора в отпуске."""
    keyboard = []
    for m in managers:
        # m - это словарь из БД с ключами 'telegram_id' и 'username'/'full_name'
        name = m.get("username") or m.get("full_name") or str(m["telegram_id"])
        keyboard.append([
            InlineKeyboardButton(text=f"👤 {name}", callback_data=f"vacation_select_{m['telegram_id']}")
        ])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="vacation_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def project_actions_kb(project_id: int) -> InlineKeyboardMarkup:
    """Действия с проектом для менеджера."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Назначить команду", callback_data=f"proj_assign_{project_id}"),
                InlineKeyboardButton(text="✅ Завершить", callback_data=f"proj_complete_{project_id}"),
            ],
            [
                InlineKeyboardButton(text="❌ Отменить проект", callback_data=f"proj_cancel_{project_id}"),
            ],
        ]
    )
