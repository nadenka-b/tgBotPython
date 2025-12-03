import logging
from database.db import Database

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from analyzer.analyzer import DataAnalyzer
from bot.messages import get_text
from bot.states import AnalysisStates
from bot.keyboards import *


logger = logging.getLogger(__name__)

PARAM_ORDERS = {
    'by_speciality': [
        'level',
        'inst',
        'faculty',
        'speciality',
        'typeofstudy',
        'category'
    ],
    'by_institute': [
        'level',
        'inst',
        'faculty',
        'typeofstudy',
        'category'
    ],
    'by_university': [
        'level',
        'inst',
        'category'
    ]
}


# Вспомогательные функции
def get_param_order(analysis_type: str) -> list[str]:
    """
    Получить порядок параметров для типа анализа

    Args:
        analysis_type: Тип анализа (by_speciality, by_institute, by_university)

    Returns:
        Список параметров в нужном порядке
    """

    return PARAM_ORDERS.get(analysis_type, [])


async def get_options_for_param(db: Database, param: str, filters: dict) -> list[tuple[int, str]]:
    """
    Получить опции для параметра из БД

    Учитывает зависимости между параметрами:
    - level: независимый
    - inst: независимый
    - faculty: зависит от inst
    - speciality: зависит от level + inst + faculty
    - typeofstudy: зависит от level + inst + faculty + speciality
    - category: независимый

    Args:
        db: Экземпляр Database
        param: Название параметра (level, inst, faculty, speciality, typeofstudy, category)
        filters: Словарь с уже выбранными параметрами

    Returns:
        Список (value, name) или пустой список если ошибка
    """
    try:
        if param == 'level':
            return db.get_levels()

        elif param == 'inst':
            return db.get_institutes()

        elif param == 'faculty':
            inst = filters.get('inst')
            if not inst:
                logger.warning(
                    f"⚠️ Не хватает inst для получения faculties")
                return []
            return db.get_faculties(inst)

        elif param == 'speciality':
            level = filters.get('level', '')
            inst = filters.get('inst', '')
            faculty = filters.get('faculty', '')
            if not all([level, inst, faculty]):
                logger.warning(
                    f"⚠️ Не хватает параметров для получения specialities")
                return []
            return db.get_specialities(level, inst, faculty)

        elif param == 'typeofstudy':
            level = filters.get('level', '')
            inst = filters.get('inst', '')
            faculty = filters.get('faculty', '')
            speciality = filters.get('speciality', '')
            if not all([level, inst, faculty, speciality]):
                logger.warning(
                    f"⚠️ Не хватает параметров для получения typeofstudy")
                return []
            return db.get_study_types(level, inst, faculty, speciality)

        elif param == 'category':
            return db.get_categories()

        else:
            logger.error(f"❌ Неизвестный параметр: {param}")
            return []

    except Exception as e:
        logger.error(f"❌ Ошибка при получении опций для {param}: {e}")
        return []


