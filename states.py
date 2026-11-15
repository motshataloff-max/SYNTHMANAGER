from aiogram.fsm.state import State, StatesGroup


# ==========================================
# АНКЕТА КЛИЕНТА (ЗАКАЗ)
# ==========================================
class ClientForm(StatesGroup):
    title = State()       # Название проекта
    description = State() # ТЗ
    budget = State()      # Бюджет
    contact = State()     # Контакт (юзернейм или телефон)
    country = State()     # Страна
    age = State()         # Возраст
    sam = State()         # Самозанятый (Да/Нет)


# ==========================================
# АНКЕТА РАЗРАБОТЧИКА (ВСТУПАЮЩИЙ)
# ==========================================
class DevForm(StatesGroup):
    name = State()        # Имя
    age = State()         # Возраст
    lang = State()        # Языки программирования
    projects = State()    # Портфолио / Проекты
    hours = State()       # Сколько часов готов уделять
    goal = State()        # Цель (Заработок или Опыт)
    sam = State()         # Самозанятый (Да/Нет)


# ==========================================
# АНКЕТА ПАРТНЁРА
# ==========================================
class PartnerForm(StatesGroup):
    name = State()        # Имя или название компании
    info = State()        # Чем занимаетесь
    offer = State()       # Что предлагаете
    country = State()     # Страна
    age = State()         # Возраст
    contact = State()     # Контакт


# ==========================================
# ПОДДЕРЖКА
# ==========================================
class SupportForm(StatesGroup):
    waiting_message = State() # Ожидание текста проблемы


# ==========================================
# НАЗНАЧЕНИЕ КОМАНДЫ НА ПРОЕКТ
# ==========================================
class AssignForm(StatesGroup):
    senior = State()      # ID Senior разработчика
    medium1 = State()     # ID первого Medium
    medium2 = State()     # ID второго Medium


# ==========================================
# УПРАВЛЕНИЕ ОТПУСКАМИ МЕНЕДЖЕРОВ
# ==========================================
class VacationForm(StatesGroup):
    select_manager = State() # Выбор менеджера из списка
    start_date = State()     # Дата начала отпуска
    end_date = State()       # Дата конца отпуска
