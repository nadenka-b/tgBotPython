from dataclasses import dataclass
from environs import Env
from pathlib import Path
# не забыть низ

KFU_URL = "https://abiturient.kpfu.ru/entrant/abit_entrant_originals_list"
DEFAULT_PARSER_TIMEOUT = 10
DEFAULT_PARSER_WAIT_TIME = 2
DEFAULT_PARSER_RETRY_COUNT = 3
DEFAULT_PARSER_CACHE_TTL = 3600  # 1 час

SELENIUM_DEFAULT_HEADLESS = False


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту


@dataclass
class LogSettings:
    level: str
    format: str


@dataclass
class ParserSettings:
    base_url: str           # URL страницы КФУ
    timeout: int            # Таймаут Selenium (сек)
    headless: bool          # Headless режим браузера (bool)
    wait_time: int          # Время ожидания загрузки (сек)
    retry_count: int        # Кол-во повторов при ошибке
    cache_ttl: int          # Время жизни кеша (сек)
    pool_size: int
    max_workers: int


# @dataclass
# class PathSettings:
#     """Пути к файлам и директориям"""
#     data_dir: Path          # data/
#     cache_dir: Path         # data/cache/
#     reports_dir: Path       # data/reports/
#     logs_dir: Path          # logs/

#     def __post_init__(self):
#         """Создать директории если их нет"""
#         for path in [self.data_dir, self.cache_dir, self.reports_dir, self.logs_dir]:
#             path.mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    bot: TgBot
    log: LogSettings
    parser: ParserSettings
    # paths: PathSettings


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)

    # base_dir = Path(__file__).parent.parent
    return Config(
        bot=TgBot(token=env("BOT_TOKEN")),
        log=LogSettings(level=env("LOG_LEVEL"), format=env("LOG_FORMAT")),
        parser=ParserSettings(
            base_url=env("PARSER_BASE_URL", KFU_URL),

            # Таймауты - публичные, но для удобства могут быть в .env
            timeout=env.int("PARSER_TIMEOUT", DEFAULT_PARSER_TIMEOUT),
            headless=env.bool("PARSER_HEADLESS", SELENIUM_DEFAULT_HEADLESS),
            wait_time=env.int("PARSER_WAIT_TIME", DEFAULT_PARSER_WAIT_TIME),
            retry_count=env.int("PARSER_RETRY_COUNT",
                                DEFAULT_PARSER_RETRY_COUNT),
            cache_ttl=env.int("PARSER_CACHE_TTL", DEFAULT_PARSER_CACHE_TTL),
            pool_size=2,
            max_workers=5,
        ),
        # paths=PathSettings(  # ВОПРОСИКИ
        #     data_dir=base_dir / "data",
        #     cache_dir=base_dir / "data" / "cache",
        #     reports_dir=base_dir / "data" / "reports",
        #     logs_dir=base_dir / "logs"
        # ),
    )
