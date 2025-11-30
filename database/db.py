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

            # Если не нашли — создаем новую
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
        # в рекорд сразу только нужные поля и в нужном порядке
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
                row = Statistics(
                    filter_combination_id=combo.id,
                    epgu_id=record.get('epgu_id'),
                    applicant_id=record.get('applicant_id'),
                    score=record.get('score'),
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

    # def get_filter_options(self, filter_name: str) -> list[str]:
    #     """
    #     Получить все уникальные значения для фильтра

    #     Args:
    #         filter_name: 'level', 'faculty', ...

    #     Returns:
    #         Список уникальных значений
    #     """
    #     session = self.get_session()
    #     try:
    #         column = getattr(Statistics, filter_name)
    #         results = session.query(column).distinct().all()
    #         return [r for r in results if r]
    #     except Exception as e:
    #         logger.error(f"❌ Ошибка при получении опций: {e}")
    #         return []
    #     finally:
    #         session.close()


def create_db_connection(config: Config) -> Database:
    """Создать подключение к БД из config"""
    db_url = f"postgresql://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{config.db.name}"
    db = Database(db_url)
    db.init_db()
    return db
