"""Merge operations for combining two datasets."""

import gc
import logging
from typing import Dict, List, Any

import pandas as pd

from models.dataset_state import DatasetState

logger = logging.getLogger(__name__)

_JOIN_MAP = {
    'inner': 'inner', 'left': 'left', 'right': 'right', 'outer': 'outer',
    'INNER JOIN': 'inner', 'LEFT JOIN': 'left',
    'RIGHT JOIN': 'right', 'FULL OUTER JOIN': 'outer',
}


class MergeService:
    """Handles merge logic between two DatasetState objects.

    Holds references to the primary/secondary states and column
    mapping dict managed by StateManager.
    """

    def __init__(self, primary: DatasetState, secondary: DatasetState,
                 column_mapping: Dict[str, str]):
        self._primary = primary
        self._secondary = secondary
        self._mapping = column_mapping

    # --- Type helpers ---

    @staticmethod
    def get_column_type(state: DatasetState, column: str) -> str:
        """Return normalized type: NUMERIC, STRING, NOMINAL, DATE, or UNKNOWN."""
        if column in state.selected_types:
            ut = state.selected_types[column].upper()
            if 'NUMERIC' in ut:
                return 'NUMERIC'
            if 'STRING' in ut:
                return 'STRING'
            if 'NOMINAL' in ut:
                return 'NOMINAL'
            if 'DATE' in ut:
                return 'DATE'

        for name, atype in state.arff_attributes:
            if name == column:
                if isinstance(atype, str):
                    u = atype.upper()
                    if any(k in u for k in ('NUMERIC', 'REAL', 'INTEGER')):
                        return 'NUMERIC'
                    if 'STRING' in u:
                        return 'STRING'
                    if 'DATE' in u:
                        return 'DATE'
                elif isinstance(atype, (list, tuple)):
                    return 'NOMINAL'
                return 'NOMINAL'

        if state.df is not None and column in state.df.columns:
            if pd.api.types.is_numeric_dtype(state.df[column].dtype):
                return 'NUMERIC'
            if pd.api.types.is_datetime64_any_dtype(state.df[column].dtype):
                return 'DATE'
            return 'STRING'

        return 'UNKNOWN'

    @staticmethod
    def are_types_compatible(t1: str, t2: str) -> bool:
        """Return True if two type codes are compatible for mapping."""
        if 'UNKNOWN' in (t1, t2) or t1 == t2:
            return True
        return {t1, t2} <= {'STRING', 'NOMINAL'}

    @staticmethod
    def type_display_name(code: str) -> str:
        """Return human-readable label for a type code."""
        return {
            'NUMERIC': 'Numeric', 'STRING': 'String',
            'NOMINAL': 'Nominal', 'DATE': 'Date',
            'UNKNOWN': 'Unknown',
        }.get(code, code)

    def check_mapping_compatibility(self, secondary_col: str, primary_col: str) -> str:
        """Return error message if types are incompatible, empty string otherwise."""
        if self._primary.df is None or self._secondary.df is None:
            return ""
        pt = self.get_column_type(self._primary, primary_col)
        st = self.get_column_type(self._secondary, secondary_col)
        if not self.are_types_compatible(pt, st):
            return (
                f"Incompatible types: '{primary_col}' is {self.type_display_name(pt)}, "
                f"but '{secondary_col}' is {self.type_display_name(st)}. "
                f"Mapping not allowed."
            )
        return ""

    # --- Mapping management ---

    def add_mapping(self, secondary_col: str, primary_col: str) -> tuple[bool, str]:
        """Add a column mapping. Returns (success, error_message)."""
        if not secondary_col or not primary_col:
            return False, "Empty column name"
        if self._primary.df is None or self._secondary.df is None:
            return False, "Bases not loaded"
        if secondary_col not in self._secondary.df.columns:
            return False, f"Coluna '{secondary_col}' não existe na Base 2"
        if primary_col not in self._primary.df.columns:
            return False, f"Coluna '{primary_col}' não existe na Base 1"
        err = self.check_mapping_compatibility(secondary_col, primary_col)
        if err:
            return False, err
        self._mapping[secondary_col] = primary_col
        return True, ""

    def remove_mapping(self, secondary_col: str) -> None:
        """Remove a column mapping by secondary column name."""
        self._mapping.pop(secondary_col, None)

    def clear_mappings(self) -> None:
        """Remove all column mappings."""
        self._mapping.clear()

    def get_mappings(self) -> List[Dict[str, str]]:
        """Return current mappings as a list of dicts."""
        return [{"secondary": s, "primary": p} for s, p in self._mapping.items()]

    def has_mappings(self) -> bool:
        """Return True if any column mappings exist."""
        return bool(self._mapping)

    def get_mappings_for_dropdown(self) -> List[str]:
        """Return mappings formatted as 'Primary / Secondary' strings."""
        return [f"{p} / {s}" for s, p in self._mapping.items()]

    @staticmethod
    def extract_primary_column(formatted: str) -> str:
        """Extract primary column name from 'ColPri / ColSec' format."""
        return formatted.split(" / ")[0] if " / " in formatted else formatted

    # --- Column queries ---

    def get_common_columns(self) -> List[str]:
        """Return columns usable as merge key, including mapped ones."""
        if self._primary.df is None or self._secondary.df is None:
            return []
        pri = set(self._primary.df.columns)
        sec = set(self._secondary.df.columns)
        common = pri & sec
        for sc, pc in self._mapping.items():
            if pc in pri and sc in sec:
                common.add(pc)
        return sorted(common)

    def get_mappable_secondary_columns(self) -> List[str]:
        """Return secondary columns not yet mapped."""
        if self._secondary.df is None:
            return []
        mapped = set(self._mapping.keys())
        return [c for c in self._secondary.df.columns if c not in mapped]

    # --- Internal ---

    def _resolve_secondary_key(self, key_column: str) -> str:
        """Find the secondary column corresponding to a primary key column."""
        for sc, pc in self._mapping.items():
            if pc == key_column:
                return sc
        return key_column

    # --- Merge operations ---

    def check_compatibility(self, key_column: str, join_type: str) -> Dict[str, Any]:
        """Check merge compatibility without creating the full result."""
        if not self._primary.is_loaded() or not self._secondary.is_loaded():
            return {'valid': False, 'error': 'Bases não carregadas'}

        sec_key = self._resolve_secondary_key(key_column)
        if key_column not in self._primary.df.columns:
            return {'valid': False, 'error': f'Coluna "{key_column}" não existe na Base 1'}
        if sec_key not in self._secondary.df.columns:
            return {'valid': False, 'error': f'Coluna "{sec_key}" não existe na Base 2'}

        try:
            pk = self._primary.df[key_column]
            sk = self._secondary.df[sec_key]
            sample_n = min(10000, len(pk), len(sk))
            pri_set = set(pk.dropna().head(sample_n).unique())
            sec_set = set(sk.dropna().head(sample_n).unique())
            common_n = len(pri_set & sec_set)

            how = _JOIN_MAP.get(join_type, 'inner')
            if how == 'inner':
                est = common_n * (len(self._primary.df) / max(1, sample_n))
            elif how == 'left':
                est = len(self._primary.df)
            elif how == 'right':
                est = len(self._secondary.df)
            else:
                est = len(self._primary.df) + len(self._secondary.df) - common_n

            return {
                'valid': True,
                'primaryKeyColumn': key_column,
                'secondaryKeyColumn': sec_key,
                'primaryUniqueKeys': int(pk.nunique()),
                'secondaryUniqueKeys': int(sk.nunique()),
                'estimatedRows': int(est),
                'commonKeysFound': common_n > 0,
            }
        except Exception as e:
            logger.warning("Compatibility check failed: %s", e)
            return {'valid': False, 'error': str(e)}

    def preview(self, key_column: str, join_type: str) -> Dict[str, Any]:
        """Generate a merge preview using small data samples."""
        if not self._primary.is_loaded() or not self._secondary.is_loaded():
            return {'error': 'Bases não carregadas'}

        is_cross = join_type in ('cross', 'CROSS JOIN') or not key_column

        try:
            n = 10 if is_cross else 100
            ps = self._primary.df.head(n).copy()
            ss = self._secondary.df.head(n).copy()

            if is_cross:
                ps['_mk'] = 1
                ss['_mk'] = 1
                merged = pd.merge(
                    ps, ss, on='_mk', how='outer',
                    suffixes=('_base1', '_base2'),
                ).drop('_mk', axis=1)
            else:
                sec_key = self._resolve_secondary_key(key_column)
                if key_column not in self._primary.df.columns:
                    return {'error': f'Coluna "{key_column}" não existe na Base 1'}
                if sec_key not in self._secondary.df.columns:
                    return {'error': f'Coluna "{sec_key}" não existe na Base 2'}

                how = _JOIN_MAP.get(join_type, 'inner')
                if sec_key != key_column:
                    ss = ss.rename(columns={sec_key: key_column})
                merged = pd.merge(
                    ps, ss, on=key_column, how=how,
                    suffixes=('_base1', '_base2'),
                )

            prev = merged.head(10)
            cols = list(prev.columns)
            data = [
                ["" if pd.isna(v) else str(v) for v in row]
                for row in prev.values.tolist()
            ]

            compat = self.check_compatibility(key_column, join_type)
            total_est = compat.get('estimatedRows', len(merged))

            del ps, ss, merged
            gc.collect()

            return {
                'columns': cols, 'data': data,
                'totalRows': total_est, 'previewRows': len(prev),
                'isEstimate': True,
            }
        except Exception as e:
            gc.collect()
            logger.warning("Preview failed: %s", e)
            return {'error': str(e)}

    def execute(self, key_column: str, join_type: str) -> tuple[bool, str]:
        """Execute the merge, updating primary state with result.

        Returns:
            Tuple of (success, message_or_error).
        """
        if not self._primary.is_loaded() or not self._secondary.is_loaded():
            return False, "Bases não carregadas para merge"

        try:
            is_cross = join_type in ('cross', 'CROSS JOIN') or not key_column

            if is_cross:
                self._primary.df['_mk'] = 1
                sec = self._secondary.df.copy()
                sec['_mk'] = 1
                merged = pd.merge(
                    self._primary.df, sec, on='_mk', how='outer',
                    suffixes=('_base1', '_base2'),
                ).drop('_mk', axis=1)
                self._primary.df = self._primary.df.drop('_mk', axis=1)
                attrs = self._combine_arff_attributes("", "")
            else:
                sec_key = self._resolve_secondary_key(key_column)
                how = _JOIN_MAP.get(join_type, 'inner')
                sec = self._secondary.df
                if sec_key != key_column:
                    sec = sec.rename(columns={sec_key: key_column})
                merged = pd.merge(
                    self._primary.df, sec, on=key_column, how=how,
                    suffixes=('_base1', '_base2'),
                )
                attrs = self._combine_arff_attributes(key_column, sec_key)

            combined_types = {**self._primary.selected_types}
            for col, typ in self._secondary.selected_types.items():
                actual = col if is_cross else (
                    key_column if col == self._resolve_secondary_key(key_column) else col
                )
                combined_types.setdefault(actual, typ)

            old_pri, old_sec = self._primary.df, self._secondary.df

            self._primary.df = merged
            self._primary.arff_attributes = attrs
            self._primary.source_file = (
                f"merge_{self._primary.source_file}_{self._secondary.source_file}"
            )
            self._primary.relation_name = "merged_dataset"
            self._primary.is_preprocessed = True
            self._primary.selected_types = combined_types

            self._secondary.df = None
            self._secondary.clear()
            self._mapping.clear()

            del old_pri, old_sec
            gc.collect()

            return True, (
                f"Junção concluída! {len(merged)} instâncias, "
                f"{len(merged.columns)} atributos"
            )
        except Exception as e:
            gc.collect()
            logger.error("Merge failed: %s", e)
            return False, f"Erro ao mesclar: {e}"

    def _combine_arff_attributes(self, pri_key: str, sec_key: str) -> List[tuple]:
        """Combine ARFF attributes from both bases, resolving name conflicts."""
        combined: List[tuple] = []
        seen: set[str] = set()
        for name, atype in self._primary.arff_attributes:
            combined.append((name, atype))
            seen.add(name)
        for name, atype in self._secondary.arff_attributes:
            if name in (sec_key, pri_key):
                continue
            out_name = f"{name}_base2" if name in seen else name
            combined.append((out_name, atype))
            seen.add(name)
        return combined
