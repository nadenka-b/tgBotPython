import pytest


class TestStates:
    """Тесты для FSM состояний"""

    def test_all_analysis_states_exist(self):
        """Проверка наличие всех нужных состояний"""
        from bot.states import AnalysisStates

        required_states = {
            'waiting_for_analysis_type',
            'waiting_for_level',
            'waiting_for_inst',
            'waiting_for_faculty',
            'waiting_for_speciality',
            'waiting_for_typeofstudy',
            'waiting_for_category',
            'processing'
        }

        for state in required_states:
            assert hasattr(
                AnalysisStates, state), f"Состояние {state} не определено"

    def test_waiting_for_level_state_exists(self):
        """Проверка что состояние ожидания уровня существует"""
        from bot.states import AnalysisStates

        state = AnalysisStates.waiting_for_level
        assert state is not None

    def test_processing_state_exists(self):
        """Проверка что состояние обработки существует"""
        from bot.states import AnalysisStates

        state = AnalysisStates.processing
        assert state is not None


class TestConfig:
    """Тесты для конфигурации"""

    def test_tgbot_config_creation(self):
        """Проверка создания TgBot конфигурации"""
        from config.config import TgBot

        bot_config = TgBot(token='test_token_123')
        assert bot_config.token == 'test_token_123'

    def test_database_settings_creation(self):
        """Проверка создания DatabaseSettings"""
        from config.config import DatabaseSettings

        db_config = DatabaseSettings(
            user='test_user',
            password='test_pass',
            host='localhost',
            port=5432,
            name='test_db'
        )

        assert db_config.user == 'test_user'
        assert db_config.password == 'test_pass'
        assert db_config.host == 'localhost'
        assert db_config.port == 5432
        assert db_config.name == 'test_db'

    def test_log_settings_creation(self):
        """Проверка создания LogSettings"""
        from config.config import LogSettings

        log_config = LogSettings(level='INFO', format='%(message)s')
        assert log_config.level == 'INFO'
        assert log_config.format == '%(message)s'

    def test_parser_settings_creation(self):
        """Проверка создания ParserSettings"""
        from config.config import ParserSettings

        parser_config = ParserSettings(base_url='https://example.com')
        assert parser_config.base_url == 'https://example.com'

    def test_config_all_components(self):
        """Проверка полной конфигурации со всеми компонентами"""
        from config.config import Config, TgBot, DatabaseSettings, LogSettings, ParserSettings

        config = Config(
            bot=TgBot(token='token'),
            db=DatabaseSettings('user', 'pass', 'host', 5432, 'db'),
            log=LogSettings('INFO', '%(message)s'),
            parser=ParserSettings('https://example.com')
        )

        assert config.bot.token == 'token'
        assert config.db.user == 'user'
        assert config.log.level == 'INFO'
        assert config.parser.base_url == 'https://example.com'

    @pytest.mark.parametrize("level,format_str", [
        ('DEBUG', '%(levelname)s - %(message)s'),
        ('INFO', '%(asctime)s - %(message)s'),
        ('WARNING', '%(message)s'),
        ('ERROR', '%(filename)s - %(message)s'),
    ])
    def test_log_settings_with_different_levels(self, level, format_str):
        """Проверка LogSettings с разными уровнями"""
        from config.config import LogSettings

        log_config = LogSettings(level=level, format=format_str)

        assert log_config.level == level
        assert log_config.format == format_str

    def test_database_settings_port_is_int(self):
        """Проверка что порт БД - целое число"""
        from config.config import DatabaseSettings

        db_config = DatabaseSettings('user', 'pass', 'localhost', 5432, 'db')
        assert isinstance(db_config.port, int)
        assert db_config.port > 0

    def test_config_dataclass_structure(self):
        """Проверка что Config имеет правильную структуру"""
        from config.config import Config, TgBot, DatabaseSettings, LogSettings, ParserSettings

        bot = TgBot(token='test')
        db = DatabaseSettings('u', 'p', 'h', 5432, 'd')
        log = LogSettings('INFO', 'fmt')
        parser = ParserSettings('url')

        config = Config(bot=bot, db=db, log=log, parser=parser)

        assert hasattr(config, 'bot')
        assert hasattr(config, 'db')
        assert hasattr(config, 'log')
        assert hasattr(config, 'parser')
