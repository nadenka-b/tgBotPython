import pytest


@pytest.fixture
def sample_filter_combination():
    """Пример комбинации фильтров"""
    from database import FilterCombination

    return FilterCombination(
        id=1,
        level_value=1,
        level_name='Бакалавриат',
        inst_value=0,
        inst_name='КФУ',
        faculty_value=5,
        faculty_name='ИВМиИТ',
        speciality_value=166,
        speciality_name='01.03.02 Прикладная математика',
        typeofstudy_value=1,
        typeofstudy_name='Очная',
        category_value=0,
        category_name='Бюджет'
    )


class TestIntegration:
    """Интеграционные тесты для взаимодействия компонентов"""

    def test_message_and_keyboard_work_together(self):
        """Проверка что сообщения и клавиатуры работают вместе"""
        from bot.messages import get_text
        from bot.keyboards import get_main_menu

        welcome_text = get_text('welcome')
        keyboard = get_main_menu()

        assert welcome_text is not None
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0

    def test_analysis_type_and_param_order(self):
        """Проверка что типы анализа соответствуют порядку параметров"""
        from bot.handlers.handlers import TYPES_ANALYSIS, get_param_order

        for analysis_type in ['by_speciality', 'by_institute', 'by_university']:
            assert analysis_type in TYPES_ANALYSIS
            order = get_param_order(analysis_type)
            assert isinstance(order, list)
            assert len(order) > 0

    def test_filter_combination_and_keyboard_options(self, sample_filter_combination):
        """Проверка что FilterCombination может быть использован для клавиатуры"""
        from bot.keyboards import create_options_keyboard

        options = [(1, sample_filter_combination.level_name)]
        keyboard = create_options_keyboard(options)

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2  # 1 опция + 1 отмена

    def test_parser_categories_match_database_categories(self):
        """Проверка что категории парсера совпадают с ожиданиями"""
        from parser.parser import CATEGORIES

        for key, value in CATEGORIES.items():
            assert key is not None
            assert value is not None
            assert len(key) > 0
            assert len(value) > 0

    def test_config_all_parts_present(self):
        """Проверка что конфигурация содержит все необходимые части"""
        from config.config import Config, TgBot, DatabaseSettings, LogSettings, ParserSettings

        config = Config(
            bot=TgBot(token='test'),
            db=DatabaseSettings('user', 'pass', 'host', 5432, 'db'),
            log=LogSettings('INFO', 'fmt'),
            parser=ParserSettings('url')
        )

        assert config.bot is not None
        assert config.db is not None
        assert config.log is not None
        assert config.parser is not None

    def test_states_and_handlers_consistency(self):
        """Проверка что состояния соответствуют обработчикам"""
        from bot.handlers.handlers import STATE_MAPPING

        for param, state in STATE_MAPPING.items():
            assert state is not None

    def test_keyboard_options_can_be_sent_to_analyzer(self):
        """Проверка что опции из клавиатуры можно отправить в анализатор"""
        from bot.keyboards import create_options_keyboard

        options = [(1, 'Опция 1'), (2, 'Опция 2')]
        keyboard = create_options_keyboard(options)

        callback_data_list = []
        for row in keyboard.inline_keyboard:
            for button in row:
                if button.callback_data != 'cancel':
                    callback_data_list.append(button.callback_data)

        assert 'option_1' in callback_data_list
        assert 'option_2' in callback_data_list

    def test_param_order_progression(self):
        """Проверка логического порядка параметров"""
        from bot.handlers.handlers import get_param_order

        speciality_order = get_param_order('by_speciality')

        assert speciality_order[0] == 'level'

        assert speciality_order.index('inst') > speciality_order.index('level')

        assert speciality_order[-1] == 'category'

    def test_message_text_keys_correspond_to_param_names(self):
        """Проверка что текстовые ключи соответствуют параметрам"""
        from bot.messages.messages import TEXTS, get_param_display_name

        param_names = ['level', 'inst', 'faculty',
                       'speciality', 'typeofstudy', 'category']

        for param in param_names:
            text_key = f'choose_{param}'
            assert text_key in TEXTS, f"Текст для {param} не найден"

            display_name = get_param_display_name(param)
            assert display_name is not None
