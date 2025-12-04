from aiogram.fsm.state import State, StatesGroup


class AnalysisStates(StatesGroup):
    # Выбор типа анализа
    waiting_for_analysis_type = State()

    # Основные параметры
    waiting_for_level = State()          # Ожидание уровня образования
    waiting_for_inst = State()           # Ожидание ВУЗа / Филиала
    waiting_for_faculty = State()        # Ожидание факультета
    waiting_for_speciality = State()     # Ожидание направления
    waiting_for_typeofstudy = State()    # Ожидание формы обучения
    waiting_for_category = State()       # Ожидание категории

    processing = State()                 # Обработка и анализ
