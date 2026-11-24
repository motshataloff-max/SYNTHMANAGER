"""
SYNTH Platform v2.0 - Клавиатуры
Все клавиатуры для клиентских форм, админки и разработчиков
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 🛒 КЛИЕНТСКИЕ КЛАВИАТУРЫ
# ==========================================

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

def skip_button(callback_data: str):
    """Кнопка 'Пропустить' для опциональных полей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data=callback_data)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])

def urgency_kb():
    """Выбор срочности для 'Починить код'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Обычно", callback_data="urgency_Обычно")],
        [InlineKeyboardButton(text="🟡 Срочно", callback_data="urgency_Срочно")],
        [InlineKeyboardButton(text="🔴 Горит", callback_data="urgency_Горит")]
    ])

def hosting_kb():
    """Выбор хостинга для 'Поднять код на сервера'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚂 Railway", callback_data="hosting_Railway")],
        [InlineKeyboardButton(text="💻 VPS (свой сервер)", callback_data="hosting_VPS")],
        [InlineKeyboardButton(text="🌐 Другой хостинг", callback_data="hosting_Другой")],
        [InlineKeyboardButton(text="❓ Не знаю", callback_data="hosting_Не знаю")]
    ])

def domain_kb():
    """Выбор наличия домена"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, есть", callback_data="domain_Да")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="domain_Нет")]
    ])

# ==========================================
# 👨‍💻 АДМИНСКИЕ КЛАВИАТУРЫ
# ==========================================

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

def manage_teams_kb():
    """Клавиатура управления командами"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Управление командами", callback_data="manage_teams")],
        [InlineKeyboardButton(text="➕ Создать команду", callback_data="create_team")],
        [InlineKeyboardButton(text="📋 Список команд", callback_data="list_teams")]
    ])

def admin_users_kb():
    """Управление пользователями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Добавить пользователя", callback_data="add_user")],
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="ban_user")],
        [InlineKeyboardButton(text="✅ Разбанить", callback_data="unban_user")],
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="list_users")]
    ])

def admin_projects_kb():
    """Управление проектами"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Активные проекты", callback_data="active_projects")],
        [InlineKeyboardButton(text="✅ Завершённые", callback_data="done_projects")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="project_stats")]
    ])

def admin_tickets_kb():
    """Управление заявками"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="new_tickets")],
        [InlineKeyboardButton(text="🔄 В работе", callback_data="in_progress_tickets")],
        [InlineKeyboardButton(text="✅ Завершённые", callback_data="done_tickets")]
    ])

def ticket_action_kb(ticket_id: int):
    """Действия с конкретной заявкой"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{ticket_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ticket_id}")],
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{ticket_id}")]
    ])

# ==========================================
# 👨‍💻 КЛАВИАТУРЫ РАЗРАБОТЧИКА
# ==========================================

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

def dev_tasks_kb():
    """Задачи разработчика"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Доступные задачи", callback_data="available_tasks")],
        [InlineKeyboardButton(text="🔄 Мои активные", callback_data="my_active_tasks")],
        [InlineKeyboardButton(text="✅ Завершённые", callback_data="my_done_tasks")]
    ])

def take_task_kb(task_id: int):
    """Взять задачу в работу"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"take_task_{task_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_task")]
    ])

# ==========================================
# 🔧 УНИВЕРСАЛЬНЫЕ КЛАВИАТУРЫ
# ==========================================

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

def back_to_menu_kb():
    """Кнопка возврата в главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])

def cancel_action_kb():
    """Отмена действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])
