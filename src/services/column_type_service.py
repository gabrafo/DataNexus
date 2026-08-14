"""Semantic type suggestions and column metadata helpers."""

import random

import pandas as pd


class ColumnTypeService:
    """Manage type overrides and column-level UI metadata for a controller."""

    def __init__(self, data_provider, overrides_attribute: str) -> None:
        self._data_provider = data_provider
        self._overrides_attribute = overrides_attribute

    @property
    def df(self):
        return getattr(self._data_provider, "df", None)

    @property
    def overrides(self) -> dict:
        overrides = getattr(self._data_provider, self._overrides_attribute, None)
        return overrides if isinstance(overrides, dict) else {}

    def suggested_type(self, attribute_name: str) -> str:
        if attribute_name in self.overrides:
            return self.overrides[attribute_name]

        attributes = getattr(self._data_provider, '_attributes', []) or []
        for name, attribute_type in attributes:
            if name != attribute_name:
                continue
            if isinstance(attribute_type, (list, tuple)):
                return 'Nominal'
            normalized = str(attribute_type).upper()
            if 'NUMERIC' in normalized or 'REAL' in normalized or 'INTEGER' in normalized:
                return 'Numeric'
            if 'DATE' in normalized:
                return 'Date'
            return 'String'

        if self.df is None or attribute_name not in self.df.columns:
            return 'String'
        column = self.df[attribute_name]
        if pd.api.types.is_numeric_dtype(column.dtype):
            return 'Numeric'
        if pd.api.types.is_datetime64_any_dtype(column.dtype):
            return 'Date'

        unique_count = column.nunique()
        total_count = len(column)
        if unique_count <= 10 and total_count and unique_count / total_count < 0.1:
            return 'Nominal'
        return 'String'

    def set_type(self, attribute_name: str, new_type: str) -> None:
        if attribute_name:
            self.overrides[attribute_name] = new_type

    def examples(self, attribute_name: str) -> list[str]:
        if self.df is None or attribute_name not in self.df.columns:
            return []
        values = [
            str(value)
            for value in self.df[attribute_name]
            if not pd.isna(value) and str(value).strip()
        ]
        if not values:
            return []

        rng = random.Random(hash(attribute_name))
        return [
            value if len(value) <= 30 else value[:27] + '...'
            for value in rng.sample(values, min(5, len(values)))
        ]

    def valid_types(self, attribute_name: str) -> list[str]:
        if self.df is None or attribute_name not in self.df.columns:
            return ['String']

        column = self.df[attribute_name]
        current_type = self.suggested_type(attribute_name)
        if current_type == 'Numeric':
            return ['Numeric', 'String', 'Nominal']
        if current_type == 'Date':
            return ['Date', 'String']
        if current_type == 'String':
            valid = ['String']
            unique_ratio = column.nunique() / len(column) if len(column) else 1
            if unique_ratio < 0.1:
                valid.append('Nominal')
            try:
                pd.to_datetime(column.dropna().head(5))
                valid.append('Date')
            except (ValueError, TypeError):
                pass
            return valid
        if current_type == 'Nominal':
            valid = ['Nominal', 'String']
            try:
                converted = pd.to_numeric(column.dropna(), errors='coerce')
                if not converted.isna().any():
                    valid.append('Numeric')
            except (ValueError, TypeError):
                pass
            return valid
        return ['String']
