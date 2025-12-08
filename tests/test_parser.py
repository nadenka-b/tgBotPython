import pytest


class TestParser:
    """Тесты для парсера"""

    def test_parser_initialization(self):
        """Проверка инициализации парсера"""
        from parser import Parser

        base_url = 'https://abiturient.kpfu.ru'
        parser = Parser(session=None, base_url=base_url)

        assert parser.base_url == base_url
        assert parser.session is None

    def test_category_mapping_has_all_categories(self):
        """Проверка что все категории маппированы"""
        from parser.parser import CATEGORIES

        assert 'на основные места' in CATEGORIES
        assert 'целевой квоты' in CATEGORIES
        assert 'особой квоты' in CATEGORIES
        assert 'отдельной квоты' in CATEGORIES
        assert 'без вступительных испытаний' in CATEGORIES

    def test_category_mapping_values_correct(self):
        """Проверка что категории маппируются правильно"""
        from parser.parser import CATEGORIES

        assert CATEGORIES['на основные места'] == 'общий конкурс'
        assert CATEGORIES['целевой квоты'] == 'целевая квота'
        assert CATEGORIES['без вступительных испытаний'] == 'без вступительных испытаний'

    def test_all_categories_map_to_strings(self):
        """Проверка что все категории маппируются на строки"""
        from parser.parser import CATEGORIES

        for key, value in CATEGORIES.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_needed_columns_has_all_fields(self):
        """Проверка что все нужные столбцы определены"""
        from parser.parser import NEEDED_COLUMNS

        required_columns = {
            'Уникальный id абитуриента ЕПГУ',
            'id абитуриента',
            'Сумма конкурсных баллов',
            'Заявление о согласии на зачисление',
            'Статус',
            'Примечание'
        }

        assert required_columns.issubset(set(NEEDED_COLUMNS.keys()))

    def test_needed_columns_mapping_correct(self):
        """Проверка правильности маппинга столбцов"""
        from parser.parser import NEEDED_COLUMNS

        assert NEEDED_COLUMNS['Уникальный id абитуриента ЕПГУ'] == 'epgu_id'
        assert NEEDED_COLUMNS['Сумма конкурсных баллов'] == 'score'
        assert NEEDED_COLUMNS['Заявление о согласии на зачисление'] == 'agreement'
        assert NEEDED_COLUMNS['Статус'] == 'status'
        assert NEEDED_COLUMNS['Примечание'] == 'note'

    def test_needed_columns_values_are_strings(self):
        """Проверка что все значения в маппинге - строки"""
        from parser.parser import NEEDED_COLUMNS

        for key, value in NEEDED_COLUMNS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
