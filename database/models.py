from sqlalchemy import (
    Column, Integer, String, DateTime,
    Index, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class FilterCombination(Base):
    """
    Таблица с сочетаниями фильтров
    """
    __tablename__ = "filter_combinations"

    id = Column(Integer, primary_key=True)

    level_value = Column(Integer, nullable=False, index=True)
    level_name = Column(String(30), nullable=False, index=True)

    inst_value = Column(Integer, nullable=False, index=True)
    inst_name = Column(String(100), nullable=False, index=True)

    faculty_value = Column(Integer, nullable=False, index=True)
    faculty_name = Column(String(100), nullable=False, index=True)

    speciality_value = Column(Integer, nullable=False, index=True)
    speciality_name = Column(String(100), nullable=False, index=True)

    typeofstudy_value = Column(Integer, nullable=False, index=True)
    typeofstudy_name = Column(String(20), nullable=False, index=True)

    category_value = Column(Integer, nullable=False, index=True)
    category_name = Column(String(10), nullable=False, index=True)

    updated_at = Column(DateTime, default=datetime.utcnow,
                        nullable=False, index=True)

    statistics = relationship(
        "Statistics", back_populates="filter_combo", cascade="all, delete-orphan")

    def to_filters_dict(self) -> dict[str, str]:
        """Преобразовать в словарь value для URL"""
        return {
            'p_level': str(self.level_value),
            'p_inst': str(self.inst_value),
            'p_faculty': str(self.faculty_value),
            'p_speciality': str(self.speciality_value),
            'p_typeofstudy': str(self.typeofstudy_value),
            'p_category': str(self.category_value),
        }


Index(
    'idx_filter_combination_unique',
    FilterCombination.level_value,
    FilterCombination.faculty_value,
    FilterCombination.inst_value,
    FilterCombination.speciality_value,
    FilterCombination.typeofstudy_value,
    FilterCombination.category_value,
    unique=True
)


class Statistics(Base):
    """
    Таблица со всеми данными поступления КФУ
    - filter_combination_id: ссылка на FilterCombination
    - admission_category: Категория конкурса
    - available_places: Количество мест в рамках конкурса
    - epgu_id: Уникальный id абитуриента ЕПГУ
    - applicant_id: id абитуриента
    - score: Сумма конкурсных баллов
    - agreement: Заявление о согласии на зачисление
    - status: Статус
    - note: Примечание

    - created_at: Когда была загружена запись
    """
    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True)

    filter_combination_id = Column(
        Integer,
        ForeignKey('filter_combinations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    admission_category = Column(String(50), nullable=True, index=True)
    available_places = Column(Integer, nullable=True)
    epgu_id = Column(String(15), nullable=True, index=True)
    applicant_id = Column(String(15), nullable=True, index=True)
    score = Column(Integer, nullable=True)
    agreement = Column(String(10), nullable=True)
    status = Column(String(30), nullable=True)
    note = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow,
                        nullable=False, index=True)

    filter_combo = relationship(
        "FilterCombination", back_populates="statistics")
