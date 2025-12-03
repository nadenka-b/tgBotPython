from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [InlineKeyboardButton(
            text="📊 Анализ данных поступления",
            callback_data="start_analysis"
        )],
        [InlineKeyboardButton(
            text="ℹ️ Справка",
            callback_data="help"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_analysis_type_menu() -> InlineKeyboardMarkup:
    """Выбор типа анализа"""
    buttons = [
        [InlineKeyboardButton(
            text="📊 По направлению",
            callback_data="analysis_type_by_speciality"
        )],
        [InlineKeyboardButton(
            text="🏛️ По институту",
            callback_data="analysis_type_by_institute"
        )],
        [InlineKeyboardButton(
            text="🎓 По университету",
            callback_data="analysis_type_by_university"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_options_keyboard(options: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру из списка опций

    Args:
        options: список label

    Returns:
        InlineKeyboardMarkup с кнопками для каждой опции
    """
    buttons = []

    for value, label in options:
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"option_{value}"
            )
        ])

    buttons.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_new_analysis_keyboard() -> InlineKeyboardMarkup:
    """Меню после завершения анализа"""
    buttons = [
        [InlineKeyboardButton(
            text="📊 Новый анализ",
            callback_data="start_analysis"
        )],
        [InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
