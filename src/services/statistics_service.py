"""Descriptive statistics for dataset columns."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class StatisticsService:
    """Compute descriptive statistics without exposing a Qt API."""

    def __init__(self, data_provider) -> None:
        self._data_provider = data_provider

    @property
    def df(self):
        return getattr(self._data_provider, "df", None)

    def _get_column(self, attribute_name: str) -> pd.Series | None:
        if self.df is None or attribute_name not in self.df.columns:
            return None
        return self.df[attribute_name]

    def get_column_statistics(self, attribute_name: str) -> dict:
        column = self._get_column(attribute_name)
        if column is None:
            return {}

        stats = {}
        try:
            stats['count'] = int(column.count())
            stats['nullCount'] = int(column.isna().sum())
            selected_type = self._data_provider.getSuggestedType(attribute_name)

            if selected_type == 'Numeric':
                try:
                    normalized = column.dropna().astype(str).str.replace(',', '.', regex=False)
                    numeric = pd.to_numeric(normalized, errors='coerce')
                    stats['min'] = float(numeric.min()) if not numeric.empty else 0.0
                    stats['max'] = float(numeric.max()) if not numeric.empty else 0.0
                    stats['mean'] = float(numeric.mean()) if not numeric.empty else 0.0
                    stats['median'] = float(numeric.median()) if not numeric.empty else 0.0
                    stats['std'] = float(numeric.std()) if not numeric.empty else 0.0
                except Exception:
                    mode = column.mode()
                    stats['mode'] = str(mode.iloc[0]) if not mode.empty else ""
                    stats['uniqueCount'] = int(column.nunique())
            elif pd.api.types.is_numeric_dtype(column):
                stats['min'] = float(column.min()) if not column.empty else 0.0
                stats['max'] = float(column.max()) if not column.empty else 0.0
                stats['mean'] = float(column.mean()) if not column.empty else 0.0
                stats['median'] = float(column.median()) if not column.empty else 0.0
                stats['std'] = float(column.std()) if not column.empty else 0.0
            else:
                mode = column.mode()
                stats['mode'] = str(mode.iloc[0]) if not mode.empty else ""
                stats['uniqueCount'] = int(column.nunique())
        except Exception as error:
            logger.warning("Error computing statistics for %s: %s", attribute_name, error)
        return stats
