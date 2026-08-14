"""ARFF parsing independent from Qt controllers."""

import logging
from typing import Any

import arff

logger = logging.getLogger(__name__)


class ArffFileService:
    """Load ARFF structures and preserve their explicit metadata."""

    def load(self, file_path: str) -> dict[str, Any]:
        self._diagnose(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                dataset = arff.load(file, encode_nominal=False, return_type=arff.DENSE)
        except Exception as error:
            logger.warning("[ARFF] Default parser error: %s", error)
            with open(file_path, 'r', encoding='utf-8') as file:
                dataset = arff.load(file, encode_nominal=False)

        data = []
        for line_number, row in enumerate(dataset.get('data', []), start=1):
            try:
                data.append(list(row) if hasattr(row, '__iter__') and not isinstance(row, str) else [row])
            except Exception as error:
                logger.warning("[ARFF] Row %s error: %s", line_number, error)
                data.append([None] * len(dataset.get('attributes', [])))

        return {
            'relation': dataset.get('relation', ''),
            'attributes': dataset.get('attributes', []),
            'data': data,
        }

    @staticmethod
    def _diagnose(file_path: str) -> None:
        """Log a small diagnostic sample when an ARFF is malformed."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            data_line = next(
                (index for index, line in enumerate(lines) if line.strip().upper().startswith('@DATA')),
                None,
            )
            if data_line is not None:
                logger.warning("[ARFF DIAG] @DATA found at line %s", data_line + 1)
                for index, line in enumerate(lines[data_line + 1:data_line + 6], start=data_line + 2):
                    logger.warning("[ARFF DIAG] Line %s: %s", index, line.strip())
        except Exception as error:
            logger.warning("[ARFF DIAG] Error: %s", error)
