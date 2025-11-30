# handlers/handlers.py
"""
Основные обработчики команд и callback-ов
"""

import logging
import os
from database.db import Database
import pandas as pd

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from parser.parser import Parser
from analyzer.analyzer import DataAnalyzer
from bot.messages import messages

from bot.states import AnalysisStates, FILTER_CHAIN
from bot.keyboards import get_main_menu, create_filter_buttons


logger = logging.getLogger(__name__)


def create_router(parser: Parser, db: Database) -> Router:
    """
    Создать роутер с обработчиками

    Args:
        parser: экземпляр парсера КФУ
        db: экземпляр БД

    Returns:
        Router с зарегистрированными обработчиками
    """
    router = Router()

    # ========== START HANDLER ==========

    @router.message(Command("start"))
    async def start_handler(message: Message):
        """Приветственное сообщение"""
        await message.answer(messages.WELCOME, reply_markup=get_main_menu())

    # ========== HELP HANDLER ==========

    @router.callback_query(F.data == "help")
    async def help_handler(callback: CallbackQuery):
        """Справка"""
        await callback.message.answer(
            messages.HELP_TEXT,
            reply_markup=get_main_menu()
        )
        await callback.answer()

    # ========== START ANALYSIS ==========

    @router.callback_query(F.data == "start_analysis")
    async def start_analysis(callback: CallbackQuery, state: FSMContext):
        """Начало анализа - выбор уровня образования"""
        await callback.answer()

        await callback.message.answer(messages.LOADING_OPTIONS)

        # Получаем опции уровня образования (используем пустые параметры для первого запроса)
        initial_params = {}
        html = await parser.fetch_page(initial_params)
        level_options = parser.extract_filter_options(html, 'p_level')

        if not level_options:
            await callback.message.answer(
                messages.ERROR_LOADING_OPTIONS,
                reply_markup=get_main_menu()
            )
            return

        # Сохраняем текущие параметры в контекст
        await state.update_data(current_params={})
        await state.set_state(AnalysisStates.waiting_for_level)

        await callback.message.answer(
            messages.SELECT_LEVEL,
            reply_markup=create_filter_buttons(level_options),
            parse_mode="Markdown"
        )

    # ========== FILTER HANDLERS ==========

    @router.callback_query(F.data.startswith("filter_"))
    async def filter_handler(callback: CallbackQuery, state: FSMContext):
        """Обработчик выбора фильтра"""
        await callback.answer()

        current_state = await state.get_state()
        data = await state.get_data()
        current_params = data.get('current_params', {})

        # Получаем значение выбранного фильтра
        filter_value = callback.data.replace("filter_", "")

        # Определяем текущий фильтр и сохраняем значение
        for filter_name, display_name, waiting_state, next_state in FILTER_CHAIN:
            if current_state == waiting_state:
                # Сохраняем значение в параметры
                if filter_name:
                    current_params[filter_name] = filter_value

                # Загружаем следующие опции
                html = await parser.fetch_page(current_params)

                # Если это последний фильтр, переходим к обработке
                if next_state == AnalysisStates.processing:
                    await state.update_data(current_params=current_params)
                    await state.set_state(AnalysisStates.processing)
                    await process_analysis(callback.message, state)
                    return

                # Получаем опции следующего фильтра
                next_filter_info = next(
                    (f for f in FILTER_CHAIN if f[-2] == next_state),
                    None
                )

                if not next_filter_info:
                    break

                next_filter_name, next_display_name, _, _ = next_filter_info
                next_options = parser.extract_filter_options(
                    html, next_filter_name
                )

                if not next_options:
                    await callback.message.answer(
                        messages.error_no_options_formatted(next_display_name),
                        reply_markup=get_main_menu()
                    )
                    await state.clear()
                    return

                # Обновляем параметры и переходим к следующему состоянию
                await state.update_data(current_params=current_params)
                await state.set_state(next_state)

                next_message = messages.SELECT_FILTER_FORMATTED(
                    next_display_name)
                await callback.message.answer(
                    next_message,
                    reply_markup=create_filter_buttons(next_options),
                    parse_mode="Markdown"
                )
                break

    # ========== PROCESSING / ANALYSIS ==========

    async def process_analysis(message: Message, state: FSMContext):
        """Процесс анализа данных"""
        data = await state.get_data()
        current_params = data.get('current_params', {})

        processing_msg = await message.answer(messages.LOADING_TABLE)

        try:
            # 🆕 ВМЕСТО ПАРСИНГА - БЕРЕМ ИЗ БД
            records = db.get_data_by_filters(
                p_level=current_params.get('p_level'),
                p_faculty=current_params.get('p_faculty'),
                p_inst=current_params.get('p_inst'),
                p_speciality=current_params.get('p_speciality'),
                p_typeofstudy=current_params.get('p_typeofstudy'),
                category=current_params.get('category'),
            )

            if not records:
                await processing_msg.edit_text(
                    messages.ERROR_TABLE_NOT_FOUND,
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return

            # Преобразуем SQLAlchemy объекты в DataFrame
            df = pd.DataFrame([
                {
                    'Направление': r.epgu_id,
                    'Заявления': r.score,
                    'Статус': r.status,
                    # ... остальные колонки
                }
                for r in records
            ])

            # Анализируем данные
            analyzer = DataAnalyzer(df)
            results = analyzer.analyze_all()

            # Сохраняем в Excel
            filename = f"kfu_report_{message.from_user.id}.xlsx"
            if analyzer.to_excel(filename):
                # Отправляем анализ
                summary_text = messages.ANALYSIS_COMPLETE_FORMATTED(
                    results.get('summary', '')
                )
                await processing_msg.edit_text(summary_text)

                # Отправляем файл
                file = FSInputFile(filename)
                await message.answer_document(
                    file,
                    caption=messages.EXCEL_CAPTION
                )

                # Очищаем файл
                if os.path.exists(filename):
                    os.remove(filename)
            else:
                await processing_msg.edit_text(
                    messages.ERROR_SAVING_RESULTS,
                    reply_markup=get_main_menu()
                )

        except Exception as e:
            logger.error(f"Ошибка при анализе: {e}")
            await processing_msg.edit_text(
                messages.error_generic_formatted(str(e)),
                reply_markup=get_main_menu()
            )

        finally:
            await state.clear()
            await message.answer(
                messages.NEW_ANALYSIS_QUESTION,
                reply_markup=get_main_menu()
            )

    # ========== CANCEL HANDLER ==========

    @router.callback_query(F.data == "cancel")
    async def cancel_handler(callback: CallbackQuery, state: FSMContext):
        """Отмена анализа"""
        await callback.answer()
        await state.clear()
        await callback.message.answer(
            messages.ANALYSIS_CANCELLED,
            reply_markup=get_main_menu()
        )

    return router
