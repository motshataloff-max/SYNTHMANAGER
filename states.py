from aiogram.fsm.state import State, StatesGroup

class ClientForm(StatesGroup):
    """Состояния для формы заказа разработки"""
    title = State()
    description = State()
    budget = State()
    contact_info = State()
    country = State()
    is_samozanyat = State()

class DevForm(StatesGroup):
    """Состояния для формы подачи заявки разработчиком"""
    name = State()
    stack = State()
    experience = State()
    portfolio = State()

class PartnerForm(StatesGroup):
    """Состояния для формы подачи заявки партнером"""
    name = State()
    niche = State()
    experience = State()

class SupportForm(StatesGroup):
    """Состояния для службы поддержки"""
    waiting_message = State()


