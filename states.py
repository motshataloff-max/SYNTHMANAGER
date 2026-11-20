from aiogram.fsm.state import State, StatesGroup

class ClientForm(StatesGroup):
    title = State()
    description = State()
    budget = State()
    contact = State()
    country = State()
    age = State()
    sam = State()

class DevForm(StatesGroup):
    name = State()
    age = State()
    lang = State()
    projects = State()
    hours = State()
    goal = State()
    sam = State()

class PartnerForm(StatesGroup):
    name = State()
    info = State()
    offer = State()
    country = State()
    age = State()
    contact = State()

class SupportForm(StatesGroup):
    waiting_message = State()

class AssignForm(StatesGroup):
    senior = State()
    medium1 = State()
    medium2 = State()

class VacationForm(StatesGroup):
    select_manager = State()
    start_date = State()
    end_date = State()

class BroadcastForm(StatesGroup):
    waiting_message = State()
