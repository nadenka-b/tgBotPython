import aiohttp
import logging
import pandas as pd
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


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
        Возвращает список (value, label) для кнопок
        """
        soup = BeautifulSoup(html, 'html.parser')

        select = soup.find('select', {'name': f"p_{filter_name}"})
        if not select:
            return []

        options = []
        for item in select.find_all("option"):
            value = item.get('value')
            if not value:
                continue
            value = str(value).strip()
            text = item.get_text(strip=True)

            if value and text and not "(для приема иностранных граждан)" in text:
                options.append((value, text))

        return options

    def extract_table_data(self, html: str) -> pd.DataFrame:
        """
        Парсинг таблицы со статистикой поступления
        Возвращает DataFrame с данными
        """
        soup = BeautifulSoup(html, 'html.parser')

        table = soup.find('table', {'class': 'tablebig'})
        if not table:
            logger.warning("Таблица не найдена на странице")
            return pd.DataFrame()

        rows = []
        headers = []

        thead = table.find('thead')
        if thead:
            header_row = thead.find("tr")
            if header_row:
                header_cells = header_row.find_all(class_="tablebig__th")
                for cell in header_cells:
                    text = cell.get_text(strip=True)
                    if text:
                        headers.append(text)

        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                cols = []
                for td in tr.find_all('td'):
                    cols.append(td.get_text(strip=True))
                if cols:
                    rows.append(cols)

        if headers and rows:
            df = pd.DataFrame(rows, columns=headers)
            df = df.rename(columns=column_mapping)
            needed_columns = ['epgu_id', 'applicant_id' 'score',
                              'agreement', 'status', 'note']
            df = df[[col for col in needed_columns if col in df.columns]]
        else:
            df = pd.DataFrame()

        return df

    async def get_filter_chain(self, filter_type: str, current_params: dict[str, str]) -> list[tuple]:
        """
        Получить опции следующего фильтра на основе текущих параметров
        """
        html = await self.fetch_page(current_params)
        return self.extract_filter_options(html, filter_type)

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()


column_mapping = {
    'Уникальный id абитуриента ЕПГУ': 'epgu_id',
    'id абитуриента': 'applicant_id',
    'Сумма конкурсных баллов': 'score',
    'Заявление о согласии на зачисление': 'agreement',
    'Статус': 'status',
    'Примечание': 'note',
}
