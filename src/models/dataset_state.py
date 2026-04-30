"""Dataset state container and type inference utilities."""

import gc
import logging
from typing import Optional, List, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class DatasetState:
    """In-memory representation of a loaded dataset with metadata."""

    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.arff_attributes: List[tuple] = []
        self.source_file: str = ""
        self.original_format: str = ""
        self.is_preprocessed: bool = False
        self.relation_name: str = ""
        self.selected_types: Dict[str, str] = {}

    def clear(self) -> None:
        """Release all data and reset to empty state."""
        if self.df is not None:
            del self.df
        self.df = None
        self.arff_attributes = []
        self.source_file = ""
        self.original_format = ""
        self.is_preprocessed = False
        self.relation_name = ""
        self.selected_types = {}
        gc.collect()

    def is_loaded(self) -> bool:
        """Return True if data is present and non-empty."""
        return self.df is not None and not self.df.empty

    def clone(self) -> 'DatasetState':
        """Create a deep copy of this state."""
        new = DatasetState()
        if self.df is not None:
            new.df = self.df.copy()
        new.arff_attributes = self.arff_attributes.copy()
        new.source_file = self.source_file
        new.original_format = self.original_format
        new.is_preprocessed = self.is_preprocessed
        new.relation_name = self.relation_name
        new.selected_types = self.selected_types.copy()
        return new


def infer_types_from_df(df: pd.DataFrame) -> tuple[Dict[str, str], List[tuple]]:
    """Infer semantic types and ARFF attributes from a DataFrame.

    Returns:
        Tuple of (selected_types dict, arff_attributes list).
    """
    inferred: Dict[str, str] = {}
    attrs: List[tuple] = []
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(dtype):
            inferred[col] = 'Numeric'
            attrs.append((col, 'NUMERIC'))
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            inferred[col] = 'Date'
            attrs.append((col, 'DATE'))
        else:
            nunique = df[col].nunique()
            total = len(df[col])
            if nunique <= 10 and total > 0 and nunique / total < 0.1:
                inferred[col] = 'Nominal'
                vals = list(df[col].dropna().astype(str).unique())
                attrs.append((col, vals if vals else ['_']))
            else:
                inferred[col] = 'String'
                attrs.append((col, 'STRING'))
    return inferred, attrs


def build_arff_attributes(state: DatasetState) -> List[tuple]:
    """Build ARFF attribute definitions from a DatasetState.

    Uses selected_types when available, falls back to dtype inference.
    If no DataFrame is present, returns stored arff_attributes.
    """
    if state.df is None:
        return state.arff_attributes.copy()

    attrs: List[tuple] = []
    for col in state.df.columns:
        sel = state.selected_types.get(col)
        if sel == 'Numeric':
            attrs.append((col, 'NUMERIC'))
        elif sel == 'Date':
            attrs.append((col, 'DATE'))
        elif sel == 'Nominal':
            uniques = list(state.df[col].dropna().astype(str).unique())
            attrs.append((col, uniques if uniques else ['_']))
        elif sel:
            attrs.append((col, 'STRING'))
        else:
            if state.df[col].dtype.kind in 'iufc':
                attrs.append((col, 'NUMERIC'))
            else:
                attrs.append((col, 'STRING'))
    return attrs
