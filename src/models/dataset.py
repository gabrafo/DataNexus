"""Dataset model and type inference utilities."""

import gc
import logging
import re
import warnings
from typing import Optional, List, Dict

import pandas as pd

logger = logging.getLogger(__name__)

# Text accepted as a date: YYYY-MM-DD or DD/MM/YYYY (separators - / .),
# optionally followed by a time and a UTC offset.
_DATE_TEXT = re.compile(
    r'^\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})'
    r'([ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?)?'
    r'\s*(Z|[+-]\d{2}:?\d{2})?\s*$'
)
_DATE_SAMPLE_SIZE = 1000


def parse_dates(values: pd.Series) -> Optional[pd.Series]:
    """Convert values to datetimes; return None if any value is not a date.

    Month-first parsing is tried before day-first, so DD/MM/YYYY columns
    are accepted when the default interpretation fails.
    """
    for dayfirst in (False, True):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                parsed = pd.to_datetime(values, errors='coerce', dayfirst=dayfirst)
        except Exception:
            continue
        if parsed.notna().all():
            return parsed
    return None


def looks_like_date(column: pd.Series) -> bool:
    """Return True when a text column holds only date-formatted values.

    Only the first non-null values are checked, to keep loading fast.
    """
    sample = column.dropna().head(_DATE_SAMPLE_SIZE)
    if sample.empty:
        return False
    is_date_text = sample.map(
        lambda value: isinstance(value, str) and bool(_DATE_TEXT.match(value))
    )
    return bool(is_date_text.all()) and parse_dates(sample) is not None


class Dataset:
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

    def clone(self) -> 'Dataset':
        """Create a deep copy of this state."""
        new = Dataset()
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
        elif looks_like_date(df[col]):
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


def build_arff_attributes(state: Dataset) -> List[tuple]:
    """Build ARFF attribute definitions from a Dataset.

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
