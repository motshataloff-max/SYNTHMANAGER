"""
SYNTH Platform v2.0 - Машина состояний (FSM)
Все формы для всех ролей.
"""
from aiogram.fsm.state import State, StatesGroup

# ==========================================
# 🛒 КЛИЕНТСКИЕ ФОРМЫ
# ==========================================

class ClientOrderForm(StatesGroup):
    """Заказать разработку"""
    name = State()
    username = State()
    phone = State()
    task = State()
    wishes = State()

class FixCodeForm(StatesGroup):
    """Починить код"""
    name = State()
    username = State()
    phone = State()
    repo = State()
    problem = State()
    expected = State()
    urgency = State()

class DeployForm(StatesGroup):
    """Поднять код на сервера"""
    name = State()
    username = State()
    phone = State()
    repo = State()
    hosting = State()
    domain = State()
    requirements = State()

class PartnerForm(StatesGroup):
    """Стать партнером"""
    name = State()
    username = State()
    phone = State()
    email = State()
    project = State()
    offer = State()

class SupportForm(StatesGroup):
    """Поддержка"""
    name = State()
    username = State()
    phone = State()
    description = State()

# ==========================================
# 👨‍💻 ФОРМА РАЗРАБОТЧИКА
# ==========================================

class DevForm(StatesGroup):
    """Стать разработчиком"""
    name = State()
    stack = State()

# ==========================================
# 🔧 АДМИНСКИЕ ФОРМЫ
# ==========================================

class AdminBroadcastForm(StatesGroup):
    """Рассылка"""
    text = State()

class AdminAddUserForm(StatesGroup):
    """Добавление пользователя"""
    user_id = State()
    role = State()

class AdminBanForm(StatesGroup):
    """Бан пользователя"""
    user_id = State()
    reason = State()

class AdminUnbanForm(StatesGroup):
    """Разбан пользователя"""
    user_id = State()
