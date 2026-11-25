from aiogram.fsm.state import State, StatesGroup

# --- НОВЫЕ КЛИЕНТСКИЕ ФОРМЫ ---
class ClientOrderForm(StatesGroup):
    name = State(); username = State(); phone = State(); task = State(); wishes = State()

class FixCodeForm(StatesGroup):
    name = State(); username = State(); phone = State(); repo = State()
    problem = State(); expected = State(); urgency = State()

class DeployForm(StatesGroup):
    name = State(); username = State(); phone = State(); repo = State()
    hosting = State(); domain = State(); requirements = State()

class PartnerForm(StatesGroup):
    name = State(); username = State(); phone = State(); email = State()
    project = State(); offer = State()

class SupportForm(StatesGroup):
    name = State(); username = State(); phone = State(); description = State()

# --- СТАРЫЕ ФОРМЫ (Для совместимости с admin.py, dev.py) ---
class DevForm(StatesGroup):
    name = State(); stack = State()

class AdminBroadcastForm(StatesGroup):
    text = State()

class AdminAddUserForm(StatesGroup):
    user_id = State(); role = State()

# --- ЖЕЛЕЗОБЕТОННАЯ ЗАЩИТА ОТ ОШИБОК ИМПОРТА ---
# Любой старый файл, который ищет ClientForm, получит ClientOrderForm
ClientForm = ClientOrderForm
