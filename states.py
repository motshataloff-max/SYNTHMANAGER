from aiogram.fsm.state import State, StatesGroup


class ClientForm(StatesGroup):
    """Анкета клиента: заказ разработки."""
    title = State()
    description = State()
    budget = State()
    contact = State()
    country = State()
    age = State()
    sam = State()


class DevForm(StatesGroup):
    """Анкета разработчика."""
    name = State()
    age = State()
    lang = State()
    projects = State()
    sam = State()


class PartnerForm(StatesGroup):
    """Анкета партнёра (заявка уходит лично CEO)."""
    name = State()
    info = State()
    offer = State()


class SupportForm(StatesGroup):
    """Тикет в поддержку."""
    waiting_message = State()


class AssignForm(StatesGroup):
    """Назначение команды на проект (тестировщика больше нет)."""
    senior = State()
    medium1 = State()
    medium2 = State()
