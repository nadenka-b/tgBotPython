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


def create_filter_buttons(options: list) -> InlineKeyboardMarkup:
    """
    Создать кнопки для фильтра из списка опций

    Args:
        options: список кортежей (value, label)

    Returns:
        InlineKeyboardMarkup с кнопками для каждой опции
    """
    buttons = []

    for value, label in options:
        # Обрезаем длинный текст если необходимо
        display_text = label[:40] + "..." if len(label) > 40 else label
        buttons.append([
            InlineKeyboardButton(
                text=display_text,
                callback_data=f"filter_{value}"
            )
        ])

    # Кнопка отмены
    buttons.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
