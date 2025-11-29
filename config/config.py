from dataclasses import dataclass
from environs import Env


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
    timeout: int            # Timeout для запросов (в секундах)


@dataclass
class Config:
    bot: TgBot
    log: LogSettings
    parser: ParserSettings


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)

    # base_dir = Path(__file__).parent.parent
    return Config(
        bot=TgBot(token=env("BOT_TOKEN")),
        log=LogSettings(level=env("LOG_LEVEL"), format=env("LOG_FORMAT")),
        parser=ParserSettings(
            base_url=env("PARSER_BASE_URL"),
            timeout=env.int("PARSER_TIMEOUT"),
        ),
    )
