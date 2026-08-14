"""Validation of user-requested dataset type conversions."""

import pandas as pd


class TypeValidationService:
    """Validate conversions without changing the source DataFrame."""

    def __init__(self, data_provider) -> None:
        self._data_provider = data_provider

    @property
    def df(self):
        return getattr(self._data_provider, "df", None)

    def _get_column(self, attribute_name: str) -> pd.Series | None:
        if self.df is None or attribute_name not in self.df.columns:
            return None
        return self.df[attribute_name]

    @staticmethod
    def _can_convert_to_numeric(column: pd.Series) -> tuple[bool, str]:
        try:
            converted = pd.to_numeric(column.dropna(), errors='coerce')
            invalid_count = converted.isna().sum()
            if invalid_count == 0:
                return True, ''

            normalized = column.dropna().astype(str).str.replace(',', '.', regex=False)
            invalid_count = pd.to_numeric(normalized, errors='coerce').isna().sum()
            if invalid_count == 0:
                return True, ''
            return False, f'A coluna contém {invalid_count} valores não numéricos.'
        except Exception as error:
            return False, f'Erro ao validar conversão: {error}'

    @staticmethod
    def _can_convert_to_date(column: pd.Series) -> tuple[bool, str]:
        try:
            pd.to_datetime(column.dropna(), errors='raise')
            return True, ''
        except Exception:
            return False, 'Formato de data não reconhecido. Use: YYYY-MM-DD, DD/MM/YYYY, etc.'

    def validate(self, attribute_name: str, new_type: str) -> dict:
        """Return ``valid`` and ``message`` for a requested conversion."""
        column = self._get_column(attribute_name)
        if column is None:
            return {'valid': False, 'message': 'Coluna não encontrada'}
        if new_type in ('String', 'Nominal'):
            return {'valid': True, 'message': ''}

        validators = {
            'Numeric': self._can_convert_to_numeric,
            'Date': self._can_convert_to_date,
        }
        validator = validators.get(new_type)
        if validator is None:
            return {'valid': True, 'message': ''}
        is_valid, message = validator(column)
        return {'valid': is_valid, 'message': message}