def create_router(db: Database) -> Router:
    """
    Создать роутер с обработчиками

    Args:
        parser: экземпляр парсера КФУ
        db: экземпляр БД

    Returns:
        Router с зарегистрированными обработчиками
    """
    router = Router()
    analyzer = DataAnalyzer(db)

    @router.message(Command("start"))
    async def start_handler(message: Message):
        """Приветственное сообщение"""
        await message.answer(get_text('welcome'), reply_markup=get_main_menu())

    @router.callback_query(F.data == "help")
    async def help_handler(callback: CallbackQuery):
        """Справка"""
        await callback.answer()
        await callback.message.answer(
            get_text('help'),
            reply_markup=get_main_menu()
        )

    @router.callback_query(F.data == "start_analysis")
    async def choose_analysis_type(callback: CallbackQuery, state: FSMContext):
        """Начало анализа - выбор типа анализа"""
        await callback.answer()

        await callback.message.answer(
            get_text('choose_analysis_type'),
            reply_markup=get_analysis_type_menu()
        )

        await state.set_state(AnalysisStates.waiting_for_analysis_type)

    @router.callback_query(AnalysisStates.waiting_for_analysis_type, F.data.startswith("analysis_type_"))
    async def handle_analysis_type(callback: CallbackQuery, state: FSMContext):
        """
        Пользователь выбрал тип анализа
        Определяем порядок параметров и переходим к первому параметру
        """
        await callback.answer()

        analysis_type_str = callback.data.replace("analysis_type_", "")

        param_order = get_param_order(analysis_type_str)

        await state.update_data(
            analysis_type=analysis_type_str,
            param_order=param_order,
            current_param_index=0,
            filters={}  # Словарь для сохранения выборов
        )

        logger.info(f"✅ Выбран анализ: {analysis_type_str}")
        logger.info(f"📋 Порядок параметров: {param_order}")

        # Переходим к первому параметру
        await ask_for_parameter(callback.message, state)

    @router.callback_query(F.data.startswith("option_"))
    async def handle_option_selection(callback: CallbackQuery, state: FSMContext):
        """
        Пользователь выбрал опцию параметра
        Сохраняем выбор и переходим к следующему параметру
        """
        await callback.answer()

        data = await state.get_data()
        param_order = data['param_order']
        current_index = data['current_param_index']
        filters = data.get('filters', {})

        # Текущий параметр
        current_param = param_order[current_index]

        # Значение выбранной опции (ID из БД)
        option_value = callback.data.replace("option_", "")

        # Сохраняем в filters
        filters[current_param] = option_value

        logger.info(f"✅ Выбран {current_param}: {option_value}")

        # Переходим к следующему параметру
        current_index += 1

        await state.update_data(
            current_param_index=current_index,
            filters=filters
        )

        # Запрашиваем следующий параметр
        if callback.message:
            await ask_for_parameter(callback.message, state)

    @router.callback_query(F.data == "cancel")
    async def cancel_handler(callback: CallbackQuery, state: FSMContext):
        """Отмена анализа"""
        await callback.answer()

        if callback.message:
            await callback.message.answer(
                get_text('analysis_cancelled'),
                reply_markup=get_main_menu()
            )

        await state.clear()

    @router.callback_query(F.data == "main_menu")
    async def main_menu_handler(callback: CallbackQuery, state: FSMContext):
        """Вернуться на главное меню"""
        await callback.answer()

        if callback.message:
            await callback.message.answer(
                get_text('welcome'),
                reply_markup=get_main_menu()
            )

        await state.clear()

    async def ask_for_parameter(message: Message, state: FSMContext):
        """
        Вспомогательная функция: получить опции параметра и отправить пользователю

        Args:
            message: Telegram сообщение
            state: FSM контекст
        """
        data = await state.get_data()
        param_order = data['param_order']
        current_index = data['current_param_index']
        filters = data.get('filters', {})

        # Если все параметры выбраны - переходим к анализу
        if current_index >= len(param_order):
            await process_analysis(message, state)
            return

        # Текущий параметр
        current_param = param_order[current_index]

        logger.info(f"📍 Запрашиваем параметр: {current_param}")

        try:
            # Получаем опции для текущего параметра
            options = await get_options_for_param(db, current_param, filters)

            if not options:
                await message.answer(
                    get_text('error_loading'),
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return

            # Создаем клавиатуру
            keyboard = create_options_keyboard(options)

            # Отправляем сообщение с опциями
            await message.answer(
                get_text(f"choose_{current_param}"),
                reply_markup=keyboard
            )

            # Переходим в соответствующее состояние
            state_mapping = {
                'level': AnalysisStates.waiting_for_level,
                'inst': AnalysisStates.waiting_for_inst,
                'faculty': AnalysisStates.waiting_for_faculty,
                'speciality': AnalysisStates.waiting_for_speciality,
                'typeofstudy': AnalysisStates.waiting_for_typeofstudy,
                'category': AnalysisStates.waiting_for_category,
            }

            await state.set_state(state_mapping[current_param])

        except Exception as e:
            logger.error(f"❌ Ошибка при получении опций: {e}")
            await message.answer(
                get_text('error_loading'),
                reply_markup=get_main_menu()
            )
            await state.clear()

    async def process_analysis(message: Message, state: FSMContext):
        """
        Вспомогательная функция: все параметры выбраны - выполняем анализ

        Args:
            message: Telegram сообщение
            state: FSM контекст
        """
        data = await state.get_data()
        filters = data.get('filters', {})
        analysis_type = data.get('analysis_type')

        logger.info(
            f"📊 Начинаем анализ {analysis_type} с фильтрами: {filters}")

        if not message:
            logger.error("❌ message is None in process_analysis")
            await state.clear()
            return

        processing_msg = await message.answer(get_text('processing'))

        try:
            if analysis_type == 'by_speciality':
                logger.info("📚 Анализирую направление...")
                result = analyzer.analyze_speciality({
                    'level': filters.get('level'),
                    'inst': filters.get('inst'),
                    'faculty': filters.get('faculty'),
                    'speciality': filters.get('speciality'),
                    'typeofstudy': filters.get('typeofstudy'),
                    'category': filters.get('category')
                })

                if isinstance(result, dict):
                    text = result.get('error', '❌ Ошибка')
                    await processing_msg.edit_text(
                        text,
                        reply_markup=get_main_menu()
                    )
                    logger.error(f"❌ Ошибка анализа: {text}")
                else:
                    input_file = BufferedInputFile(
                        result.read(), filename="speciality_analysis.xlsx")
                    await message.answer_document(
                        input_file,
                        caption="📊 Анализ направления выполнен!",
                        reply_markup=get_new_analysis_keyboard()
                    )
                    await processing_msg.delete()
                    logger.info("✅ Файл отправлен пользователю")

            elif analysis_type == 'by_institute':
                logger.info("🏛️ Анализирую направления в институте...")

                result = analyzer.analyze_institute({
                    'level': filters.get('level'),
                    'inst': filters.get('inst'),
                    'faculty': filters.get('faculty'),
                    'typeofstudy': filters.get('typeofstudy'),
                    'category': filters.get('category')
                })

                if isinstance(result, dict):
                    text = result.get('error', '❌ Ошибка')
                    await processing_msg.edit_text(
                        text,
                        reply_markup=get_main_menu()
                    )
                    logger.error(f"❌ Ошибка анализа: {text}")
                else:
                    input_file = BufferedInputFile(
                        result.read(), filename="institute_analysis.xlsx")
                    await message.answer_document(
                        input_file,
                        caption="📊 Анализ направлений в институте выполнен!",
                        reply_markup=get_new_analysis_keyboard()
                    )
                    await processing_msg.delete()
                    logger.info("✅ Файл отправлен пользователю")

            elif analysis_type == 'by_university':
                logger.info("🎓 Анализирую все направления...")

                result = analyzer.analyze_university({
                    'level': filters.get('level'),
                    'inst': filters.get('inst'),
                    'category': filters.get('category')
                })

                if isinstance(result, dict):
                    text = result.get('error', '❌ Ошибка')
                    await processing_msg.edit_text(
                        text,
                        reply_markup=get_main_menu()
                    )
                    logger.error(f"❌ Ошибка анализа: {text}")
                else:
                    input_file = BufferedInputFile(
                        result.read(), filename="university_analysis.xlsx")
                    await message.answer_document(
                        input_file,
                        caption="📊 Анализ всех направлений выполнен!",
                        reply_markup=get_new_analysis_keyboard()
                    )
                    await processing_msg.delete()
                    logger.info("✅ Файл отправлен пользователю")

        except Exception as e:
            logger.error(f"❌ Ошибка при анализе: {e}")
            await processing_msg.edit_text(
                f"❌ Ошибка анализа: {str(e)}",
                reply_markup=get_main_menu()
            )

        finally:
            await state.clear()

    return router

    # @router.callback_query(F.data.startswith("filter_"))
    # async def filter_handler(callback: CallbackQuery, state: FSMContext):
    #     """Обработчик выбора фильтра"""
    #     await callback.answer()

    #     current_state = await state.get_state()
    #     data = await state.get_data()
    #     current_params = data.get('current_params', {})

    #     # Получаем значение выбранного фильтра
    #     filter_value = callback.data.replace("filter_", "")

    #     # Определяем текущий фильтр и сохраняем значение
    #     for filter_name, display_name, waiting_state, next_state in FILTER_CHAIN:
    #         if current_state == waiting_state:
    #             # Сохраняем значение в параметры
    #             if filter_name:
    #                 current_params[filter_name] = filter_value

    #             # Загружаем следующие опции
    #             html = await parser.fetch_page(current_params)

    #             # Если это последний фильтр, переходим к обработке
    #             if next_state == AnalysisStates.processing:
    #                 await state.update_data(current_params=current_params)
    #                 await state.set_state(AnalysisStates.processing)
    #                 await process_analysis(callback.message, state)
    #                 return

    #             # Получаем опции следующего фильтра
    #             next_filter_info = next(
    #                 (f for f in FILTER_CHAIN if f[-2] == next_state),
    #                 None
    #             )

    #             if not next_filter_info:
    #                 break

    #             next_filter_name, next_display_name, _, _ = next_filter_info
    #             next_options = parser.extract_filter_options(
    #                 html, next_filter_name
    #             )

    #             if not next_options:
    #                 await callback.message.answer(
    #                     messages.error_no_options_formatted(next_display_name),
    #                     reply_markup=get_main_menu()
    #                 )
    #                 await state.clear()
    #                 return

    #             # Обновляем параметры и переходим к следующему состоянию
    #             await state.update_data(current_params=current_params)
    #             await state.set_state(next_state)

    #             next_message = messages.SELECT_FILTER_FORMATTED(
    #                 next_display_name)
    #             await callback.message.answer(
    #                 next_message,
    #                 reply_markup=create_filter_buttons(next_options),
    #                 parse_mode="Markdown"
    #             )
    #             break

    # # ========== PROCESSING / ANALYSIS ==========

    # async def process_analysis(message: Message, state: FSMContext):
    #     """Процесс анализа данных"""
    #     data = await state.get_data()
    #     current_params = data.get('current_params', {})

    #     processing_msg = await message.answer(messages.LOADING_TABLE)

    #     try:
    #         # 🆕 ВМЕСТО ПАРСИНГА - БЕРЕМ ИЗ БД
    #         records = db.get_data_by_filters(
    #             p_level=current_params.get('p_level'),
    #             p_faculty=current_params.get('p_faculty'),
    #             p_inst=current_params.get('p_inst'),
    #             p_speciality=current_params.get('p_speciality'),
    #             p_typeofstudy=current_params.get('p_typeofstudy'),
    #             category=current_params.get('category'),
    #         )

    #         if not records:
    #             await processing_msg.edit_text(
    #                 messages.ERROR_TABLE_NOT_FOUND,
    #                 reply_markup=get_main_menu()
    #             )
    #             await state.clear()
    #             return

    #         # Преобразуем SQLAlchemy объекты в DataFrame
    #         df = pd.DataFrame([
    #             {
    #                 'Направление': r.epgu_id,
    #                 'Заявления': r.score,
    #                 'Статус': r.status,
    #                 # ... остальные колонки
    #             }
    #             for r in records
    #         ])

    #         # Анализируем данные
    #         analyzer = DataAnalyzer(df)
    #         results = analyzer.analyze_all()

    #         # Сохраняем в Excel
    #         filename = f"kfu_report_{message.from_user.id}.xlsx"
    #         if analyzer.to_excel(filename):
    #             # Отправляем анализ
    #             summary_text = messages.ANALYSIS_COMPLETE_FORMATTED(
    #                 results.get('summary', '')
    #             )
    #             await processing_msg.edit_text(summary_text)

    #             # Отправляем файл
    #             file = FSInputFile(filename)
    #             await message.answer_document(
    #                 file,
    #                 caption=messages.EXCEL_CAPTION
    #             )

    #             # Очищаем файл
    #             if os.path.exists(filename):
    #                 os.remove(filename)
    #         else:
    #             await processing_msg.edit_text(
    #                 messages.ERROR_SAVING_RESULTS,
    #                 reply_markup=get_main_menu()
    #             )

    #     except Exception as e:
    #         logger.error(f"Ошибка при анализе: {e}")
    #         await processing_msg.edit_text(
    #             messages.error_generic_formatted(str(e)),
    #             reply_markup=get_main_menu()
    #         )

    #     finally:
    #         await state.clear()
    #         await message.answer(
    #             messages.NEW_ANALYSIS_QUESTION,
    #             reply_markup=get_main_menu()
    #         )

    # # ========== CANCEL HANDLER ==========

    # @router.callback_query(F.data == "cancel")
    # async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    #     """Отмена анализа"""
    #     await callback.answer()
    #     await state.clear()
    #     await callback.message.answer(
    #         messages.ANALYSIS_CANCELLED,
    #         reply_markup=get_main_menu()
    #     )
