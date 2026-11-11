"""ARFF parsing independent from Qt controllers."""

import logging
import re
from typing import Any

import arff

logger = logging.getLogger(__name__)

# ``@attribute <name> date [format]``; the name may be quoted.
_DATE_ATTRIBUTE = re.compile(
    r"""^(\s*@attribute\s+(?:'[^']*'|"[^"]*"|\S+)\s+)date\b.*$""",
    re.IGNORECASE,
)


class ArffFileService:
    """Load ARFF structures and preserve their explicit metadata."""

    def load(self, file_path: str) -> dict[str, Any]:
        self._diagnose(file_path)
        with open(file_path, 'r', encoding='utf-8') as file:
            text, date_indexes = self._hide_date_attributes(file.read())
        try:
            dataset = arff.loads(text, encode_nominal=False, return_type=arff.DENSE)
        except Exception as error:
            logger.warning("[ARFF] Default parser error: %s", error)
            dataset = arff.loads(text, encode_nominal=False)

        attributes = list(dataset.get('attributes', []))
        for index in date_indexes:
            if index < len(attributes):
                attributes[index] = (attributes[index][0], 'DATE')
        dataset['attributes'] = attributes

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
    def _hide_date_attributes(text: str) -> tuple[str, list[int]]:
        """Declare DATE attributes as STRING, which liac-arff can parse.

        Returns the adjusted text and the positions of the date attributes.
        """
        lines = text.split('\n')
        date_indexes: list[int] = []
        attribute_index = -1
        for line_number, line in enumerate(lines):
            stripped = line.strip().lower()
            if stripped.startswith('@data'):
                break
            if not stripped.startswith('@attribute'):
                continue
            attribute_index += 1
            match = _DATE_ATTRIBUTE.match(line)
            if match:
                lines[line_number] = f'{match.group(1)}STRING'
                date_indexes.append(attribute_index)
        return '\n'.join(lines), date_indexes

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
