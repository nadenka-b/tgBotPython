import asyncio
import logging

from .parser import Parser
from database import Database

from datetime import datetime

logger = logging.getLogger(__name__)


class BackgroundParser:
    """Фоновый парсер для периодической загрузки данных"""

    def __init__(self, parser: Parser, db: Database):
        self.parser: Parser = parser
        self.db = db

    async def get_all_filter_combinations(self) -> list[dict[str, dict[str, str]]]:
        """
        Получить все возможные комбинации фильтров

        Returns:
            Список словарей с комбинациями фильтров
            [{
                'level': {'value': '1', 'name': 'Бакалавриат'},
                'faculty': {'value': '5', 'name': 'Факультет инженерии'},
                ...
            }, ...]
        """
        logger.info("🚀 Начинаю получение комбинаций...")

        html = await self.parser.fetch_page({})
        levels = self.parser.extract_filter_options(html, 'level')
        logger.debug(f"Уровни образования: {levels}")

        institutes = self.parser.extract_filter_options(html, 'inst')
        logger.debug(f"Университет: {institutes}")

        categories = self.parser.extract_filter_options(html, 'category')
        logger.debug(f"Категории: {categories}")

        combinations = []

        for level in levels:
            level_value = level[0]
            level_name = level[-1]

            for inst in institutes:
                inst_value = inst[0]
                inst_name = inst[-1]

                faculties_params = {'p_level': level_value,
                                    'p_inst': inst_value}
                html = await self.parser.fetch_page(faculties_params)
                faculties = self.parser.extract_filter_options(html, 'faculty')
                logger.debug(f"Институты: {faculties}")

                for faculty in faculties:
                    faculty_value = faculty[0]
                    faculty_name = faculty[-1]

                    spec_params = {'p_level': level_value,
                                   'p_inst': inst_value,
                                   'p_faculty': faculty_value}
                    html = await self.parser.fetch_page(spec_params)
                    specialities = self.parser.extract_filter_options(
                        html, 'speciality')
                    logger.debug(f"Специальности: {specialities}")

                    for speciality in specialities:
                        speciality_value = speciality[0]
                        speciality_name = speciality[-1]

                        study_params = {
                            'p_level': level_value,
                            'p_inst': inst_value,
                            'p_faculty': faculty_value,
                            'p_speciality': speciality_value
                        }
                        html = await self.parser.fetch_page(study_params)
                        studies = self.parser.extract_filter_options(
                            html, 'typeofstudy')

                        for study in studies:
                            typeofstudy_value = study[0]
                            typeofstudy_name = study[-1]

                            for category in categories:
                                category_value = category[0]
                                category_name = category[-1]

                                combo = {
                                    'level': {'value': level_value, 'name': level_name},
                                    'faculty': {'value': faculty_value, 'name': faculty_name},
                                    'inst': {'value': inst_value, 'name': inst_name},
                                    'speciality': {'value': speciality_value, 'name': speciality_name},
                                    'typeofstudy': {'value': typeofstudy_value, 'name': typeofstudy_name},
                                    'category': {'value': category_value, 'name': category_name},
                                }
                                combinations.append(combo)
                                logger.debug(
                                    f"✅ Добавлена комбинация #{len(combinations)}: {combo}")
        logger.info(f"🎉 Всего получено {len(combinations)} комбинаций")
        return combinations

    async def update_filter_combinations(self):
        """
        Обновить таблицу комбинаций
        """
        logger.info(
            f"🔄 Начинаю обновление таблицы комбинаций {datetime.now()}...")

        try:
            combinations = await self.get_all_filter_combinations()

            for idx, combo_data in enumerate(combinations, 1):
                try:
                    self.db.get_or_create_filter_combination(combo_data)

                    if idx % 100 == 0:
                        logger.info(
                            f"Обновлено комбинаций [{idx}/{len(combinations)}]")
                except Exception as e:
                    logger.error(f"❌ Ошибка при сохранении комбинации: {e}")
                    continue

            logger.info(
                f"✅ Таблица комбинаций обновлена {datetime.now()}. Было обработано {len(combinations)} записей")

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении комбинаций: {e}")

    async def parse_and_save_all(self):
        """Парсить ВСЕ комбинации и сохранить в БД"""
        logger.info(f"🚀 Начинается фоновый парсинг данных {datetime.now()}...")

        try:
            combinations = self.db.get_all_filter_combinations()
            logger.info(f"📊 Найдено {len(combinations)} комбинаций фильтров")
            if not combinations:
                logger.warning("⚠️ Нет комбинаций в БД")
                return

            total_records = 0

            for idx, combo in enumerate(combinations, 1):
                filters = combo.to_filters_dict()
                logger.debug(
                    f"[{idx}/{len(combinations)}] Парсинг комбинации {combo.id}...")

                try:
                    html = await self.parser.fetch_page(filters)
                    df = self.parser.extract_table_data(html)

                    if df is not None and not df.empty:
                        records = df.to_dict('records')

                        saved = await self.db.save_data_batch(records, combo)
                        total_records += saved

                        logger.info(f"✅ Сохранено {saved} записей")
                    else:
                        logger.warning(
                            f"⚠️ Таблица пуста для комбинации {combo.id}")

                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(
                        f"❌ Ошибка при парсинге комбинации {combo.id}: {e}")
                    continue

            logger.info(
                f"🎉 Парсинг завершен {datetime.now()}! Всего сохранено {total_records} записей")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
