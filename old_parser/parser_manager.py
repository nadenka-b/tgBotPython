from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import Dict, Optional
import logging
import asyncio
from .parser import Parser


logger = logging.getLogger(__name__)


class ParseManager:
    """Менеджер парсинга с пулом браузеров"""

    def __init__(self, config, pool_size: int = 2, max_workers: int = 5):
        self.config = config
        self.pool_size = pool_size
        self.max_workers = max_workers
        self.browser_pool = Queue(maxsize=pool_size)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        logger.info(f"🚀 Инициализирую ParseManager...")
        logger.info(f"   • Размер пула браузеров: {pool_size}")
        logger.info(f"   • Макимум потоков: {max_workers}")

        # ГЛАВНОЕ: Создаём браузеры один раз при запуске
        self._create_browser_pool()

        logger.info(f"✅ ParseManager готов!")

    def _create_browser_pool(self):
        """Создать все браузеры для пула"""

        for i in range(self.pool_size):
            try:
                logger.info(f"   ⏳ Создаю браузер #{i+1}...")

                options = Options()
                if self.config.parser.headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")

                driver = webdriver.Chrome(options=options)
                self.browser_pool.put(driver)

                logger.info(f"   ✓ Браузер #{i+1} создан и добавлен в пул")

            except Exception as e:
                logger.error(f"   ❌ Ошибка при создании браузера: {e}")
                raise

    def get_driver(self, timeout: int = 5, user_id: Optional[int] = None):
        """
        Получить браузер из пула

        Args:
            timeout: Сколько секунд ждать браузер (по умолчанию 5)
            user_id: ID пользователя (для логирования)

        Returns:
            webdriver.Chrome или None если таймаут
        """
        pool_size_before = self.browser_pool.qsize()
        if user_id:
            logger.info(f"👤 Пользователь {user_id}: запросил браузер")
            logger.info(
                f"   Браузеров в пуле: {pool_size_before}/{self.pool_size}")
        try:
            driver = self.browser_pool.get(timeout=timeout)
            pool_size_after = self.browser_pool.qsize()
            if user_id:
                logger.info(f"   ✓ Браузер выдан")
                logger.info(f"   Осталось: {pool_size_after}/{self.pool_size}")
            return driver
        except Empty:
            logger.warning(f"⏳ Пул переполнен (таймаут {timeout}s)")
            if user_id:
                logger.warning(f"   Пользователь {user_id} не получил браузер")
            return None

    def return_driver(self, driver, user_id: Optional[int] = None):
        """
        Вернуть браузер в пул

        Args:
            driver: webdriver.Chrome объект
            user_id: ID пользователя (для логирования)
        """
        if driver is None:
            return
        try:
            pool_size_before = self.browser_pool.qsize()
            self.browser_pool.put(driver, timeout=2)
            pool_size_after = self.browser_pool.qsize()
            if user_id:
                logger.info(f"👤 Пользователь {user_id}: вернул браузер")
            logger.debug(
                f"   Пул: {pool_size_before} → {pool_size_after}/{self.pool_size}")
        except Exception as e:
            logger.error(f"❌ Ошибка при возврате браузера: {e}")

    def apply_filter_sync(self, driver, filters_dict: Dict[str, str], field_name: str, value: str):
        """Синхронная функция для работы в отдельном потоке"""
        try:
            logger.info(f"⚙️ Применяю фильтр {field_name}={value}...")
            parser = Parser(self.config, driver)

            if not filters_dict:
                parser._open_page_with_filters()

            parser.apply_filter(field_name, value)

            logger.info(f"✓ Фильтр {field_name}={value} применён")

            return {"status": "ok",  "driver": driver}
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            return {"status": "error", "error": str(e)}

    async def apply_filter_async(self, driver, filters_dict: Dict[str, str], field_name: str, value: str):
        """Асинхронная обёртка"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self.apply_filter_sync,
            driver,
            filters_dict,
            field_name,
            value
        )
        return result

    def close_all(self):
        """Закрыть все браузеры"""
        logger.info("🛑 Закрываю пул браузеров...")
        while not self.browser_pool.empty():
            try:
                driver = self.browser_pool.get_nowait()
                driver.quit()
            except:
                pass
        self.executor.shutdown()
        logger.info("🛑 Все браузеры закрыты")
