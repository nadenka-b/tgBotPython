import asyncio
import time
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.states import ParsingStates
from bot.texts import (
    FILTER_QUESTIONS, FIELD_NAMES, FIELD_LABELS, START_MESSAGE,
    FINISH_MESSAGE, CHANGE_FILTER_MESSAGE, FILTER_DEPENDENCIES, ERROR_MESSAGE
)
from bot.keyboards import create_filter_keyboard, create_change_filter_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Глобальные переменные (инициализируются в main.py)
parse_manager = None
config = None
database = None


def set_parse_manager(pm):
    global parse_manager
    parse_manager = pm


def set_config(cfg):
    global config
    config = cfg


def set_database(db):
    global database
    database = db


STATE_ORDER = [
    ParsingStates.waiting_p_level,
    ParsingStates.waiting_p_inst,
    ParsingStates.waiting_p_faculty,
    ParsingStates.waiting_p_speciality,
    ParsingStates.waiting_p_typeofstudy,
    ParsingStates.waiting_p_category,
]

# ============ START ============


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    await message.answer(START_MESSAGE)

# ============ PARSE ============


@router.message(Command("parse"))
async def cmd_parse(message: Message, state: FSMContext):
    """Команда /parse - начать парсинг"""
    user_id = message.from_user.id

    await state.update_data(
        filters={},
        driver=None,
        parser=None,
        user_id=user_id,
        parse_start_time=time.time()
    )

    field_name = FIELD_NAMES[0]
    question = FILTER_QUESTIONS[field_name]["question"]
    keyboard = create_filter_keyboard(field_name)

    await message.answer(question, reply_markup=keyboard)
    await state.set_state(STATE_ORDER[0])

# ============ FILTER CHOICE ============


@router.callback_query(F.data.startswith("filter_"))
async def handle_filter_choice(callback: CallbackQuery, state: FSMContext):
    """Обработить выбор фильтра"""

    parts = callback.data.split("_")
    field_name = "_".join(parts[1:-1])
    value = parts[-1]

    current_state = await state.get_state()
    stage_idx = STATE_ORDER.index(current_state)

    data = await state.get_data()
    filters = data.get("filters", {})
    driver = data.get("driver")

    await callback.answer("⏳ Применяю фильтр...")

    try:
        if driver is None:
            driver = parse_manager.get_driver(user_id=callback.from_user.id)
            if driver is None:
                await callback.message.answer("❌ Пул браузеров переполнен, попробуй позже")
                return

        # ✅ НОВОЕ: Передаём фильтры как параметр!
        result = await parse_manager.apply_filter_async(
            driver,
            filters,  # ← Текущие фильтры (которые уже применены)
            field_name,  # ← Новый фильтр
            value  # ← Значение нового фильтра
        )

        if result["status"] != "ok":
            # ✅ КРАСИВАЯ ОШИБКА
            error_msg = result.get('error', 'Неизвестная ошибка')
            if 'WinError 10061' in str(error_msg) or 'Max retries' in str(error_msg):
                user_message = "❌ Браузер потерял соединение. Попробуй /parse заново"
            elif 'not found' in str(error_msg).lower():
                user_message = "❌ Элемент не найден на странице. Попробуй /parse заново"
            else:
                user_message = "❌ Ошибка при применении фильтра. Попробуй /parse заново"
            await callback.message.answer(user_message)
            parse_manager.return_driver(driver, user_id=callback.from_user.id)
            await state.clear()
            return

        filters[field_name] = value
        await state.update_data(filters=filters, driver=driver)

        label = FILTER_QUESTIONS[field_name]["options"].get(value, value)
        await callback.message.edit_text(
            f"✅ {FIELD_LABELS[field_name]}\n"
            f"Выбран: {label}"
        )

        # Следующий фильтр или завершение
        if stage_idx + 1 < len(STATE_ORDER):
            next_field_name = FIELD_NAMES[stage_idx + 1]
            next_question = FILTER_QUESTIONS[next_field_name]["question"]
            next_keyboard = create_filter_keyboard(next_field_name)

            await callback.message.answer(next_question, reply_markup=next_keyboard)
            await state.set_state(STATE_ORDER[stage_idx + 1])
        else:
            # ВСЕ ФИЛЬТРЫ - ФИНАЛИЗИРУЕМ
            await callback.message.answer("⏳ Получаю таблицу...")
            await state.set_state(ParsingStates.parsing_complete)

            data = await state.get_data()
            driver = data.get("driver")
            start_time = data.get("parse_start_time", 0)
            execution_time = time.time() - start_time

            # ✅ СОХРАНЯЕМ В БД
            if database and filters:
                database.save_parse_history(
                    user_id=data.get("user_id"),
                    filters=filters,
                    result_count=100,  # TODO: обновить на реальное значение из DataFrame
                    execution_time=execution_time,
                    status="success"
                )

            # ✅ ВОЗВРАЩАЕМ БРАУЗЕР В ПУЛ (НЕ закрываем!)
            if driver:
                parse_manager.return_driver(
                    driver, user_id=data.get("user_id"))

            await callback.message.answer(FINISH_MESSAGE)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await callback.message.answer(f"{ERROR_MESSAGE}: {str(e)}")

        # ✅ ВОЗВРАЩАЕМ БРАУЗЕР ПРИ ОШИБКЕ
        if driver:
            parse_manager.return_driver(driver, user_id=callback.from_user.id)
        await state.clear()

