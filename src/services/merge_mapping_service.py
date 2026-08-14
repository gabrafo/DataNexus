"""Column mapping and type compatibility for dataset merges."""

from typing import Callable, Dict, List

import pandas as pd

from models.dataset import Dataset


class MergeMappingService:
    """Manage merge-key mapping independently from merge execution.

    The service owns only mapping rules and type checks. It receives a
    translator from its facade so it does not depend on Qt or QML.
    """

    def __init__(
        self,
        primary: Dataset,
        secondary: Dataset,
        mapping: Dict[str, str],
        translator: Callable[[str], str] | None = None,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._mapping = mapping
        self._translate = translator or (lambda text: text)

    def _tr(self, text: str) -> str:
        return self._translate(text)

    @staticmethod
    def get_column_type(state: Dataset, column: str) -> str:
        """Return normalized type: NUMERIC, STRING, NOMINAL, DATE, or UNKNOWN."""
        if column in state.selected_types:
            selected = state.selected_types[column].upper()
            if 'NUMERIC' in selected:
                return 'NUMERIC'
            if 'STRING' in selected:
                return 'STRING'
            if 'NOMINAL' in selected:
                return 'NOMINAL'
            if 'DATE' in selected:
                return 'DATE'

        for name, attribute_type in state.arff_attributes:
            if name != column:
                continue
            if isinstance(attribute_type, str):
                normalized = attribute_type.upper()
                if any(kind in normalized for kind in ('NUMERIC', 'REAL', 'INTEGER')):
                    return 'NUMERIC'
                if 'STRING' in normalized:
                    return 'STRING'
                if 'DATE' in normalized:
                    return 'DATE'
            elif isinstance(attribute_type, (list, tuple)):
                return 'NOMINAL'
            return 'NOMINAL'

        if state.df is not None and column in state.df.columns:
            series = state.df[column]
            if pd.api.types.is_numeric_dtype(series.dtype):
                return 'NUMERIC'
            if pd.api.types.is_datetime64_any_dtype(series.dtype):
                return 'DATE'
            return 'STRING'

        return 'UNKNOWN'

    @staticmethod
    def normalize_label(type_label: str) -> str | None:
        """Normalize type labels to the canonical labels used by the app."""
        if not type_label:
            return None
        normalized = str(type_label).strip().lower()
        if 'num' in normalized:
            return 'Numeric'
        if 'nom' in normalized:
            return 'Nominal'
        if 'date' in normalized:
            return 'Date'
        return 'String'

    @staticmethod
    def are_types_compatible(type_a: str, type_b: str) -> bool:
        """Return whether two type codes can be used as a merge key."""
        if 'UNKNOWN' in (type_a, type_b) or type_a == type_b:
            return True
        return {type_a, type_b} <= {'STRING', 'NOMINAL'}

    @staticmethod
    def type_display_name(code: str) -> str:
        return {
            'NUMERIC': 'Numeric',
            'STRING': 'String',
            'NOMINAL': 'Nominal',
            'DATE': 'Date',
            'UNKNOWN': 'Unknown',
        }.get(code, code)

    def check_compatibility(self, secondary_col: str, primary_col: str) -> str:
        """Return an error if mapped columns have incompatible types."""
        if self._primary.df is None or self._secondary.df is None:
            return ""

        primary_type = self.get_column_type(self._primary, primary_col)
        secondary_type = self.get_column_type(self._secondary, secondary_col)
        if self.are_types_compatible(primary_type, secondary_type):
            return ""

        return self._tr(
            "Incompatible types: '{primary}' is {primary_type}, "
            "but '{secondary}' is {secondary_type}. Mapping not allowed."
        ).format(
            primary=primary_col,
            primary_type=self.type_display_name(primary_type),
            secondary=secondary_col,
            secondary_type=self.type_display_name(secondary_type),
        )

    def add_mapping(self, secondary_col: str, primary_col: str) -> tuple[bool, str]:
        """Replace the active mapping after validating both columns."""
        if not secondary_col or not primary_col:
            return False, self._tr("Empty column name")
        if self._primary.df is None or self._secondary.df is None:
            return False, self._tr("Databases not loaded")
        if secondary_col not in self._secondary.df.columns:
            return False, self._tr(
                "Column '{column}' does not exist in Dataset 2"
            ).format(column=secondary_col)
        if primary_col not in self._primary.df.columns:
            return False, self._tr(
                "Column '{column}' does not exist in Dataset 1"
            ).format(column=primary_col)

        error = self.check_compatibility(secondary_col, primary_col)
        if error:
            return False, error

        self._mapping.clear()
        self._mapping[secondary_col] = primary_col
        return True, ""

    def remove_mapping(self, secondary_col: str) -> None:
        self._mapping.pop(secondary_col, None)

    def clear_mappings(self) -> None:
        self._mapping.clear()

    def get_mappings(self) -> List[Dict[str, str]]:
        return [
            {"secondary": secondary, "primary": primary}
            for secondary, primary in self._mapping.items()
        ]

    def has_mappings(self) -> bool:
        return bool(self._mapping)

    def get_mappings_for_dropdown(self) -> List[str]:
        return [
            f"{primary} / {secondary}"
            for secondary, primary in self._mapping.items()
        ]

    @staticmethod
    def extract_primary_column(formatted: str) -> str:
        return formatted.split(" / ")[0] if " / " in formatted else formatted

    def get_common_columns(self) -> List[str]:
        if self._primary.df is None or self._secondary.df is None:
            return []

        primary_columns = set(self._primary.df.columns)
        secondary_columns = set(self._secondary.df.columns)
        common = primary_columns & secondary_columns
        for secondary, primary in self._mapping.items():
            if primary in primary_columns and secondary in secondary_columns:
                common.add(primary)
        return sorted(common)

    def get_mappable_secondary_columns(self) -> List[str]:
        if self._secondary.df is None:
            return []
        mapped = set(self._mapping.keys())
        return [column for column in self._secondary.df.columns if column not in mapped]

    def resolve_secondary_key(self, key_column: str) -> str:
        for secondary, primary in self._mapping.items():
            if primary == key_column:
                return secondary
        return key_column
