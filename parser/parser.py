from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver
from urllib.parse import urlencode
from typing import Optional
import pandas as pd
import time
import logging


logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, config, driver: WebDriver):
        """Инициализация парсера"""
        self.config = config
        self.driver = driver
        self.df = None
        self.base_url = config.parser.base_url
        self.current_filters: dict[str, str] = {}

        logger.info(f"Парсер инициализирован")

    def _build_url_with_filters(self, filters: dict[str, str]) -> str:
        """Построить URL со всеми фильтрами

        Args:
            filters (dict): словарь с фильтрами {field_name: value}
        """
        url = f"{self.base_url}?{urlencode(filters)}"
        return url

    def _open_page_with_filters(self):
        """Открыть страницу с фильтрами или без"""
        if self.driver is None:
            raise RuntimeError("Driver не инициализирован")

        if self.current_filters:
            url = self._build_url_with_filters(self.current_filters)
            logger.info(f"📄 Открываю: {url}")
        else:
            url = self.base_url
            logger.info(f"📄 Открываю главную страницу")

        self.driver.get(url)

        wait = WebDriverWait(self.driver, self.config.parser.wait_time)

        logger.info("  ⏳ Жду SELECT элемента p_level...")
        wait.until(EC.presence_of_all_elements_located((By.NAME, "p_level")))
        logger.info("  ✓ SELECT найден")

        logger.info("  ⏳ Жду загрузки Choices.js UI...")
        try:
            wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".choices__list--dropdown .choices__item")
                )
            )
        except:
            logger.warning("⚠️  UI может загружаться...")

        logger.info("  ✓ Страница готова")
        time.sleep(2)

    def _get_choices_container(self, select_name: str):
        """Найти контейнер .choices для SELECT

        Args:
            select_name (str): имя поля SELECT (например: "p_level", "p_faculty")
        """
        if self.driver is None:
            raise RuntimeError("Driver не инициализирован")
        try:
            select_element = self.driver.find_element(By.NAME, select_name)
            choices_container = select_element.find_element(
                By.XPATH,
                "ancestor::div[@class='choices']"
            )
            return choices_container
        except Exception as e:
            logger.error(
                f"❌ Не могу найти контейнер для {select_name}: {e}")
            raise

    def get_select_options(self, select_name) -> dict[str, str]:
        """
        Получить все доступные опции select

        Args:
            select_name (str): имя поля SELECT (например: "p_level", "p_faculty")

        Returns:
            dict: {value: label, ...}
                  Например: {"1": "бакалавриат", "2": "магистратура"}
        """
        try:
            logger.debug(f"  Получаю опции для {select_name}...")

            choices_container = self._get_choices_container(select_name)

            inner_div = choices_container.find_element(
                By.CLASS_NAME, "choices__inner")
            inner_div.click()
            time.sleep(0.5)

            options_elements = choices_container.find_elements(
                By.XPATH,
                ".//div[@data-value and contains(@class, 'choices__item')]"
            )

            logger.debug(f"    ↳ Найдено элементов: {len(options_elements)}")

            options = {}
            for opt in options_elements:
                value = opt.get_attribute("data-value")
                label = opt.text.strip()

                if value and label and value.strip():
                    options[value] = label

            logger.debug(f"    ↳ Извлечено опций: {len(options)}")
            return options

        except Exception as e:
            logger.error(f"❌ Ошибка при получении опций {select_name}: {e}")
            return {}

    def apply_filter(self, field_name, value) -> bool:
        """
        Применить один фильтр
        Выбираем опцию, потом перезагружаем страницу с новыми фильтрами

        Args:
            field_name (str): имя поля SELECT (например: "p_level", "p_faculty")
            value (str): значение фильтра (например: "1", "2")
        """
        if self.driver is None:
            raise RuntimeError("Driver не инициализирован")
        try:
            logger.info(f"  ⚙️  Применяю фильтр {field_name}={value}...")

            choices_container = self._get_choices_container(field_name)

            inner_div = choices_container.find_element(
                By.CLASS_NAME, "choices__inner")
            inner_div.click()
            time.sleep(0.5)

            option_element = choices_container.find_element(
                By.XPATH,
                f".//div[@data-value='{value}' and contains(@class, 'choices__item')]"
            )

            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);",
                option_element
            )
            time.sleep(0.3)

            self.driver.execute_script(
                "arguments[0].click();",
                option_element
            )

            logger.debug(f"    ✓ Опция выбрана")

            # Добавляем фильтр в текущие
            self.current_filters[field_name] = value
            logger.info(f"    📋 Текущие фильтры: {self.current_filters}")

            time.sleep(1)

            logger.info(f"    🔄 Перезагружаю страницу с фильтрами...")
            self._open_page_with_filters()

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при применении {field_name}={value}: {e}")
            raise

    # def fetch_with_filters(self, filters=None):
    #     """
    #     Получить данные с фильтрами

    #     Args:
    #         filters (dict): словарь с фильтрами {field_name: value}

    #     Returns:
    #         pd.DataFrame: таблица с данными
    #     """
    #     if filters is None:  # тоже на подумать
    #         logger.info("Фильтры не указаны.")
    #         return None
    #     try:
    #         self._open_page_with_filters()
    #         if self.driver is None:
    #             raise RuntimeError("Driver не инициализирован")
    #         logger.info(f"⚙️  Применяю фильтры...")

    #         for i, (field_name, value) in enumerate(filters.items(), 1):
    #             logger.info(
    #                 f"[{i}/{len(filters)}] Применяю {field_name}={value}")
    #             self.apply_filter(field_name, value)
    #             logger.info(f"✓ Фильтр {field_name} применён\n")

    #         logger.info("⏳ Жду загрузку таблицы...")
    #         wait = WebDriverWait(self.driver, self.config.parser.timeout)
    #         wait.until(
    #             EC.presence_of_all_elements_located((By.TAG_NAME, "table"))
    #         )
    #         time.sleep(self.config.parser.wait_time)

    #         logger.info("📥 Извлекаю данные из таблицы...")
    #         table_element = self.driver.find_element(By.TAG_NAME, "table")
    #         table_html = table_element.get_attribute("outerHTML")

    #         if table_html is None:
    #             logger.error("❌ HTML таблицы пуст")
    #             return None
    #         df_list = pd.read_html(table_html)

    #         if not df_list:
    #             logger.error("❌ Таблица не распарсилась")
    #             return None

    #         self.df = df_list[0]
    #         logger.info(
    #             f"✓ Загружено {len(self.df)} строк, {len(self.df.columns)} колонок")

    #         return self.df

    #     except Exception as e:
    #         logger.error(f"❌ Ошибка: {e}", exc_info=True)
    #         return None

    def save_data(self, filename, format="csv"):  # тоже на подумать
        """Сохранить данные"""
        if self.df is None:
            logger.error("❌ Нет данных")
            return False

        try:
            logger.info(f"💾 Сохраняю в {format}: {filename}")

            if format == "excel":
                self.df.to_excel(filename, index=False)
            elif format == "csv":
                self.df.to_csv(filename, index=False)
            elif format == "json":
                self.df.to_json(filename)

            logger.info(f"✓ Сохранено ({len(self.df)} записей)")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False

    def close(self):
        """Закрыть браузер"""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("🛑 Браузер закрыт")
            except:
                pass
            finally:
                self.driver = None

    # def __del__(self):
    #     self.close()

    # def __enter__(self):
    #     return self

    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     self.close()
    #     return False
