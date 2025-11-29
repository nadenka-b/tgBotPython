from aiogram.fsm.state import State, StatesGroup


class AnalysisStates(StatesGroup):
    """Состояния для диалога анализа"""
    waiting_for_level = State()          # Ожидание уровня образования
    waiting_for_inst = State()           # Ожидание института
    waiting_for_faculty = State()        # Ожидание факультета
    waiting_for_speciality = State()     # Ожидание направления
    waiting_for_typeofstudy = State()    # Ожидание формы обучения
    waiting_for_category = State()       # Ожидание категории
    processing = State()                 # Обработка и анализ


FILTER_CHAIN = [
    ('p_level', 'Уровень образования', AnalysisStates.waiting_for_level,
     AnalysisStates.waiting_for_inst),
    ('p_inst', 'ВУЗ / Филиал', AnalysisStates.waiting_for_inst,
     AnalysisStates.waiting_for_faculty),
    ('p_faculty', 'Институт / Факультет', AnalysisStates.waiting_for_faculty,
     AnalysisStates.waiting_for_speciality),
    ('p_speciality', 'Направление подготовки / специальность', AnalysisStates.waiting_for_speciality,
     AnalysisStates.waiting_for_typeofstudy),
    ('p_typeofstudy', 'Форма обучения', AnalysisStates.waiting_for_typeofstudy,
     AnalysisStates.waiting_for_category),
    ('p_category', 'Категория', AnalysisStates.waiting_for_category,
     AnalysisStates.processing),
]
