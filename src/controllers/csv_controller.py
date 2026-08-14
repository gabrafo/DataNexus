"""Controller for CSV file handling."""

import os
from typing import Optional, List, Dict

import pandas as pd
from PySide6.QtCore import QObject, Signal, Slot, QUrl, Property
from models.dataframe_adapter import DataFrameAdapter
from services.column_type_service import ColumnTypeService
from services.csv_file_service import CsvFileService
from services.arff_writer_service import ArffWriterService
from .base_controller import BaseDataController

class CSVController(BaseDataController):
    """Controller for CSV dataset operations."""

    dataframeChanged = Signal()
    fileNameChanged = Signal()
    errorOccurred = Signal(str)
    successOccurred = Signal(str)
    infoChanged = Signal()
    metadataChanged = Signal()
    pageChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.df: Optional[pd.DataFrame] = None
        self._file_name: str = ""
        self._has_header: bool = True
        self._delimiter: Optional[str] = None
        self._model = DataFrameAdapter()
        self._files = CsvFileService()
        self._writer = ArffWriterService()
        self._selected_types: Dict[str, str] = {}
        self._column_types = ColumnTypeService(self, '_selected_types')
        self._page_size: int = 50
        self._current_page: int = 0

    @Property(int, notify=dataframeChanged)
    def instanceCount(self) -> int:
        """Total number of instances (rows) in the dataset."""
        return 0 if self.df is None else int(self.df.shape[0])

    @Property(int, notify=dataframeChanged)
    def attributeCount(self) -> int:
        """Total number of attributes (columns) in the dataset."""
        return 0 if self.df is None else int(self.df.shape[1])

    @Property(str, notify=fileNameChanged)
    def fileName(self) -> str:
        """Loaded CSV file name (without path)."""
        return self._file_name

    @Property(str, notify=infoChanged)
    def info(self) -> str:
        """Informational string about dataset dimensions."""
        if self.df is None:
            return "Nenhum dado carregado"
        rows, cols = self.df.shape
        return f"Linhas: {rows} | Colunas: {cols}"

    @Property(QObject, constant=True)
    def tableModel(self) -> QObject:
        """Exposed to QML as the table model."""
        return self._model

    @Property(int, notify=pageChanged)
    def currentPage(self) -> int:
        """Current page index (0-based)."""
        return self._current_page

    @Property(int, notify=pageChanged)
    def totalPages(self) -> int:
        """Total number of available pages."""
        if self.df is None or self._page_size <= 0:
            return 0
        return (len(self.df) + self._page_size - 1) // self._page_size

    @Property(int, notify=pageChanged)
    def pageSize(self) -> int:
        """Number of rows per page."""
        return self._page_size

    @Slot(int)
    def setPageSize(self, page_size: int) -> None:
        """Set the number of rows per page and reset to page 0."""
        if self.df is None:
            self._page_size = max(1, int(page_size))
            self._current_page = 0
            self.pageChanged.emit()
            return

        try:
            page_size_int = int(page_size)
        except Exception:
            page_size_int = self._page_size

        page_size_int = max(1, page_size_int)
        if page_size_int == self._page_size:
            return

        self._page_size = page_size_int
        self._current_page = 0
        self._updatePagedModel()
        self.pageChanged.emit()

    @Slot(int)
    def setCurrentPage(self, page: int) -> None:
        """Set the current page and update the model."""
        if self.df is None:
            return
        
        max_page = self.totalPages - 1
        page = max(0, min(page, max_page))
        
        if page != self._current_page:
            self._current_page = page
            self._updatePagedModel()
            self.pageChanged.emit()

    @Slot()
    def nextPage(self) -> None:
        """Go to the next page."""
        self.setCurrentPage(self._current_page + 1)

    @Slot()
    def previousPage(self) -> None:
        """Go to the previous page."""
        self.setCurrentPage(self._current_page - 1)

    def _updatePagedModel(self) -> None:
        """Load only the current page into the Qt model."""
        if self.df is None:
            return
        
        start_idx = self._current_page * self._page_size
        end_idx = start_idx + self._page_size
        page_data = self.df.iloc[start_idx:end_idx]
        
        self._model.setDataFrame(page_data, show_headers=self._has_header)

    @Slot(int)
    def deleteRow(self, global_row_index: int) -> None:
        """Remove a row by global index (0-based, not page-relative)."""
        if self.df is None:
            return
        try:
            idx = int(global_row_index)
        except Exception:
            return
        if idx < 0 or idx >= len(self.df):
            return

        self.df = self.df.drop(self.df.index[idx]).reset_index(drop=True)

        # Adjust current page if total pages decreased
        max_page = max(0, self.totalPages - 1)
        if self._current_page > max_page:
            self._current_page = max_page
        self._updatePagedModel()

        self.dataframeChanged.emit()
        self.infoChanged.emit()
        self.pageChanged.emit()

    @Slot(int)
    def deleteColumn(self, column_index: int) -> None:
        """Remove a column by index (0-based). Also removes associated metadata."""
        if self.df is None:
            return
        try:
            col_idx = int(column_index)
        except Exception:
            return
        if col_idx < 0 or col_idx >= self.df.shape[1]:
            return

        col_name = str(self.df.columns[col_idx])
        self.df = self.df.drop(columns=[col_name])
        self._selected_types.pop(col_name, None)

        max_page = max(0, self.totalPages - 1)
        if self._current_page > max_page:
            self._current_page = max_page
        self._updatePagedModel()

        self.dataframeChanged.emit()
        self.infoChanged.emit()
        self.pageChanged.emit()
        self.metadataChanged.emit()

    @Slot(QUrl, str)
    def loadCsv(self, file_url: QUrl, user_delimiter: str = "") -> None:
        """Load a CSV file through the format service and refresh QML state."""
        try:
            if file_url.scheme() == "file":
                file_path = file_url.toLocalFile()
            else:
                file_path = file_url.toString()

            self._file_name = os.path.basename(file_path)
            self.fileNameChanged.emit()

            result = self._files.load(file_path, user_delimiter)
            self.df = result.dataframe
            self._has_header = result.has_header
            self._delimiter = result.delimiter
            
            self._current_page = 0
            self._updatePagedModel()
            self.dataframeChanged.emit()
            self.infoChanged.emit()
            self.pageChanged.emit()
            self._selected_types.clear()
            self.metadataChanged.emit()
        except Exception as e: 
            self.df = None
            self.dataframeChanged.emit()
            self.infoChanged.emit()
            self.errorOccurred.emit(f"Erro ao carregar CSV: {e}")

    @Slot(result=str)
    def detectedDelimiter(self) -> str:
        """Return the detected delimiter in a UI-friendly representation."""
        d = self._delimiter
        if not d:
            return "(não detectado)"
        if d == "\t":
            return "Tab"
        return d

    @Slot(result=int)
    def rowCount(self) -> int:
        """Total number of rows in the full (non-paginated) dataset."""
        return 0 if self.df is None else int(self.df.shape[0])

    @Slot(result=int)
    def columnCount(self) -> int:
        """Total number of columns in the dataset."""
        return 0 if self.df is None else int(self.df.shape[1])

    @Slot(int, result=str)
    def headerForColumn(self, column: int) -> str:
        """Return column name by index."""
        if self.df is None:
            return ""
        if column < 0 or column >= self.df.shape[1]:
            return ""
        return str(self.df.columns[column])

    @Slot(int, int, result=str)
    def dataAt(self, row: int, column: int) -> str:
        """Direct access to a specific cell value."""
        if self.df is None:
            return ""
        if row < 0 or column < 0:
            return ""
        if row >= self.df.shape[0] or column >= self.df.shape[1]:
            return ""
        value = self.df.iat[row, column]
        return "" if pd.isna(value) else str(value)
    
    @Slot(result=list)
    def getAttributeNames(self) -> List[str]:
        """List all column names."""
        if self.df is None:
            return []
        return list(self.df.columns)
    
    @Slot(str, result=str)
    def getSuggestedType(self, attribute_name: str) -> str:
        return self._column_types.suggested_type(attribute_name)
    
    @Slot(str, result=list)
    def getAttributeExamples(self, attribute_name: str) -> List[str]:
        return self._column_types.examples(attribute_name)
    
    @Property(list, constant=True)
    def availableTypes(self) -> List[str]:
        """Available types for manual selection by the user."""
        return ['Numeric', 'String', 'Nominal', 'Date']
    
    @Slot(str, str)
    def setAttributeType(self, attribute_name: str, new_type: str) -> None:
        self._column_types.set_type(attribute_name, new_type)
        self.metadataChanged.emit()
    
    
    @Slot(str, result=list)
    def getValidTypesForAttribute(self, attribute_name: str) -> List[str]:
        return self._column_types.valid_types(attribute_name)
    
    @Slot(str)
    def generateArff(self, output_path: str) -> None:
        """Generate an ARFF file through the format writer service."""
        try:
            if self.df is None:
                self.errorOccurred.emit("Nenhum dado carregado para gerar ARFF")
                return
            self._writer.write_dataframe(
                output_path,
                self.df,
                self._selected_types,
                self._file_name.replace('.csv', ''),
            )
            self.successOccurred.emit(f"Arquivo ARFF salvo com sucesso em: {output_path}")
        except Exception as error:
            self.errorOccurred.emit(f"Erro ao gerar arquivo ARFF: {error}")

    @Slot(str)
    def saveMetadata(self, output_path: str) -> None:
        """Save selected semantic metadata through the format writer service."""
        try:
            if self.df is None:
                self.errorOccurred.emit("Nenhum dado carregado para salvar metadados")
                return
            selected = {
                column: self.getSuggestedType(column)
                for column in self.df.columns
            }
            self._writer.write_dataframe(
                output_path,
                self.df,
                selected,
                self._file_name.replace('.csv', '') or 'dataset',
                normalize_numeric=True,
            )
            self.successOccurred.emit(f"Arquivo ARFF salvo em: {output_path}")
        except Exception as error:
            self.errorOccurred.emit(f"Erro ao salvar metadados: {error}")
