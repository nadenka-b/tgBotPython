from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str


@dataclass
class DatabaseSettings:
    user: str
    password: str
    host: str
    port: int
    name: str


@dataclass
class LogSettings:
    level: str
    format: str


@dataclass
class ParserSettings:
    base_url: str


@dataclass
class Config:
    bot: TgBot
    db: DatabaseSettings
    log: LogSettings
    parser: ParserSettings


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)

    return Config(
        bot=TgBot(token=env("BOT_TOKEN")),
        db=DatabaseSettings(user=env('DB_USER'),
                            password=env('DB_PASSWORD'),
                            host=env('DB_HOST', default='localhost'),
                            port=env.int('DB_PORT', default=5432),
                            name=env('DB_NAME'),),
        log=LogSettings(level=env("LOG_LEVEL"),
                        format=env("LOG_FORMAT")),
        parser=ParserSettings(base_url=env("PARSER_BASE_URL")),
    )
