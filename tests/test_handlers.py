import pytest


class TestHandlers:
    """Тесты для обработчиков"""

    @pytest.mark.parametrize("analysis_type,expected_order", [
        ('by_speciality', ['level', 'inst', 'faculty',
         'speciality', 'typeofstudy', 'category']),
        ('by_institute', ['level', 'inst', 'faculty', 'category']),
        ('by_university', ['level', 'inst', 'category']),
    ])
    def test_param_order_for_analysis_types(self, analysis_type, expected_order):
        """Проверка правильного порядка параметров для каждого типа анализа"""
        from bot.handlers.handlers import get_param_order

        order = get_param_order(analysis_type)
        assert order == expected_order

    def test_param_order_speciality_has_all_params(self):
        """Проверка что для анализа направления все параметры"""
        from bot.handlers.handlers import get_param_order

        order = get_param_order('by_speciality')

        assert 'level' in order
        assert 'inst' in order
        assert 'faculty' in order
        assert 'speciality' in order
        assert 'typeofstudy' in order
        assert 'category' in order

    def test_param_order_institute_fewer_params(self):
        """Проверка что для анализа института меньше параметров"""
        from bot.handlers.handlers import get_param_order

        speciality_order = get_param_order('by_speciality')
        institute_order = get_param_order('by_institute')

        assert len(institute_order) < len(speciality_order)
        assert 'speciality' not in institute_order

    def test_param_order_university_minimal_params(self):
        """Проверка что для анализа университета минимум параметров"""
        from bot.handlers.handlers import get_param_order

        university_order = get_param_order('by_university')

        assert len(university_order) == 3
        assert university_order == ['level', 'inst', 'category']

    def test_param_order_first_param_always_level(self):
        """Проверка что первый параметр всегда уровень образования"""
        from bot.handlers.handlers import get_param_order

        for analysis_type in ['by_speciality', 'by_institute', 'by_university']:
            order = get_param_order(analysis_type)
            assert order[0] == 'level', f"Первый параметр для {analysis_type} должен быть level"

    def test_param_order_category_always_last(self):
        """Проверка что категория всегда последний параметр"""
        from bot.handlers.handlers import get_param_order

        for analysis_type in ['by_speciality', 'by_institute', 'by_university']:
            order = get_param_order(analysis_type)
            assert order[-1] == 'category', f"Последний параметр для {analysis_type} должен быть category"

    def test_types_analysis_has_all_types(self):
        """Проверка что все типы анализа определены"""
        from bot.handlers.handlers import TYPES_ANALYSIS

        assert 'by_speciality' in TYPES_ANALYSIS
        assert 'by_institute' in TYPES_ANALYSIS
        assert 'by_university' in TYPES_ANALYSIS

    def test_types_analysis_values_are_strings(self):
        """Проверка что значения типов анализа - строки"""
        from bot.handlers.handlers import TYPES_ANALYSIS

        for key, value in TYPES_ANALYSIS.items():
            assert isinstance(value, str)

    def test_param_orders_structure(self):
        """Проверка структуры PARAM_ORDERS"""
        from bot.handlers.handlers import PARAM_ORDERS

        for analysis_type, order in PARAM_ORDERS.items():
            assert isinstance(order, list)
            assert len(order) > 0
            for param in order:
                assert isinstance(param, str)
