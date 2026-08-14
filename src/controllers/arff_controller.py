"""Controller for ARFF file operations (loading, saving, and type management)."""

import os
import logging
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
from PySide6.QtCore import Signal, Slot, QUrl, Property
from models.dataframe_adapter import DataFrameAdapter
from services.arff_file_service import ArffFileService
from services.arff_writer_service import ArffWriterService
from services.column_type_service import ColumnTypeService
from .base_controller import BaseDataController


logger = logging.getLogger(__name__)


class ARFFController(BaseDataController):
    """Controller for ARFF format operations, maintaining parity with CSVController."""

    dataLoaded = Signal()
    fileNameChanged = Signal()
    errorOccurred = Signal(str)
    successOccurred = Signal(str)
    metadataChanged = Signal()
    pageChanged = Signal()
    
    def __init__(self) -> None:
        super().__init__()
        self._data: Optional[List[List[Any]]] = None
        self._attributes: List[Tuple[str, Any]] = []
        self._relation_name: str = ""
        self._file_name: str = ""
        self.df: Optional[pd.DataFrame] = None
        self._model: Optional[DataFrameAdapter] = None
        self._files = ArffFileService()
        self._writer = ArffWriterService()
        self._suggested_types: Dict[str, str] = {}
        self._column_types = ColumnTypeService(self, '_suggested_types')
        self._page_size: int = 50
        self._current_page: int = 0
        self._available_types = ['Numeric', 'String', 'Nominal', 'Date']
    
    @Property('QVariant', notify=dataLoaded)
    def tableModel(self):
        """Returns the table model for QML display."""
        return self._model
    
    @Property(str, notify=fileNameChanged)
    def fileName(self) -> str:
        """Returns the loaded file name."""
        return self._file_name
    
    @Property(str, notify=metadataChanged)
    def relationName(self) -> str:
        """Returns the ARFF relation name."""
        return self._relation_name

    @Property(int, notify=pageChanged)
    def currentPage(self) -> int:
        """Returns the current page index (0-based)."""
        return self._current_page

    @Property(int, notify=pageChanged)
    def totalPages(self) -> int:
        """Returns the total number of pages."""
        if self.df is None or self._page_size <= 0:
            return 0
        return (len(self.df) + self._page_size - 1) // self._page_size

    @Property(int, notify=pageChanged)
    def pageSize(self) -> int:
        """Returns the number of rows per page."""
        return self._page_size

    @Slot(int)
    def setPageSize(self, page_size: int) -> None:
        """Sets the number of rows per page and resets to page 0."""
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
        """Sets the current page and updates the paged model."""
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
        """Advances to the next page."""
        self.setCurrentPage(self._current_page + 1)

    @Slot()
    def previousPage(self) -> None:
        """Goes back to the previous page."""
        self.setCurrentPage(self._current_page - 1)

    def _updatePagedModel(self) -> None:
        """Updates the table model with data from the current page."""
        if self.df is None or self._model is None:
            return
        
        start_idx = self._current_page * self._page_size
        end_idx = start_idx + self._page_size
        page_data = self.df.iloc[start_idx:end_idx]
        
        self._model.setDataFrame(page_data, show_headers=True)
    
    @Property(int, notify=dataLoaded)
    def instanceCount(self) -> int:
        """Returns the total number of instances (rows)."""
        return len(self._data) if self._data else 0
    
    @Property(int, notify=dataLoaded)
    def attributeCount(self) -> int:
        """Returns the total number of attributes (columns)."""
        return len(self._attributes)
    
    @Property(list, notify=metadataChanged)
    def availableTypes(self) -> List[str]:
        """Returns the available types for UI dropdown selection."""
        return self._available_types
    
    @Slot(QUrl)
    def loadArff(self, file_url: QUrl) -> None:
        """Load an ARFF file through the format service and refresh QML state."""
        try:
            if file_url.scheme() == "file":
                file_path = file_url.toLocalFile()
            else:
                file_path = file_url.toString()
            
            self._file_name = os.path.basename(file_path)
            self.fileNameChanged.emit()

            dataset = self._files.load(file_path)
            self._relation_name = dataset['relation']
            self._attributes = dataset['attributes']
            self._data = dataset['data']
            
            self._generateTypeSuggestions()
            self._createDataFrame()
            
            self.dataLoaded.emit()
            self.metadataChanged.emit()
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"[ARFF] Fatal error: {error_msg}")
            
            if "Invalid numerical value" in error_msg:
                detailed_msg = (
                    f"Erro ao carregar ARFF: {error_msg}\n\n"
                    "O arquivo contém valores não-numéricos em colunas declaradas como NUMERIC.\n"
                    "Sugestões:\n"
                    "1. Verifique se as colunas numéricas não contêm texto\n"
                    "2. Use '?' para valores ausentes\n"
                    "3. Declare colunas com texto como STRING ao invés de NUMERIC"
                )
            else:
                detailed_msg = f"Erro ao carregar arquivo ARFF: {error_msg}"
            
            self._data = None
            self._attributes = []
            self._relation_name = ""
            self.errorOccurred.emit(detailed_msg)
    
    def _generateTypeSuggestions(self) -> None:
        """Generates UI type suggestions based on ARFF attribute metadata."""
        self._suggested_types = {}
        
        for attr_name, attr_type in self._attributes:
            # attr_type is a string ('NUMERIC', 'STRING', 'DATE') or a list (nominal)
            if isinstance(attr_type, str):
                attr_type_upper = attr_type.upper().strip()
                
                if 'STRING' in attr_type_upper:
                    self._suggested_types[attr_name] = 'String'
                elif any(t in attr_type_upper for t in ('NUMERIC', 'REAL', 'INTEGER')):
                    self._suggested_types[attr_name] = 'Numeric'
                elif 'DATE' in attr_type_upper:
                    self._suggested_types[attr_name] = 'Date'
                else:
                    self._suggested_types[attr_name] = 'String'
            elif isinstance(attr_type, (list, tuple)):
                self._suggested_types[attr_name] = 'Nominal'
            else:
                self._suggested_types[attr_name] = 'String'
    
    def _createDataFrame(self) -> None:
        """Creates a pandas DataFrame from the loaded ARFF data."""
        try:
            if not self._data or not self._attributes:
                self.df = None
                self._model = None
                return
            
            column_names = [attr[0] for attr in self._attributes]
            self.df = pd.DataFrame(self._data, columns=column_names)
            self._model = DataFrameAdapter()
            self._current_page = 0
            self._updatePagedModel()
            self.pageChanged.emit()
            
        except Exception as e:
            logger.warning(f"Error creating DataFrame: {e}")
            self.df = None
            self._model = None
    
    @Slot(str, result=str)
    def getSuggestedType(self, attribute_name: str) -> str:
        return self._column_types.suggested_type(attribute_name)
    
    @Slot(str, result=list)
    def getAttributeExamples(self, attribute_name: str) -> List[str]:
        return self._column_types.examples(attribute_name)
    
    @Slot(result=list)
    def getAttributeNames(self) -> List[str]:
        """Returns the list of attribute names."""
        return [name for name, _ in self._attributes]
    
    @Slot(str, str)
    def setAttributeType(self, attribute_name: str, new_type: str) -> None:
        self._column_types.set_type(attribute_name, new_type)

    @Slot(result=int)
    def rowCount(self) -> int:
        """Returns the number of data rows."""
        return len(self._data) if self._data else 0
    
    @Slot(result=int)
    def columnCount(self) -> int:
        """Returns the number of data columns."""
        return len(self._attributes) if self._attributes else 0
    
    @Slot(int, result=str)
    def headerForColumn(self, column: int) -> str:
        """Returns the header name for a given column index."""
        if column < 0 or column >= len(self._attributes):
            return ""
        return str(self._attributes[column][0])

    @Slot(int)
    def deleteRow(self, global_row_index: int) -> None:
        """Removes a row by global index, keeping ARFF data and DataFrame in sync."""
        if not self._data:
            return
        try:
            idx = int(global_row_index)
        except Exception:
            return
        if idx < 0 or idx >= len(self._data):
            return

        try:
            self._data.pop(idx)
        except Exception:
            return

        if self.df is not None and 0 <= idx < len(self.df):
            self.df = self.df.drop(self.df.index[idx]).reset_index(drop=True)

        max_page = max(0, self.totalPages - 1)
        if self._current_page > max_page:
            self._current_page = max_page
        self._updatePagedModel()

        self.dataLoaded.emit()
        self.pageChanged.emit()

    @Slot(int)
    def deleteColumn(self, column_index: int) -> None:
        """Removes a column by index, updating attributes, data, and DataFrame."""
        if not self._attributes:
            return
        try:
            col_idx = int(column_index)
        except Exception:
            return
        if col_idx < 0 or col_idx >= len(self._attributes):
            return

        col_name = str(self._attributes[col_idx][0])

        try:
            self._attributes.pop(col_idx)
        except Exception:
            return
        self._suggested_types.pop(col_name, None)

        if self._data:
            new_data = []
            for row in self._data:
                if not isinstance(row, list):
                    row = list(row)
                if col_idx < len(row):
                    row.pop(col_idx)
                new_data.append(row)
            self._data = new_data

        if self.df is not None and col_name in self.df.columns:
            self.df = self.df.drop(columns=[col_name])

        max_page = max(0, self.totalPages - 1)
        if self._current_page > max_page:
            self._current_page = max_page
        self._updatePagedModel()

        self.dataLoaded.emit()
        self.metadataChanged.emit()
        self.pageChanged.emit()
    
    @Slot(str)
    def generateArff(self, output_path: str) -> None:
        """Generate an ARFF file through the format writer service."""
        try:
            if not self._data or not self._attributes:
                self.errorOccurred.emit("Nenhum dado carregado para gerar ARFF")
                return
            self._writer.write_rows(
                output_path,
                self._relation_name,
                self._attributes,
                self._data,
                self._suggested_types,
            )
            self.successOccurred.emit(f"Arquivo ARFF salvo com sucesso em: {output_path}")
        except Exception as error:
            self.errorOccurred.emit(f"Erro ao gerar arquivo ARFF: {error}")

    @Slot(str)
    def saveMetadata(self, output_path: str) -> None:
        """Save selected semantic metadata through the format writer service."""
        try:
            if not self._attributes:
                self.errorOccurred.emit("Não há metadados carregados")
                return
            self._writer.write_rows(
                output_path,
                self._relation_name or 'dataset',
                self._attributes,
                self._data or [],
                self._suggested_types,
                normalize_numeric=True,
            )
            self.successOccurred.emit(f"Arquivo ARFF salvo com sucesso em: {output_path}")
        except Exception as error:
            self.errorOccurred.emit(f"Erro ao salvar metadados: {error}")
    
    @Slot(str, result=list)
    def getValidTypesForAttribute(self, attribute_name: str) -> List[str]:
        return self._column_types.valid_types(attribute_name)
