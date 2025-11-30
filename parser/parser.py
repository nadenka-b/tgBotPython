import asyncio
import re
import aiohttp
import logging
import pandas as pd
from bs4 import BeautifulSoup, Tag
from typing import Optional

logger = logging.getLogger(__name__)

CATEGORIES = {
    'на основные места': 'общий конкурс',
    'целевой квоты': 'целевая квота',
    'особой квоты': 'особая квота',
    'отдельной квоты': 'отдельная квота',
    'без вступительных испытаний': 'без вступительных испытаний',
}

NEEDED_COLUMNS = {
    'Уникальный id абитуриента ЕПГУ': 'epgu_id',
    'id абитуриента': 'applicant_id',
    'Сумма конкурсных баллов': 'score',
    'Заявление о согласии на зачисление': 'agreement',
    'Статус': 'status',
    'Примечание': 'note',
}

CATEGORY_MAPPING = {
    'особой квоты': 'особая квота',
    'целевой квоты': 'целевая квота',
    'отдельная квота': 'отдельная квота'
}


class Parser:
    """Парсер для сайта КФУ"""

    def __init__(self, session: aiohttp.ClientSession, base_url: str):
        self.session: Optional[aiohttp.ClientSession] = session
        self.base_url = base_url

    async def fetch_page(self, params: dict[str, str]) -> str:
        """
        Загрузить страницу с заданными параметрами
        params: Словарь параметров для URL
        """
        try:
            if not self.session:
                logging.warning("Сессия не инициализирована")
                return ""
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(
                        f"Ошибка при загрузке: статус {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"Ошибка при запросе: {e}")
            return ""

    def extract_filter_options(self, html: str, filter_name: str) -> list[tuple]:
        """
        Извлечь доступные опции из селекта
        filter_name: 'level', 'faculty', 'inst', 'speciality', 'typeofstudy', 'category'
        Возвращает список (value, label)
        """
        soup = BeautifulSoup(html, 'lxml')

        select = soup.find('select', {'name': f"p_{filter_name}"})
        if not select:
            return []

        options = []
        for item in select.find_all("option"):
            value = item.get('value')
            text = item.get_text(strip=True)
            if not value or not text or "(для приема иностранных граждан)" in text:
                continue

            value = str(value).strip()

            if filter_name == 'speciality':
                text = text.split('(')[0].strip()

            options.append((value, text))

        return options

    def _extract_admission_category(self, table) -> str:
        """
        Извлечь категорию приема из заголовка перед таблицей
        Ищет текст типа: "... отдельной квоты" и берет именно "отдельной квоты"

        Returns:
            Строка с категорией (e.g., "отдельной квоты", "целевой квоты") или пустая строка
        """
        overflow_div = table.find_parent('div', {'class': 'overflow-table'})

        if not overflow_div:
            logger.warning("⚠️ Не найден div.overflow-table")
            return ""

        previous = overflow_div.find_previous(
            ['h1', 'h2', 'h3', 'h4', 'p', 'div'])

        if not previous:
            logger.warning("⚠️ Не найден заголовок перед таблицей")
            return ""

        text = previous.get_text(strip=True)
        logger.debug(f"🔍 Найден текст перед таблицей: {text}")

        for key, category_name in CATEGORIES.items():
            if key.lower() in text.lower():
                logger.debug(f"✅ Определена категория: {category_name}")
                return category_name

        return text[:50]

    def _extract_admission_plan(self, soup: BeautifulSoup) -> dict[str, int]:
        """
        Извлечь план приема по категориям

        Returns: {'общий конкурс': 71,
                'целевая квота': 8,...}
        """

        plan_div = soup.find('div', {'class': 'listing-abitur__plan'})

        if not plan_div:
            logger.warning("⚠️ Блок плана приема не найден")
            return {}

        plan_data = {}

        plan_strong = plan_div.find('p')
        if plan_strong:
            plan_text = plan_strong.get_text(strip=True)
            match = re.search(r'\d+', plan_text)
            if match:
                total_plan = int(match.group())
                plan_data['общий конкурс'] = total_plan
                logger.debug(f"📊 Общий план приема: {total_plan}")

        lis = plan_div.find_all('li')

        for li in lis:
            li_text = li.get_text(strip=True)
            logger.debug(f"🔍 Строка плана: {li_text}")

            for key, category_name in CATEGORY_MAPPING.items():
                if key.lower() in li_text.lower():
                    match = re.search(r'(\d+)(?:\s|$)', li_text)
                    if match:
                        seats = int(match.group(1))
                        plan_data[category_name] = seats
                        logger.debug(f"✅ {category_name}: {seats} мест")
                    break

        logger.info(f"📋 План приема по категориям: {plan_data}")
        return plan_data

    def _extract_headers(self, table: Tag, table_idx: int, admission_category: str) -> dict[str, int] | None:
        """
        Извлечь заголовки таблицы и найти их индексы в таблице

        Returns: {'Уникальный id абитуриента ЕПГУ': 1,
                'id абитуриента': 2,...}
        """
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find("tr")
            if header_row:
                header_cells = header_row.find_all(
                    class_="tablebig__th")
                for cell in header_cells:
                    text = cell.get_text(strip=True)
                    if text:
                        headers.append(text)

        if not headers:
            logger.warning(
                f"⚠️ Таблица {table_idx + 1} не имеет заголовков")
            return None

        logger.debug(f"Заголовки: {headers}")

        column_indices = {}
        headers = list(map(str.lower, headers))

        for header_name, column_name in NEEDED_COLUMNS.items():
            if header_name.lower() in headers:
                idx = headers.index(header_name.lower())
                column_indices[column_name] = idx
                logger.debug(
                    f"✅ Найден столбец '{column_name}' по индексу {idx}")
            elif admission_category == 'без вступительных испытаний' and header_name == 'Сумма конкурсных баллов':
                continue
            else:
                logger.warning(
                    f"⚠️ Не найден столбец '{column_name}' в таблице {table_idx + 1}")
                return None

        return column_indices

    def extract_table_data(self, html: str) -> pd.DataFrame | None:
        """
        Извлечь данные из таблиц
        Находит все таблицы с классом tablebig, извлекает нужные столбцы и объединяет их
        """
        soup = BeautifulSoup(html, 'lxml')

        admission_plans = self._extract_admission_plan(soup)
        logger.debug(f"📋 Извлеченный план: {admission_plans}")

        tables = soup.find_all('table', {'class': 'tablebig'})
        if not tables:
            logger.warning("⚠️ Таблицы не найдены")
            return None

        logger.debug(f"📊 Найдено таблиц: {len(tables)}")

        all_data = []

        for table_idx, table in enumerate(tables):
            logger.debug(f"📋 Обрабатываю таблицу {table_idx + 1}")
            try:
                admission_category = self._extract_admission_category(table)
                available_seats = admission_plans.get(admission_category, 0)
                logger.debug(f"📌 Категория приема: {admission_category}")

                column_indices = self._extract_headers(
                    table, table_idx, admission_category)

                if not column_indices:
                    continue

                rows = table.find_all('tr')[1:]
                for _, tr in enumerate(rows):
                    tds = tr.find_all('td')

                    if not tds:
                        continue

                    row_data = {}
                    for key, col_idx in column_indices.items():
                        if col_idx < len(tds):
                            cell_text = tds[col_idx].get_text(strip=True)
                            row_data[key] = cell_text if cell_text else None
                        else:
                            row_data[key] = None

                    row_data['admission_category'] = admission_category
                    row_data['available_seats'] = available_seats
                    all_data.append(row_data)

                logger.debug(
                    f"✅ Таблица {table_idx + 1}: извлечено {len(all_data)} строк")

            except Exception as e:
                logger.error(
                    f"❌ Ошибка при обработке таблицы {table_idx + 1}: {e}")
                continue

        if not all_data:
            logger.warning("⚠️ Данные не найдены")
            return None

        df = pd.DataFrame(all_data)
        logger.info(
            f"✅ Всего извлечено {len(df)} записей из {len(tables)} таблиц")

        return df

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
