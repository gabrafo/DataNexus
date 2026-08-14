"""Qt table model backed by a pandas DataFrame."""

from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex


class DataFrameAdapter(QAbstractTableModel):
    """Adapter between a pandas DataFrame and Qt's QAbstractTableModel for QML."""

    def __init__(self, dataframe: pd.DataFrame | None = None, show_headers: bool = False) -> None:
        """Initialize with an optional DataFrame."""
        super().__init__()
        self._df: pd.DataFrame = dataframe.copy() if dataframe is not None else pd.DataFrame()
        self._show_headers: bool = show_headers
        # Extra UI-only column (e.g. delete button) to avoid polluting the DataFrame
        self._action_column_enabled: bool = False

    def setActionColumnEnabled(self, enabled: bool) -> None:
        """Enables or disables an extra action column at the end for UI controls."""
        enabled = bool(enabled)
        if enabled == self._action_column_enabled:
            return
        self.beginResetModel()
        self._action_column_enabled = enabled
        self.endResetModel()

    def setDataFrame(self, dataframe: pd.DataFrame, show_headers: bool = False) -> None:
        """Replaces the current DataFrame and notifies views."""
        self.beginResetModel()
        self._df = dataframe.copy()
        self._show_headers = show_headers
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        """Number of rows in the dataset."""
        return int(self._df.shape[0])

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        """Number of columns in the dataset."""
        extra = 1 if self._action_column_enabled else 0
        return int(self._df.shape[1] + extra)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
        """Returns the data for a given cell index and role."""
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        # Action column is UI-only; the view draws its own controls
        if self._action_column_enabled and index.column() >= self._df.shape[1]:
            return ""
        
        value = self._df.iat[index.row(), index.column()]
        
        # Show blank instead of NaN for cleaner display
        if pd.isna(value):
            return ""
        return str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore[override]
        """Returns header labels for rows and columns."""
        if role != Qt.DisplayRole:
            return None
        
        if orientation == Qt.Horizontal:
            if 0 <= section < self._df.shape[1]:
                return str(self._df.columns[section])
            if self._action_column_enabled and section == self._df.shape[1]:
                return ""
            return ""
        
        # 1-indexed for user-facing display
        return str(section + 1)

    def roleNames(self):
        """Maps Qt roles to QML role names."""
        return {Qt.DisplayRole: b"display"}
