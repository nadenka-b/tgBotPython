import pytest


@pytest.fixture
def sample_options():
    """Пример опций для тестирования клавиатуры"""
    return [
        (1, 'Бакалавриат'),
        (2, 'Магистратура'),
        (3, 'Специалитет')
    ]


class TestKeyboards:
    """Тесты для создания клавиатур"""

    def test_main_menu_keyboard_structure(self):
        """Проверка структуры главного меню"""
        from bot.keyboards import get_main_menu

        keyboard = get_main_menu()

        assert keyboard is not None
        assert hasattr(keyboard, 'inline_keyboard')
        assert isinstance(keyboard.inline_keyboard, list)
        assert len(keyboard.inline_keyboard) > 0

    def test_main_menu_has_analysis_button(self):
        """Проверка наличие кнопки анализа в главном меню"""
        from bot.keyboards import get_main_menu

        keyboard = get_main_menu()

        callback_data_list = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_data_list.append(button.callback_data)

        assert 'start_analysis' in callback_data_list

    def test_main_menu_has_help_button(self):
        """Проверка наличие кнопки справки"""
        from bot.keyboards import get_main_menu

        keyboard = get_main_menu()

        callback_data_list = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_data_list.append(button.callback_data)

        assert 'help' in callback_data_list

    def test_analysis_type_menu_contains_all_types(self):
        """Проверка что меню содержит все типы анализа"""
        from bot.keyboards import get_analysis_type_menu

        keyboard = get_analysis_type_menu()
        callback_data_list = []

        for row in keyboard.inline_keyboard:
            for button in row:
                callback_data_list.append(button.callback_data)

        expected_callbacks = {
            'analysis_type_by_speciality',
            'analysis_type_by_institute',
            'analysis_type_by_university',
            'cancel'
        }

        assert expected_callbacks.issubset(set(callback_data_list))

    def test_options_keyboard_creation_with_options(self, sample_options):
        """Проверка создания клавиатуры из опций"""
        from bot.keyboards import create_options_keyboard

        keyboard = create_options_keyboard(sample_options)

        assert len(keyboard.inline_keyboard) == 4

    def test_options_keyboard_has_correct_callback_data(self, sample_options):
        """Проверка что callback_data опций правильные"""
        from bot.keyboards import create_options_keyboard

        keyboard = create_options_keyboard(sample_options)

        first_button = keyboard.inline_keyboard[0][0]
        assert first_button.callback_data == 'option_1'
        assert first_button.text == 'Бакалавриат'

        second_button = keyboard.inline_keyboard[1][0]
        assert second_button.callback_data == 'option_2'
        assert second_button.text == 'Магистратура'

        third_button = keyboard.inline_keyboard[2][0]
        assert third_button.callback_data == 'option_3'
        assert third_button.text == 'Специалитет'

    def test_options_keyboard_has_cancel_button(self, sample_options):
        """Проверка наличие кнопки отмены"""
        from bot.keyboards import create_options_keyboard

        keyboard = create_options_keyboard(sample_options)

        cancel_button = keyboard.inline_keyboard[-1][0]
        assert cancel_button.callback_data == 'cancel'
        assert '❌' in cancel_button.text or 'Отмена' in cancel_button.text

    def test_options_keyboard_empty_list(self):
        """Проверка создания клавиатуры с пустым списком"""
        from bot.keyboards import create_options_keyboard

        keyboard = create_options_keyboard([])

        assert len(keyboard.inline_keyboard) == 1
        assert keyboard.inline_keyboard[0][0].callback_data == 'cancel'

    def test_new_analysis_keyboard_structure(self):
        """Проверка структуры клавиатуры после анализа"""
        from bot.keyboards import get_new_analysis_keyboard

        keyboard = get_new_analysis_keyboard()

        callback_data_list = []
        for row in keyboard.inline_keyboard:
            for button in row:
                callback_data_list.append(button.callback_data)

        assert 'start_analysis' in callback_data_list
        assert 'main_menu' in callback_data_list
