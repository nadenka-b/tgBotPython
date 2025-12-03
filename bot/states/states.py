from aiogram.fsm.state import State, StatesGroup
from enum import Enum


class AnalysisType(Enum):
    """Три типа анализа"""
    BY_SPESIALITY = "by_speciality"      # Анализ по направлению
    BY_INSTITUTE = "by_institute"      # Анализ по институту
    BY_UNIVERSITY = "by_university"    # Анализ по университету


class AnalysisStates(StatesGroup):
    """Состояния для диалога анализа"""
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
