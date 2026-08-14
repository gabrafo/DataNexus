"""Synchronization between file controllers and application dataset state."""

import logging
from typing import Dict

from models.dataset import Dataset, build_arff_attributes, infer_types_from_df

logger = logging.getLogger(__name__)


class DatasetSyncService:
    """Move dataset data and metadata across controller boundaries.

    File controllers remain responsible for parsing files. This service is
    responsible for translating their in-memory representation into the
    application-level ``Dataset`` state and updating a controller after a
    merge.
    """

    def sync_from_controller(
        self,
        target: Dataset,
        controller,
        source_file: str,
        file_format: str,
        clear_mapping: bool,
        mapping: Dict[str, str],
    ) -> str | None:
        """Copy a loaded controller into a dataset and return an error, if any."""
        try:
            dataframe = controller.df
            if dataframe is None:
                return None

            target.df = dataframe.copy()
            target.source_file = source_file
            target.original_format = file_format

            if file_format == "csv":
                types, attributes = infer_types_from_df(dataframe)
                target.arff_attributes = attributes
                target.selected_types = types
                target.relation_name = source_file.replace(".csv", "")
            else:
                target.arff_attributes = getattr(controller, '_attributes', []) or []
                target.selected_types = getattr(controller, '_suggested_types', {}) or {}
                target.relation_name = getattr(controller, '_relation_name', "") or ""

            target.is_preprocessed = True
            if clear_mapping:
                mapping.clear()
            return None
        except Exception as error:
            logger.warning("Sync from controller failed: %s", error)
            return str(error)

    def push_to_controller(self, state: Dataset, controller) -> str | None:
        """Copy a dataset state into a controller and refresh its UI model."""
        if controller is None:
            return None

        try:
            controller._attributes = build_arff_attributes(state)
            controller._suggested_types = state.selected_types.copy()
            controller._relation_name = state.relation_name
            controller._file_name = state.source_file

            if state.df is not None:
                controller.df = state.df.copy()
                controller._data = (
                    state.df.where(state.df.notnull(), None).values.tolist()
                )

            if hasattr(controller, '_createDataFrame'):
                controller._createDataFrame()
            if hasattr(controller, '_updatePagedModel'):
                controller._current_page = 0
                controller._updatePagedModel()

            for signal_name in ('dataLoaded', 'pageChanged', 'metadataChanged'):
                signal = getattr(controller, signal_name, None)
                if signal is not None:
                    signal.emit()
            return None
        except Exception as error:
            logger.warning("Push to controller failed: %s", error)
            return str(error)

    def sync_types_from_controller(self, state: Dataset, controller) -> bool:
        """Apply user-selected type labels from a file controller to a Dataset."""
        if controller is None:
            return False

        raw_types = None
        selected_types = getattr(controller, '_selected_types', None)
        suggested_types = getattr(controller, '_suggested_types', None)
        if isinstance(selected_types, dict) and selected_types:
            raw_types = selected_types
        elif isinstance(suggested_types, dict) and suggested_types:
            raw_types = suggested_types

        if not raw_types or state.df is None:
            return False

        valid_columns = {str(column) for column in state.df.columns}
        normalized: Dict[str, str] = {}
        for column, type_label in raw_types.items():
            column_name = str(column)
            if column_name not in valid_columns or not isinstance(type_label, str):
                continue
            label = self._normalize_type_label(type_label)
            if label:
                normalized[column_name] = label

        if not normalized:
            return False

        state.selected_types.update(normalized)
        state.arff_attributes = build_arff_attributes(state)
        return True

    @staticmethod
    def _normalize_type_label(type_label: str) -> str | None:
        normalized = str(type_label).strip().lower()
        if 'num' in normalized:
            return 'Numeric'
        if 'nom' in normalized:
            return 'Nominal'
        if 'date' in normalized:
            return 'Date'
        return 'String' if normalized else None
