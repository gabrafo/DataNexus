"""ARFF serialization for controller-owned data."""

from typing import Any, Iterable

import arff
import pandas as pd


class ArffWriterService:
    """Build and write ARFF documents from DataFrames or row data."""

    @staticmethod
    def write(
        output_path: str,
        relation: str,
        attributes: list[tuple],
        data: list[list[Any]],
    ) -> None:
        with open(output_path, 'w', encoding='utf-8') as file:
            arff.dump({
                'relation': relation,
                'attributes': attributes,
                'data': data,
            }, file)

    def write_dataframe(
        self,
        output_path: str,
        dataframe: pd.DataFrame,
        selected_types: dict[str, str],
        relation: str,
        use_selected_types: bool = True,
        normalize_numeric: bool = False,
    ) -> None:
        attributes = []
        for column in dataframe.columns:
            selected = selected_types.get(column) if use_selected_types else None
            selected = selected or self._infer_dataframe_type(dataframe[column])
            attributes.append((column, self._attribute_type(selected, dataframe[column])))

        data = []
        for row in dataframe.itertuples(index=False, name=None):
            values = []
            for column, value in zip(dataframe.columns, row):
                values.append(self._normalize_value(value, selected_types.get(column), normalize_numeric))
            data.append(values)
        self.write(output_path, relation, attributes, data)

    def write_rows(
        self,
        output_path: str,
        relation: str,
        source_attributes: list[tuple],
        rows: Iterable[Iterable[Any]],
        selected_types: dict[str, str],
        normalize_numeric: bool = False,
    ) -> None:
        materialized_rows = [list(row) for row in rows]
        attributes = []
        for index, (name, original_type) in enumerate(source_attributes):
            selected = selected_types.get(name, 'String')
            if selected == 'Nominal':
                values = [row[index] for row in materialized_rows if index < len(row)]
                attribute_type = self._nominal_values(values)
            else:
                attribute_type = self._attribute_type(selected, original_type)
            attributes.append((name, attribute_type))

        data = []
        for row in materialized_rows:
            data.append([
                self._normalize_value(
                    value,
                    selected_types.get(source_attributes[index][0], 'String')
                    if index < len(source_attributes) else 'String',
                    normalize_numeric,
                )
                for index, value in enumerate(row)
            ])
        self.write(output_path, relation, attributes, data)

    @staticmethod
    def _infer_dataframe_type(column: pd.Series) -> str:
        return 'NUMERIC' if pd.api.types.is_numeric_dtype(column) else 'STRING'

    def _attribute_type(self, selected: str, column_or_original: Any) -> Any:
        normalized = str(selected).upper()
        if normalized in {'NUMERIC', 'REAL', 'INTEGER'} or selected == 'Numeric':
            return 'NUMERIC'
        if selected == 'Date' or 'DATE' in normalized:
            return 'DATE'
        if selected == 'Nominal':
            values = column_or_original if isinstance(column_or_original, Iterable) else []
            return self._nominal_values(values)
        return 'STRING'

    @staticmethod
    def _nominal_values(values: Iterable[Any]) -> list[str] | str:
        unique = list(dict.fromkeys(str(value) for value in values if value is not None))[:50]
        return unique if unique else 'STRING'

    @staticmethod
    def _normalize_value(value: Any, selected: str | None, normalize_numeric: bool) -> Any:
        if pd.isna(value):
            return None
        if normalize_numeric and selected == 'Numeric':
            if isinstance(value, str):
                value = value.replace(',', '.')
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return value
