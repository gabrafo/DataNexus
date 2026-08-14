"""CSV parsing and delimiter detection."""

import csv
import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CsvLoadResult:
    dataframe: pd.DataFrame
    has_header: bool
    delimiter: str | None


class CsvFileService:
    """Load CSV files without depending on Qt or controller signals."""

    @staticmethod
    def _detect_header(file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                sample = file.read(8192)
            has_header = csv.Sniffer().has_header(sample)
            logger.warning("[CSV] Header detection: %s", has_header)
            return has_header
        except Exception:
            return True

    @staticmethod
    def _detect_delimiter(file_path: str) -> str | None:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                sample = file.read(8192)
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|:")
            delimiter = getattr(dialect, 'delimiter', None)
            logger.warning("[CSV] Detected delimiter: %r", delimiter)
            return delimiter
        except Exception:
            return None

    @staticmethod
    def _normalize_delimiter(user_delimiter: str) -> str:
        normalized = user_delimiter.lower()
        if normalized == 'tab':
            return '\t'
        if normalized == 'espaço':
            return ' '
        return user_delimiter

    def load(self, file_path: str, user_delimiter: str = '') -> CsvLoadResult:
        has_header = self._detect_header(file_path)
        delimiter = (
            self._normalize_delimiter(user_delimiter)
            if user_delimiter
            else self._detect_delimiter(file_path)
        )

        read_kwargs = {'sep': delimiter} if delimiter else {
            'sep': None,
            'engine': 'python',
        }
        if has_header:
            dataframe = pd.read_csv(file_path, **read_kwargs)
        else:
            dataframe = pd.read_csv(file_path, header=None, **read_kwargs)
            dataframe.columns = [f"Coluna_{index}" for index in range(len(dataframe.columns))]

        return CsvLoadResult(dataframe, has_header, delimiter)
