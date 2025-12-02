import logging
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session
from database.db import Database
from database.models import FilterCombination, Statistics

logger = logging.getLogger(__name__)

ALL_CATEGORIES = ['без вступительных испытаний',
                  'целевая квота', 'особая квота', 'отдельная квота']


class DataAnalyzer:
    """Анализатор данных поступления в КФУ"""

    def __init__(self, db: Database):
        self.db = db

    def _analyze_categoties(self, session: Session, filter_id, filter_note) -> tuple[dict[str, dict[str, int]], int]:
        category_stats = session.query(
            Statistics.admission_category,
            Statistics.available_places,
            func.count(Statistics.id).label('total_count'),
            func.count(
                case(
                    (and_(
                        Statistics.agreement == 'да',
                        filter_note
                    ), 1)
                )
            ).label('agreed_count')
        ).filter(
            filter_id
        ).group_by(
            Statistics.admission_category,
            Statistics.available_places
        ).all()

        admitted_by_category = {}
        occupied_places = 0
        for stat_row in category_stats:
            cat_name = stat_row.admission_category
            if not cat_name or cat_name == 'общий конкурс':
                continue
            agreed_count = stat_row.agreed_count or 0
            available_places = stat_row.available_places or 0
            if cat_name == 'без вступительных испытаний':
                available_places = agreed_count
            admitted_by_category[cat_name] = {
                'available_places': available_places,
                'agreed_count': agreed_count,
                'total': min(available_places, agreed_count)
            }
            occupied_places += admitted_by_category[cat_name]['total']
            logger.debug(
                f"✅ Категория '{cat_name}': согласились {agreed_count}, мест {available_places}, заняли {admitted_by_category[cat_name]['total']}")
        return admitted_by_category, occupied_places

    def analyze_speciality(self, filters: dict) -> dict:
        """Анализ конкретного направления"""
        session = self.db.get_session()
        try:
            combo = session.query(FilterCombination).filter(
                FilterCombination.level_value == filters['level'],
                FilterCombination.faculty_value == filters['faculty'],
                FilterCombination.inst_value == filters['inst'],
                FilterCombination.speciality_value == filters['speciality'],
                FilterCombination.typeofstudy_value == filters['typeofstudy'],
                FilterCombination.category_value == filters['category'],
            ).first()

            if not combo:
                logger.warning("⚠️ Комбинация не найдена")
                return {'error': '❌ Не существует такого сочетания параметров'}

            filter_id = Statistics.filter_combination_id == combo.id
            filter_note = or_(Statistics.note.is_(None),
                              ~Statistics.note.contains("не сданы один или несколько экзаменов"))

            total_apps = session.query(func.count(Statistics.id)).filter(
                filter_id
            ).scalar() or 0

            if not total_apps:
                logger.warning(f"⚠️ Нет статистики для комбинации {combo.id}")
                return {'error': '❌ Не существует данных для такого сочетания параметров'}

            total_participants = session.query(func.count(Statistics.id)).filter(
                filter_id, filter_note).scalar() or 0

            total_available_places = session.query(Statistics.available_places).filter(
                filter_id,
                Statistics.admission_category == 'общий конкурс',
            ).limit(1).scalar()
            if not total_available_places:
                logger.warning(
                    "Не найдены доступные места по этому направлению")
                return {'error': '❌ Не найдены доступные места по этому направлению'}

            admitted_by_category, occupied_places = self._analyze_categoties(
                session, filter_id, filter_note)

            remaining_places = total_available_places - occupied_places

            logger.debug(
                f"Всего мест: {total_available_places}, занято: {occupied_places}, осталось: {remaining_places}")

            general_participants = session.query(Statistics).filter(
                filter_id, filter_note,
                Statistics.admission_category == 'общий конкурс',
                Statistics.agreement == 'да',
            ).order_by(Statistics.score.desc()).limit(remaining_places).all()

            scores: list = [
                s.score for s in general_participants if s.score is not None]

            result = {
                'speciality_name': combo.speciality_name,
                'total_applications': total_apps,
                'total_participants': total_participants,
                'total_places': total_available_places,
                'places_general_competition': remaining_places,
                'applicants_per_place': round(total_participants / remaining_places, 2),

                'special_categories': admitted_by_category,

                'avg_score': round(sum(scores) / len(scores), 1) if scores else None,
                'min_score': min(scores) if scores else None,
                'max_score': max(scores) if scores else None,
            }

            logger.info(
                f"✅ Анализ направления {combo.speciality_name}: {total_apps} заявлений, средний балл {result['avg_score']}")
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка анализа направления: {e}")
            return {'error': "❌ Ошибка анализа направления"}
        finally:
            session.close()

    def get_count_unique_id(self, session: Session, filters: list) -> int:
        return session.query(func.count(Statistics.id.distinct())).filter(
            *filters).scalar() or 0

    def analyze_institute(self, filters: dict) -> dict:
        """Анализ популярности направлений в институте"""
        session = self.db.get_session()
        try:
            base_filter = [
                FilterCombination.level_value == filters.get('level'),
                FilterCombination.faculty_value == filters.get('faculty'),
                FilterCombination.inst_value == filters.get('inst'),
                FilterCombination.typeofstudy_value == filters.get(
                    'typeofstudy'),
                FilterCombination.category_value == filters.get('category'),
            ]
            combos = session.query(FilterCombination).filter(
                *base_filter,).all()

            if not combos:
                logger.warning(
                    f"⚠️ Нет такого сочетания параметров для института {filters['inst']}")
                return {
                    'error': '❌ Не существует данных для такого сочетания параметров'
                }

            faculty_name = combos[0].faculty_name
            combo_ids = [c.id for c in combos]

            filter_id = Statistics.filter_combination_id.in_(combo_ids)
            filter_applicant_id = or_(Statistics.epgu_id.isnot(None),
                                      Statistics.applicant_id.isnot(None))
            filter_note = or_(~Statistics.note.contains(
                "не сданы один или несколько экзаменов"),
                Statistics.note.is_(None))

            unique_applicant_count = self.get_count_unique_id(
                session, [filter_id, filter_applicant_id])

            unique_participants_count = self.get_count_unique_id(
                session, [filter_id, filter_note, filter_applicant_id])

            logger.debug(
                f"Уникальных заявлений: {unique_applicant_count}, уникальных конкурсантов: {unique_participants_count}")

            spec_category_all = session.query(
                FilterCombination.speciality_name,
                FilterCombination.speciality_value,
                Statistics.available_places,
                Statistics.admission_category,
                func.count(Statistics.id).label('total_apps'),
            ).join(
                Statistics, Statistics.filter_combination_id == FilterCombination.id
            ).filter(filter_id, filter_note,
                     ).group_by(
                FilterCombination.speciality_value,
                FilterCombination.speciality_name,
                Statistics.available_places,
                Statistics.admission_category,
            ).all()

            spec_category_admitted = session.query(
                FilterCombination.speciality_name,
                FilterCombination.speciality_value,
                Statistics.admission_category,
                func.count(Statistics.id).label('admitted_count'),
            ).join(
                Statistics, Statistics.filter_combination_id == FilterCombination.id
            ).filter(
                *base_filter,
                filter_note,
                Statistics.agreement == 'да',
            ).group_by(
                FilterCombination.speciality_value,
                FilterCombination.speciality_name,
                Statistics.admission_category,
            ).all()

            if not spec_category_all:
                logger.warning(f"⚠️ Нет статистики для специальностей")
                return {'error': '❌ Нет статистики для специальностей'}

            specialities_map = {}
            for row in spec_category_all:
                spec_key = row.speciality_name
                if spec_key not in specialities_map:
                    specialities_map[spec_key] = {
                        'name': spec_key,
                        'total_places': 0,
                        'categories': {},
                        'total_apps': 0,
                    }
                cat = row.admission_category or 'общий конкурс'
                total_apps = row.total_apps or 0
                specialities_map[spec_key]['total_apps'] += total_apps
                max_places_for_cat = row.available_places or 0
                specialities_map[spec_key]['categories'][cat] = {
                    'total_applications': total_apps,
                    'total_participants': 0,
                    'max_places': max_places_for_cat,
                    'admitted': 0,
                }

            for row in spec_category_admitted:
                spec_key = row.speciality_name
                cat = row.admission_category or 'общий конкурс'
                if spec_key in specialities_map and cat in specialities_map[spec_key]['categories']:
                    specialities_map[spec_key]['categories'][cat]['admitted'] = row.admitted_count or 0
                    if cat == 'без вступительных испытаний':
                        specialities_map[spec_key]['categories'][cat]['max_places'] = specialities_map[spec_key]['categories'][cat]['admitted']

            specialities_data = []
            for spec_key, spec_info in specialities_map.items():
                total_places = spec_info['categories'].get(
                    'общий конкурс', {}).get('max_places', 0) or 0
                specialities_map[spec_key]['total_places'] = total_places

                occupied_by_special = 0
                for cat, cat_info in spec_info['categories'].items():
                    if cat == 'общий конкурс':
                        continue
                    max_places = cat_info.get('max_places', 0)
                    admitted_in_cat = cat_info.get('admitted', 0)
                    occupied = min(admitted_in_cat, max_places)
                    occupied_by_special += occupied

                remaining_places = total_places - occupied_by_special
                total_apps = spec_info['total_apps']
                applicants_per_place = round(
                    total_apps / total_places, 2) if total_places > 0 else 0
                specialities_data.append({
                    'name': spec_info['name'],  # название специальности
                    'total_applications': total_apps,  # всего заявлений
                    'total_places': total_places,  # всего мест
                    # занято мест специальными категориями
                    'occupied_by_special_categories': occupied_by_special,
                    'remaining_places': remaining_places,  # осталось мест на общий конкурс
                    'applicants_per_place': applicants_per_place,  # заявлений на одно место
                })

            specialities_data.sort(
                key=lambda x: x['applicants_per_place'], reverse=True)
            for idx, spec in enumerate(specialities_data, 1):
                spec['popularity_rank'] = idx  # место по популярности
            result = {
                'institute_name': faculty_name,  # название института
                'total_unique_applicants': unique_applicant_count,  # всего уникальных заявителей
                # всего уникальных конкурсантов
                'total_unique_participants': unique_participants_count,
                # всего специальностей
                'total_specialities': len(specialities_data),
                'specialities': specialities_data,  # данные по каждой специальности
                # самая популярная специальность
                'most_popular': specialities_data[0]['name'] if specialities_data else None,
                # самая редкая специальность
                'least_popular': specialities_data[-1]['name'] if specialities_data else None,
            }
            logger.info(
                f"✅ Анализ института {faculty_name}: {unique_applicant_count} уникальных заявлений, "
                f"{len(specialities_data)} специальностей"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка анализа института: {e}")
            return {'error': '❌ Не удалось проанализировать институт'}
        finally:
            session.close()

    def analyze_university(self, filters: dict) -> dict:
        """Анализ всего университета"""
        session = self.db.get_session()
        try:
            combos = session.query(FilterCombination).filter(
                FilterCombination.level_value == filters.get('level'),
                FilterCombination.inst_value == filters.get('inst'),
                FilterCombination.category_value == filters.get('category'),
            ).all()

            if not combos:
                logger.warning(
                    f"⚠️ Нет такого сочетания параметров для университета {filters['inst']}")
                return {
                    'error': '❌ Не существует данных для такого сочетания параметров'
                }

            inst_name = combos[0].inst_name
            combo_ids = [c.id for c in combos]

            filter_id = Statistics.filter_combination_id.in_(combo_ids)
            filter_applicant_id = or_(Statistics.epgu_id.isnot(None),
                                      Statistics.applicant_id.isnot(None))
            filter_note = or_(~Statistics.note.contains(
                "не сданы один или несколько экзаменов"),
                Statistics.note.is_(None))

            unique_applicant_count = self.get_count_unique_id(
                session, [filter_id, filter_applicant_id])

            unique_participants_count = self.get_count_unique_id(
                session, [filter_id, filter_applicant_id, filter_note])

            logger.debug(
                f"Университет {inst_name}: {unique_applicant_count} заявок, {unique_participants_count} конкурсантов")

            faculties_all_stats = session.query(
                FilterCombination.faculty_value,
                FilterCombination.faculty_name,
                func.count(Statistics.id.distinct()).label('total_apps')
            ).join(
                Statistics, Statistics.filter_combination_id == FilterCombination.id
            ).filter(
                filter_id,
                filter_applicant_id,
            ).group_by(
                FilterCombination.faculty_value,
                FilterCombination.faculty_name,
            ).all()

            faculties_unique_stats = session.query(
                FilterCombination.faculty_value,
                FilterCombination.faculty_name,
                func.count(Statistics.id.distinct()).label(
                    'unique_participants'),

            ).join(
                Statistics, Statistics.filter_combination_id == FilterCombination.id
            ).filter(
                filter_id,
                filter_applicant_id,
                filter_note,
            ).group_by(
                FilterCombination.faculty_value,
                FilterCombination.faculty_name,
            ).all()

            if not faculties_all_stats:
                logger.warning(
                    f"⚠️ Нет статистики для институтов по университету {inst_name}")
                return {
                    'total_unique_applicants': unique_applicant_count,
                    'total_unique_participants': unique_participants_count,
                    'faculties': [],
                    'most_popular': None,
                    'least_popular': None,
                }

            faculties_data = {}
            for faculty in faculties_all_stats:
                faculties_data[faculty.faculty_name] = {
                    'unique_applications': faculty.total_apps or 0,
                    'unique_participants': 0
                }

            for faculty in faculties_unique_stats:
                if faculty.faculty_name in faculties_data:
                    faculties_data[faculty.faculty_name]['unique_participants'] = faculty.unique_participants or 0

            faculty_list = []
            for faculty_name, data in faculties_data.items():
                if data['unique_applications'] > 0:
                    faculty_list.append({
                        'name': faculty_name,
                        'unique_applications': data['unique_applications'],
                        'unique_participants': data['unique_participants'],
                    })

            faculty_list.sort(
                key=lambda x: x['unique_participants'], reverse=True)

            for idx, inst in enumerate(faculty_list, 1):
                inst['popularity_rank'] = idx

            result = {
                'total_unique_applicants': unique_applicant_count,
                'total_unique_participants': unique_participants_count,
                'total_institutes': len(faculty_list),
                'institutes': faculty_list,
                'most_popular': faculty_list[0]['name'] if faculty_list else None,
                'least_popular': faculty_list[-1]['name'] if faculty_list else None,
            }
            logger.info(
                f"✅ Анализ университета {inst_name}: {len(faculty_list)} институтов"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Ошибка анализа университета: {e}")
            return {'error': '❌ Не удалось проанализировать университет'}
        finally:
            session.close()
