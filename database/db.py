import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.config import Config
from .models import Base, FilterCombination, Statistics

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с БД"""

    def __init__(self, db_url: str):
        """
        Args:
            db_url: Connection string (postgresql://user:pass@localhost/dbname)
        """
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine, expire_on_commit=False)

    def init_db(self):
        """Создать все таблицы"""
        Base.metadata.create_all(self.engine)
        logger.info("✅ База данных инициализирована")

    def get_session(self) -> Session:
        """Получить новую сессию"""
        return self.SessionLocal()

    def get_or_create_filter_combination(self, filters_dict: dict) -> FilterCombination:
        """
        Получить комбинацию фильтров или создать новую

        Args:
            filters_dict: Словарь с value и name для каждого фильтра
            {
                'level': {'value': '1', 'name': 'Бакалавриат'},
                'faculty': {'value': '5', 'name': 'Факультет инженерии'},
                ...
            }

        Returns:
            Объект FilterCombination
        """
        session = self.get_session()
        try:
            combo = session.query(FilterCombination).filter(
                FilterCombination.level_value == filters_dict['level']['value'],
                FilterCombination.faculty_value == filters_dict['faculty']['value'],
                FilterCombination.inst_value == filters_dict['inst']['value'],
                FilterCombination.speciality_value == filters_dict['speciality']['value'],
                FilterCombination.typeofstudy_value == filters_dict['typeofstudy']['value'],
                FilterCombination.category_value == filters_dict['category']['value'],
            ).first()

            if combo:
                logger.debug(f"✅ Комбинация найдена: id={combo.id}")
                return combo

            combo = FilterCombination(
                level_value=int(filters_dict['level']['value']),
                level_name=filters_dict['level']['name'],
                faculty_value=int(filters_dict['faculty']['value']),
                faculty_name=filters_dict['faculty']['name'],
                inst_value=int(filters_dict['inst']['value']),
                inst_name=filters_dict['inst']['name'],
                speciality_value=int(filters_dict['speciality']['value']),
                speciality_name=filters_dict['speciality']['name'],
                typeofstudy_value=int(filters_dict['typeofstudy']['value']),
                typeofstudy_name=filters_dict['typeofstudy']['name'],
                category_value=int(filters_dict['category']['value']),
                category_name=filters_dict['category']['name'],
            )
            session.add(combo)
            session.commit()
            logger.debug(f"✅ Новая комбинация создана: id={combo.id}")
            return combo

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка при получении комбинации: {e}")
            raise
        finally:
            session.close()

    def get_all_filter_combinations(self) -> list[FilterCombination]:
        """Получить все комбинации фильтров"""
        session = self.get_session()
        try:
            combos = session.query(FilterCombination).all()
            logger.info(f"✅ Получено {len(combos)} комбинаций")
            return combos
        except Exception as e:
            logger.error(f"❌ Ошибка при получении комбинаций: {e}")
            return []
        finally:
            session.close()

    async def save_data_batch(
        self,
        records: list[dict],
        combo: FilterCombination
    ) -> int:
        """
        Сохранить данные

        Args:
            records: Список словарей с данными строк таблицы
            combo: Объект FilterCombination

        Returns:
            Количество сохраненных записей
        """
        session = self.get_session()
        try:
            session.query(Statistics).filter(
                Statistics.filter_combination_id == combo.id
            ).delete()

            count = 0
            for record in records:
                score = None
                if record.get('score'):
                    try:
                        score = int(record['score'])
                    except (ValueError, TypeError):
                        score = None
                row = Statistics(
                    filter_combination_id=combo.id,
                    admission_category=record.get('admission_category'),
                    available_places=record.get('available_places'),
                    epgu_id=record.get('epgu_id'),
                    applicant_id=record.get('applicant_id'),
                    score=score,
                    agreement=record.get('agreement'),
                    status=record.get('status'),
                    note=record.get('note'),
                )
                session.add(row)
                count += 1

            session.commit()
            logger.info(
                f"✅ Сохранено {count} записей для комбинации {combo.id}")
            return count

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка при сохранении: {e}")
            return 0
        finally:
            session.close()

    def get_data_by_filters(
        self,
        level: str | None = None,
        faculty: str | None = None,
        inst: str | None = None,
        speciality: str | None = None,
        typeofstudy: str | None = None,
        category: str | None = None,
        limit: int = 1000
    ) -> list[Statistics]:
        """
        Получить данные из БД по фильтрам

        Args:
            level, faculty, ... : value фильтров (или None для пропуска)
            limit: Максимум записей

        Returns:
            Список записей Statistics
        """
        session = self.get_session()
        try:
            combo_query = session.query(FilterCombination)

            if level:
                combo_query = combo_query.filter(
                    FilterCombination.level_value == level)
            if faculty:
                combo_query = combo_query.filter(
                    FilterCombination.faculty_value == faculty)
            if inst:
                combo_query = combo_query.filter(
                    FilterCombination.inst_value == inst)
            if speciality:
                combo_query = combo_query.filter(
                    FilterCombination.speciality_value == speciality)
            if typeofstudy:
                combo_query = combo_query.filter(
                    FilterCombination.typeofstudy_value == typeofstudy)
            if category:
                combo_query = combo_query.filter(
                    FilterCombination.category_value == category)

            combo = combo_query.first()
            if not combo:
                logger.warning("⚠️ Комбинация не найдена")
                return []

            results = session.query(Statistics).filter(
                Statistics.filter_combination_id == combo.id
            ).limit(limit).all()

            logger.info(f"✅ Найдено {len(results)} записей")
            return results

        except Exception as e:
            logger.error(f"❌ Ошибка при получении данных: {e}")
            return []
        finally:
            session.close()

    def get_levels(self) -> list[tuple[int, str]]:
        """
        Получить все уровни образования

        Returns:
            Список кортежей (value, name)
            Пример: [(1, 'бакалавриат'), (2, 'магистратура')]
        """
        session = self.get_session()
        try:
            results = session.query(
                FilterCombination.level_value,
                FilterCombination.level_name
            ).distinct().order_by(FilterCombination.level_value).all()

            levels = [(r.level_value, r.level_name) for r in results]
            logger.debug(f"✅ Получено {len(levels)} уровней")
            return levels
        except Exception as e:
            logger.error(f"❌ Ошибка при получении уровней: {e}")
            return []
        finally:
            session.close()

    def get_institutes(self) -> list[tuple[int, str]]:
        """
        Получить все филиалы и ВУЗ

        Returns:
            Список кортежей (value, name)
            Пример: [(0, 'КФУ'), (1, 'Набережночелнинский институт')]
        """
        session = self.get_session()
        try:
            results = session.query(
                FilterCombination.inst_value,
                FilterCombination.inst_name
            ).distinct().order_by(FilterCombination.inst_value).all()

            institutes = [(r.inst_value, r.inst_name) for r in results]
            logger.debug(
                f"✅ Получено {len(institutes)} филиалов ВУЗа")
            return institutes
        except Exception as e:
            logger.error(f"❌ Ошибка при получении филиалов ВУЗа: {e}")
            return []
        finally:
            session.close()

    def get_faculties(self, inst_value: str) -> list[tuple[int, str]]:
        """
        Получить все институты по ВУЗу

        Args:
            inst_value: value ВУЗа

        Returns:
            Список кортежей (value, name)
            Пример: [('6', 'Институт физики'), ('8', 'Юридический факультет')]
        """
        session = self.get_session()
        try:
            results = session.query(
                FilterCombination.faculty_value,
                FilterCombination.faculty_name
            ).filter(
                FilterCombination.inst_value == int(inst_value)
            ).distinct().order_by(FilterCombination.faculty_value).all()

            faculties = [(r.faculty_value, r.faculty_name) for r in results]
            logger.debug(f"✅ Получено {len(faculties)} факультетов")
            return faculties
        except Exception as e:
            logger.error(f"❌ Ошибка при получении факультетов: {e}")
            return []
        finally:
            session.close()

    def get_specialities(
        self,
        level_value: str,
        inst_value: str,
        faculty_value: str
    ) -> list[tuple[int, str]]:
        """
        Получить направления подготовки

        Args:
            level_value: value уровня
            inst_value: value ВУЗа
            faculty_value: value института

        Returns:
            Список кортежей (value, name)
            Пример: [(166, '01.03.02 Прикладная математика и информатика'), (203, '38.03.05 Бизнес-информатика')]
        """
        session = self.get_session()
        try:
            results = session.query(
                FilterCombination.speciality_value,
                FilterCombination.speciality_name
            ).filter(
                FilterCombination.level_value == int(level_value),
                FilterCombination.inst_value == int(inst_value),
                FilterCombination.faculty_value == int(faculty_value)
            ).distinct().order_by(FilterCombination.speciality_value).all()

            specialities = [(r.speciality_value, r.speciality_name)
                            for r in results]
            logger.debug(f"✅ Получено {len(specialities)} направлений")
            return specialities
        except Exception as e:
            logger.error(f"❌ Ошибка при получении направлений: {e}")
            return []
        finally:
            session.close()

    def get_study_types(
        self,
        level_value: str,
        inst_value: str,
        faculty_value: str,
        speciality_value: str
    ) -> list[tuple[int, str]]:
        """
        Получить типы обучения

        Args:
            level_value: value уровня
            inst_value: value ВУЗа
            faculty_value: value института
            speciality_value: value направления

        Returns:
            Список кортежей (value, name)
            Пример: [(1, 'Очная'), (2, 'Очно-заочная')]
        """
        session = self.get_session()
        try:
            results = session.query(
                FilterCombination.typeofstudy_value,
                FilterCombination.typeofstudy_name
            ).filter(
                FilterCombination.level_value == int(level_value),
                FilterCombination.inst_value == int(inst_value),
                FilterCombination.faculty_value == int(faculty_value),
                FilterCombination.speciality_value == int(speciality_value)
            ).distinct().order_by(FilterCombination.typeofstudy_value).all()

            study_types = [(r.typeofstudy_value, r.typeofstudy_name)
                           for r in results]
            logger.debug(f"✅ Получено {len(study_types)} типа обучения")
            return study_types
        except Exception as e:
            logger.error(f"❌ Ошибка при получении типов обучения: {e}")
            return []
        finally:
            session.close()

    def get_categories(self) -> list[tuple[int, str]]:
        """
        Получить категории конкурса

        Returns:
            Список кортежей (value, name)
            Пример: [(1, 'Бюджет'), (2, 'Внебюджет')]
        """
        session = self.get_session()
        try:
            results = session.query(
                FilterCombination.category_value,
                FilterCombination.category_name
            ).distinct().order_by(FilterCombination.category_value).all()

            categories = [(r.category_value, r.category_name) for r in results]
            logger.debug(f"✅ Получено {len(categories)} категории")
            return categories
        except Exception as e:
            logger.error(f"❌ Ошибка при получении категорий: {e}")
            return []
        finally:
            session.close()


def create_db_connection(config: Config) -> Database:
    """Создать подключение к БД из config"""
    db_url = f"postgresql://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{config.db.name}"
    db = Database(db_url)
    db.init_db()
    return db
