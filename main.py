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
        logger.info("🔄 Запуск обновления комбинаций фильтров...")
        await bg_parser.update_filter_combinations()
        logger.info("✅ Комбинации фильтров обновлены")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении комбинаций: {e}")


async def background_parsing_task(bg_parser: BackgroundParser):
    """Задача парсинга данных"""
    try:
        logger.info("🔄 Запуск фонового парсинга...")
        await bg_parser.parse_and_save_all()
        logger.info("✅ Фоновый парсинг завершен")
    except Exception as e:
        logger.error(f"Ошибка в фоновом парсинге: {e}")


async def main():
    config = load_config()

    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )
    try:
        logger.info("📊 Подключаюсь к БД...")
        db = create_db_connection(config)
        logger.info("✅ БД подключена")

        logger.info("🌐 Инициализирую парсер...")
        session = aiohttp.ClientSession()
        parser = Parser(session, config.parser.base_url)
        bg_parser = BackgroundParser(parser, db)
        logger.info("✅ Парсер инициализирован")

        logger.info("🤖 Инициализирую бота...")
        bot = Bot(token=config.bot.token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        logger.info("✅ Бот Инициализирован")

        logger.info("📝 Регистрирую обработчики...")
        router = create_router(db)
        dp.include_router(router)
        logger.info("✅ Обработчики зарегистрированы")

        logger.info("⏰ Запускаю планировщик задач...")
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            update_filter_combinations_task,
            "cron",
            day=1,
            hour=2,
            minute=0,
            args=(bg_parser,),
            id="update_filter_combinations",
            name="Обновление комбинаций фильтров",
            coalesce=True,
            misfire_grace_time=60,
        )
        scheduler.add_job(
            background_parsing_task,
            "cron",
            hour=3,
            minute=0,
            args=(bg_parser,),
            id="kfu_background_parsing",
            name="Фоновый парсинг КФУ",
            coalesce=True,
            misfire_grace_time=60,
        )
        scheduler.start()
        logger.info("✅ Планировщик запущен")
        logger.info("✨ БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ! ✨")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        raise

    finally:
        logger.info("🛑 ОСТАНОВКА БОТА...")
        try:
            scheduler.shutdown()
            logger.info("✅ Планировщик остановлен")
        except:
            pass

        try:
            await bot.session.close()
            logger.info("✅ Сессия бота закрыта")
        except:
            pass

        try:
            await parser.close()
            logger.info("✅ Парсер закрыт")
        except:
            pass

        try:
            await session.close()
            logger.info("✅ HTTP сессия закрыта")
        except:
            pass
        logger.info("🛑 Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
