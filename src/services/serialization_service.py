"""File I/O for saving datasets to CSV and ARFF."""

import logging
from typing import List

import pandas as pd
import arff

from models.dataset import Dataset, build_arff_attributes

logger = logging.getLogger(__name__)


class SerializationService:
    """Save Dataset objects to disk in CSV or ARFF format."""

    @staticmethod
    def save(target: Dataset, file_path: str) -> tuple[bool, str]:
        """Save a dataset to file. Format is detected from extension.

        Returns:
            Tuple of (success, error_message).
        """
        if not target.is_loaded():
            return False, "No data to save"
        try:
            if file_path.startswith("file://"):
                file_path = file_path[7:]
            if file_path.lower().endswith('.csv'):
                return SerializationService._save_csv(target, file_path)
            return SerializationService._save_arff(target, file_path)
        except Exception as e:
            logger.error("Save failed: %s", e)
            return False, f"Erro ao salvar: {e}"

    @staticmethod
    def _save_arff(target: Dataset, file_path: str) -> tuple[bool, str]:
        """Save dataset as ARFF file."""
        attributes = build_arff_attributes(target)
        data = target.df.where(target.df.notnull(), None).values.tolist()
        dataset = {
            'relation': target.relation_name or 'dataset',
            'attributes': attributes,
            'data': data,
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            arff.dump(dataset, f)
        return True, ""

    @staticmethod
    def _save_csv(target: Dataset, file_path: str) -> tuple[bool, str]:
        """Save dataset as CSV file."""
        target.df.to_csv(file_path, index=False)
        return True, ""
