import pytest


@pytest.fixture
def sample_filter_combination():
    """Пример комбинации фильтров"""
    from database.models import FilterCombination

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


class TestModels:
    """Тесты для моделей данных"""

    def test_filter_combination_to_dict_conversion(self, sample_filter_combination):
        """Проверка преобразования FilterCombination в dict"""
        filters_dict = sample_filter_combination.to_filters_dict()

        assert isinstance(filters_dict, dict)
        assert filters_dict['p_level'] == '1'
        assert filters_dict['p_inst'] == '0'
        assert filters_dict['p_faculty'] == '5'
        assert filters_dict['p_speciality'] == '166'
        assert filters_dict['p_typeofstudy'] == '1'
        assert filters_dict['p_category'] == '0'

    def test_filter_combination_dict_has_all_keys(self, sample_filter_combination):
        """Проверка что все параметры присутствуют в словаре"""
        filters_dict = sample_filter_combination.to_filters_dict()

        required_keys = {'p_level', 'p_inst', 'p_faculty',
                         'p_speciality', 'p_typeofstudy', 'p_category'}
        assert set(filters_dict.keys()) == required_keys

    def test_filter_combination_values_are_strings(self, sample_filter_combination):
        """Проверка что все значения в dict - строки"""
        filters_dict = sample_filter_combination.to_filters_dict()

        for key, value in filters_dict.items():
            assert isinstance(
                value, str), f"Значение {key} должно быть строкой, получен {type(value)}"
