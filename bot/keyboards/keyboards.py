from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.texts import FILTER_QUESTIONS, FIELD_NAMES, FIELD_LABELS, FILTER_DEPENDENCIES


def create_filter_keyboard(field_name: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру для фильтра"""
    options = FILTER_QUESTIONS[field_name]["options"]
    buttons = [
        [InlineKeyboardButton(
            text=label,
            callback_data=f"filter_{field_name}_{value}"
        )]
        for value, label in options.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_change_filter_keyboard(current_filters: dict) -> InlineKeyboardMarkup:
    """Создать клавиатуру для выбора фильтра к изменению"""
    buttons = []

    for field_name in FIELD_NAMES:
        current_value = current_filters.get(field_name, "не выбран")
        current_label = FILTER_QUESTIONS[field_name]["options"].get(
            current_value, current_value)

        label = f"{FIELD_LABELS[field_name]}: {current_label}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"change_filter_{field_name}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_cancel_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отменить", callback_data="cancel_parsing")]
    ])