# ============ REPEAT REQUEST ============


@router.message(Command("again"))
async def cmd_again(message: Message, state: FSMContext):
    """Команда /again - запросить новую таблицу со сменой фильтров"""

    data = await state.get_data()
    filters = data.get("filters", {})

    if not filters:
        await message.answer("❌ Нет предыдущих данных. Начни с /parse")
        return

    # Форматируем текущие фильтры
    current_filters_str = "\n".join([
        f"{FIELD_LABELS.get(k, k)}: {FILTER_QUESTIONS.get(k, {}).get('options', {}).get(v, v)}"
        for k, v in filters.items()
    ])

    question = CHANGE_FILTER_MESSAGE.format(
        current_filters=current_filters_str)
    keyboard = create_change_filter_keyboard(filters)

    await message.answer(question, reply_markup=keyboard)
    await state.set_state(ParsingStates.choose_filter_to_change)

# ============ CHANGE FILTER ============


@router.callback_query(F.data.startswith("change_filter_"), ParsingStates.choose_filter_to_change)
async def handle_change_filter(callback: CallbackQuery, state: FSMContext):
    """Выбрали какой фильтр менять"""

    field_name = callback.data.replace("change_filter_", "")

    data = await state.get_data()
    filters = data.get("filters", {})

    # ⭐ СБРАСЫВАЕМ ЗАВИСИМЫЕ ФИЛЬТРЫ
    dependent_filters = FILTER_DEPENDENCIES.get(field_name, [])
    for dep_filter in dependent_filters:
        if dep_filter in filters:
            del filters[dep_filter]

    await state.update_data(filters=filters, changing_filter=field_name)

    question = FILTER_QUESTIONS[field_name]["question"]
    keyboard = create_filter_keyboard(field_name)

    await callback.message.answer(question, reply_markup=keyboard)
    await state.set_state(ParsingStates.waiting_new_filter_value)

# ============ NEW FILTER VALUE ============


@router.callback_query(F.data.startswith("filter_"), ParsingStates.waiting_new_filter_value)
async def handle_new_filter_value(callback: CallbackQuery, state: FSMContext):
    """Получили новое значение для фильтра"""

    parts = callback.data.split("_")
    field_name = "_".join(parts[1:-1])
    value = parts[-1]

    data = await state.get_data()
    filters = data.get("filters", {})
    driver = data.get("driver")
    changing_filter = data.get("changing_filter")

    await callback.answer("⏳ Обновляю данные...")

    try:
        if driver is None:
            driver = parse_manager.get_driver(user_id=callback.from_user.id)
            if driver is None:
                await callback.message.answer("❌ Пул браузеров переполнен")
                return

        # ✅ НОВОЕ: Передаём уже применённые фильтры
        result = await parse_manager.apply_filter_async(
            driver,
            # ← Фильтры которые уже были применены (могут быть пусты после reset)
            filters,
            field_name,
            value
        )

        if result["status"] != "ok":
            await callback.message.answer(f"{ERROR_MESSAGE}: {result.get('error')}")
            parse_manager.return_driver(driver, user_id=callback.from_user.id)
            return

        filters[field_name] = value
        await state.update_data(filters=filters, driver=driver)

        label = FILTER_QUESTIONS[field_name]["options"].get(value, value)
        await callback.message.edit_text(
            f"✅ {FIELD_LABELS[field_name]}\n"
            f"Новое значение: {label}"
        )

        # ✅ СОХРАНЯЕМ ОБНОВЛЁННЫЕ ФИЛЬТРЫ В БД
        start_time = data.get("parse_start_time", 0)
        execution_time = time.time() - start_time

        if database and filters:
            database.save_parse_history(
                user_id=data.get("user_id"),
                filters=filters,
                result_count=100,
                execution_time=execution_time,
                status="success"
            )

        await callback.message.answer(FINISH_MESSAGE)
        await state.set_state(ParsingStates.parsing_complete)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await callback.message.answer(f"{ERROR_MESSAGE}: {str(e)}")

        # ✅ ВОЗВРАЩАЕМ БРАУЗЕР ПРИ ОШИБКЕ
        if driver:
            parse_manager.return_driver(driver, user_id=callback.from_user.id)

# ============ CANCEL ============


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Команда /cancel - отменить"""

    current_state = await state.get_state()

    if current_state:
        data = await state.get_data()
        driver = data.get("driver")

        # ✅ ВОЗВРАЩАЕМ БРАУЗЕР
        if driver:
            parse_manager.return_driver(driver, user_id=message.from_user.id)

        await message.answer("❌ Отменено")
        await state.clear()
    else:
        await message.answer("Ничего не запущено")
