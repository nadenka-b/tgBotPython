import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.config import Config, load_config
from bot.handlers.handlers import create_router
from parser.parser import Parser

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    config = load_config()
    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )

    session = aiohttp.ClientSession()
    parser = Parser(session, config.parser.base_url)

    bot = Bot(token=config.bot.token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    router = create_router(parser)
    dp.include_router(router)

    logger.info("🚀 Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await parser.close()
        logger.info("🛑 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
