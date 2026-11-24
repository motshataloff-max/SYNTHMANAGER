"""
SYNTH Platform v2.0 - Машина состояний (FSM)
Только актуальные формы.
"""
from aiogram.fsm.state import State, StatesGroup

# ==========================================
# 🛒 КЛИЕНТСКИЕ ФОРМЫ (5 основных услуг)
# ==========================================

class ClientOrderForm(StatesGroup):
    """Заказать разработку"""
    name = State()
    username = State()
    phone = State()
    task = State()
    wishes = State()  # Опционально

class FixCodeForm(StatesGroup):
    """Починить код"""
    name = State()
    username = State()
    phone = State()
    repo = State()       # Опционально
    problem = State()
    expected = State()   # Опционально
    urgency = State()

class DeployForm(StatesGroup):
    """Поднять код на сервера"""
    name = State()
    username = State()
    phone = State()
    repo = State()       # Опционально
    hosting = State()
    domain = State()
    requirements = State() # Опционально

class PartnerForm(StatesGroup):
    """Стать партнером"""
    name = State()
    username = State()
    phone = State()
    email = State()      # Опционально
    project = State()
    offer = State()

class SupportForm(StatesGroup):
    """Поддержка"""
    name = State()
    username = State()
    phone = State()
    description = State()

# ==========================================
# 👨‍💻 ФОРМА РАЗРАБОТЧИКА (если нужна модерация)
# ==========================================

class DevForm(StatesGroup):
    """Стать разработчиком (для модерации)"""
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
