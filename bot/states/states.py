from aiogram.fsm.state import State, StatesGroup


class ParsingStates(StatesGroup):
    """Состояния парсинга"""
    waiting_p_level = State()
    waiting_p_inst = State()
    waiting_p_faculty = State()
    waiting_p_speciality = State()
    waiting_p_typeofstudy = State()
    waiting_p_category = State()
    parsing_complete = State()
    choose_filter_to_change = State()      # ← нужно для @router.callback_query(...)
    waiting_new_filter_value = State()     # ← используется ниже в handlers
    parsing_complete = State()
