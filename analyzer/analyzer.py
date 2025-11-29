import pandas as pd
from typing import Dict, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Анализатор данных поступления в КФУ"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.analysis_results = {}

    def analyze_all(self) -> Dict:
        """Выполнить полный анализ данных"""
        results = {
            'total_rows': len(self.df),
            'columns': list(self.df.columns),
            'most_demanded': self.get_most_demanded_specialties(),
            'statistics': self.get_statistics(),
            'summary': self.get_summary()
        }
        self.analysis_results = results
        return results

    def get_most_demanded_specialties(self, top_n: int = 10) -> List[Dict]:
        """
        Получить самые востребованные направления
        (по количеству заявлений)
        """
        # Предполагаем, что есть колонка с названием направления и количеством заявлений
        # Названия колонок могут варьироваться в зависимости от сайта

        specialty_col = None
        application_col = None

        # Поиск релевантных колонок
        for col in self.df.columns:
            col_lower = col.lower()
            if 'направ' in col_lower or 'специал' in col_lower:
                specialty_col = col
            if 'заявл' in col_lower or 'application' in col_lower:
                application_col = col

        if not specialty_col or not application_col:
            logger.warning("Не найдены нужные колонки для анализа")
            return []

        # Сортировка по количеству заявлений
        sorted_df = self.df.sort_values(
            by=application_col, ascending=False).head(top_n)

        results = []
        for idx, row in sorted_df.iterrows():
            results.append({
                'specialty': str(row[specialty_col]),
                'applications': str(row[application_col])
            })

        return results

    def get_statistics(self) -> Dict:
        """Получить общую статистику"""
        stats = {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'memory_usage': f"{self.df.memory_usage(deep=True).sum() / 1024:.2f} KB"
        }

        # Попытка вычислить числовые метрики для числовых колонок
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            try:
                stats[f"{col}_mean"] = float(self.df[col].mean())
                stats[f"{col}_max"] = float(self.df[col].max())
                stats[f"{col}_min"] = float(self.df[col].min())
            except Exception as e:
                logger.error(f"Ошибка при анализе колонки {col}: {e}")

        return stats

    def get_summary(self) -> str:
        """Получить текстовое резюме анализа"""
        summary = f"""
📊 АНАЛИЗ ДАННЫХ ПОСТУПЛЕНИЯ В КФУ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Всего записей: {len(self.df)}
📋 Всего колонок: {len(self.df.columns)}
🕐 Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

Первые несколько строк:
{self.df.head(3).to_string()}
        """.strip()

        return summary

    def to_excel(self, filename: str = "kfu_analysis.xlsx") -> bool:
        """
        Сохранить данные и анализ в Excel
        Возвращает True если успешно
        """
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Основные данные
                self.df.to_excel(writer, sheet_name='Данные', index=False)

                # Анализ
                if self.analysis_results:
                    summary_df = pd.DataFrame({
                        'Метрика': list(self.analysis_results.get('statistics', {}).keys()),
                        'Значение': list(self.analysis_results.get('statistics', {}).values())
                    })
                    summary_df.to_excel(
                        writer, sheet_name='Статистика', index=False)

                    # Самые востребованные
                    if self.analysis_results.get('most_demanded'):
                        demanded_df = pd.DataFrame(
                            self.analysis_results['most_demanded'])
                        demanded_df.to_excel(
                            writer, sheet_name='ТОП Направления', index=False)

            logger.info(f"✅ Файл сохранен: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении: {e}")
            return False


def create_analysis_report(df: pd.DataFrame) -> Tuple[Dict, str]:
    """
    Создать отчет анализа
    Возвращает (результаты анализа, текстовый отчет)
    """
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze_all()
    summary = analyzer.get_summary()

    return results, summary
