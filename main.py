import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.config import load_config
from parser.parser import Parser
from parser.background_parser import BackgroundParser
from database.db import create_db_connection
from bot.handlers.handlers import create_router


logger = logging.getLogger(__name__)


async def update_filter_combinations_task(bg_parser: BackgroundParser):
    """Задача обновления комбинаций"""
    try:
        await bg_parser.update_filter_combinations()
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении комбинаций: {e}")


async def background_parsing_task(bg_parser: BackgroundParser):
    """Задача парсинга данных"""
    try:
        await bg_parser.parse_and_save_all()
    except Exception as e:
        logger.error(f"Ошибка в фоновом парсинге: {e}")


async def main():
    config = load_config()
    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )

    db = create_db_connection(config)

    session = aiohttp.ClientSession()
    parser = Parser(session, config.parser.base_url)
    bg_parser = BackgroundParser(parser, db)

    bot = Bot(token=config.bot.token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    router = create_router(parser, db)
    dp.include_router(router)

    logger.info("🚀 Бот запущен")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_filter_combinations_task,
        "cron",
        day=1,           # 1-е число месяца
        hour=2,
        minute=0,
        args=(bg_parser,),
        id="update_filter_combinations",
        name="Обновление комбинаций фильтров"
    )
    scheduler.add_job(
        background_parsing_task,
        "cron",
        hour=3,
        minute=0,
        args=(bg_parser,),
        id="kfu_background_parsing",
        name="Фоновый парсинг КФУ"
    )
    scheduler.start()
    logger.info("✅ Планировщик запущен")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        await parser.close()
        logger.info("🛑 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
