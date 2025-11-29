import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
# from database import Database
from parser.parser_manager import ParseManager
from bot.handlers import handlers
from aiogram import Bot, Dispatcher
from config.config import Config, load_config
from parser.parser import Parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Инициализируем логгер
logger = logging.getLogger(__name__)

bot = None
dp = None
database = None
parse_manager = None


async def main():
    """Главная функция запуска бота"""

    global bot, dp, database, parse_manager

    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК БОТА")
    logger.info("=" * 60)

    # ============ ЗАГРУЗ КОНФИГ ============

    logger.info("📋 Загружаю конфиг...")
    config = load_config()
    logger.info(f"✓ Конфиг загружен")

    # ============ ИНИЦИАЛИЗИРУЮ БД ============

    # logger.info("💾 Инициализирую БД...")
    # try:
    #     database = Database(
    #         db_url=config.database.url,
    #         pool_size=config.database.pool_size,
    #         max_overflow=config.database.max_overflow
    #     )
    #     logger.info("✅ БД готова")
    # except Exception as e:
    #     logger.error(f"❌ Ошибка БД: {e}")
    #     raise

    # ============ ИНИЦИАЛИЗИРУЮ ПУЛ БРАУЗЕРОВ ============

    logger.info("🌐 Инициализирую пул браузеров...")
    try:
        parse_manager = ParseManager(
            config=config,
            pool_size=config.parser.pool_size,
            max_workers=config.parser.max_workers
        )
        logger.info("✅ Пул браузеров готов")
    except Exception as e:
        logger.error(f"❌ Ошибка пула браузеров: {e}")
        if database:
            database.close()
        raise

    # ============ ИНИЦИАЛИЗИРУЮ БОТА ============

    logger.info("🤖 Инициализирую бота...")

    bot = Bot(token=config.bot.token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Передаём объекты в handlers
    handlers.set_parse_manager(parse_manager)
    handlers.set_config(config)
    handlers.set_database(database)

    # Подключаем маршруты
    dp.include_router(handlers.router)

    logger.info("✅ Бот инициализирован")

    # ============ ЗАПУСК БОТА ============

    logger.info("=" * 60)
    logger.info("✅ ВСЕ КОМПОНЕНТЫ ГОТОВЫ")
    logger.info("=" * 60)
    logger.info("📡 Начинаю слушать сообщения...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # ============ GRACEFUL SHUTDOWN ============

        logger.info("=" * 60)
        logger.info("🛑 ВЫКЛЮЧЕНИЕ БОТА")
        logger.info("=" * 60)

        logger.info("🔌 Закрываю пул браузеров...")
        if parse_manager:
            parse_manager.close_all()
            logger.info("✓ Браузеры закрыты")

        logger.info("💾 Закрываю БД...")
        if database:
            database.close()
            logger.info("✓ БД закрыта")

        logger.info("🤖 Закрываю бота...")
        if bot:
            await bot.session.close()
            logger.info("✓ Бот отключен")

        logger.info("=" * 60)
        logger.info("✅ БОТ ВЫКЛЮЧЕН")
        logger.info("=" * 60)


if __name__ == "__main__":
    print("MAIN STARTED")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Прерывание пользователем")
    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
