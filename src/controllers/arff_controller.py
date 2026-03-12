"""Controller for ARFF file operations (loading, saving, and type management)."""

import os
import logging
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
from PySide6.QtCore import Signal, Slot, QUrl, Property
import arff
from models.table_model import DataFrameModel
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
        self._table_model: Optional[DataFrameModel] = None
        self._suggested_types: Dict[str, str] = {}
        self._page_size: int = 50
        self._current_page: int = 0
        self._available_types = ['Numeric', 'String', 'Nominal', 'Date']
    
    @Property('QVariant', notify=dataLoaded)
    def tableModel(self):
        """Returns the table model for QML display."""
        return self._table_model
    
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
        if self.df is None or self._table_model is None:
            return
        
        start_idx = self._current_page * self._page_size
        end_idx = start_idx + self._page_size
        page_data = self.df.iloc[start_idx:end_idx]
        
        self._table_model.setDataFrame(page_data, show_headers=True)
    
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
        """Loads and parses an ARFF file from the given URL."""
        try:
            if file_url.scheme() == "file":
                file_path = file_url.toLocalFile()
            else:
                file_path = file_url.toString()
            
            self._file_name = os.path.basename(file_path)
            self.fileNameChanged.emit()
            
            logger.warning(f"[ARFF] Loading file: {file_path}")
            
            self._diagnoseArffFile(file_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    dataset = arff.load(f, encode_nominal=False, return_type=arff.DENSE)
            except Exception as load_error:
                logger.warning(f"[ARFF] Default parser error: {load_error}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    dataset = arff.load(f, encode_nominal=False)
            
            self._relation_name = dataset['relation']
            self._attributes = dataset['attributes']
            
            logger.warning(f"[ARFF] Relation: {self._relation_name}")
            logger.warning(f"[ARFF] Attributes: {len(self._attributes)}")
            
            raw_data = dataset.get('data', [])
            if not raw_data:
                self._data = []
            else:
                self._data = []
                for line_num, row in enumerate(raw_data, start=1):
                    try:
                        if hasattr(row, '__iter__') and not isinstance(row, str):
                            row_list = list(row)
                        else:
                            row_list = [row]
                        self._data.append(row_list)
                    except Exception as row_error:
                        logger.warning(f"[ARFF] Row {line_num} error: {row_error}")
                        logger.warning(f"[ARFF] Row content: {row}")
                        # Preserve row indices by inserting None placeholders
                        self._data.append([None] * len(self._attributes))
                
                logger.warning(f"[ARFF] Loaded {len(self._data)} rows")
            
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
    
    def _diagnoseArffFile(self, file_path: str) -> None:
        """Logs diagnostic info about the ARFF file structure."""
        try:
            logger.warning(f"[ARFF DIAG] Analyzing file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            data_line_idx = None
            for idx, line in enumerate(lines):
                if line.strip().upper().startswith('@DATA'):
                    data_line_idx = idx
                    break
            
            if data_line_idx:
                logger.warning(f"[ARFF DIAG] @DATA found at line {data_line_idx + 1}")
                data_lines = lines[data_line_idx + 1:data_line_idx + 6]
                for i, line in enumerate(data_lines, start=data_line_idx + 2):
                    logger.warning(f"[ARFF DIAG] Line {i}: {line.strip()}")
        except Exception as e:
            logger.warning(f"[ARFF DIAG] Error: {e}")
    
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
                self._table_model = None
                return
            
            column_names = [attr[0] for attr in self._attributes]
            self.df = pd.DataFrame(self._data, columns=column_names)
            self._table_model = DataFrameModel()
            self._current_page = 0
            self._updatePagedModel()
            self.pageChanged.emit()
            
        except Exception as e:
            logger.warning(f"Error creating DataFrame: {e}")
            self.df = None
            self._table_model = None
    
    @Slot(str, result=str)
    def getSuggestedType(self, attribute_name: str) -> str:
        """Returns the suggested type for a given attribute."""
        return self._suggested_types.get(attribute_name, 'String')
    
    @Slot(str, result=list)
    def getAttributeExamples(self, attribute_name: str) -> List[str]:
        """Returns up to 5 random non-empty sample values for a given attribute."""
        import random
        if not self._data or not self._attributes:
            return []
        
        attr_index = None
        for i, (name, _) in enumerate(self._attributes):
            if name == attribute_name:
                attr_index = i
                break
        
        if attr_index is None:
            return []
        
        non_empty = []
        for row in self._data:
            if attr_index < len(row):
                value = row[attr_index]
                if value is not None:
                    text = str(value).strip()
                    if text:
                        non_empty.append(text)
        
        if not non_empty:
            return []
        
        rng = random.Random(hash(attribute_name))
        sampled = rng.sample(non_empty, min(5, len(non_empty)))
        
        examples = []
        for text in sampled:
            if len(text) > 30:
                text = text[:27] + "..."
            examples.append(text)
        
        return examples
    
    @Slot(result=list)
    def getAttributeNames(self) -> List[str]:
        """Returns the list of attribute names."""
        return [name for name, _ in self._attributes]
    
    @Slot(str, str)
    def setAttributeType(self, attribute_name: str, new_type: str) -> None:
        """Sets a new type for a given attribute."""
        self._suggested_types[attribute_name] = new_type

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
        """Generates a new ARFF file with the selected attribute types."""
        try:
            if not self._data or not self._attributes:
                self.errorOccurred.emit("Nenhum dado carregado para gerar ARFF")
                return
            
            reverse_mapping = {
                'Numeric': 'NUMERIC',
                'String': 'STRING',
                'Nominal': lambda values: list(set(str(v) for v in values if v is not None)),
                'Date': 'DATE'
            }
            
            new_attributes = []
            for i, (attr_name, _) in enumerate(self._attributes):
                selected_type = self._suggested_types.get(attr_name, 'String')
                
                if selected_type == 'Nominal':
                    column_values = [row[i] for row in self._data if i < len(row)]
                    unique_values = list(set(str(v) for v in column_values if v is not None))
                    new_attributes.append((attr_name, unique_values))
                else:
                    arff_type = reverse_mapping.get(selected_type, 'STRING')
                    new_attributes.append((attr_name, arff_type))
            
            dataset = {
                'relation': self._relation_name,
                'attributes': new_attributes,
                'data': self._data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                arff.dump(dataset, f)
            
            self.successOccurred.emit(f"Arquivo ARFF salvo com sucesso em: {output_path}")
            
        except Exception as e:
            self.errorOccurred.emit(f"Erro ao gerar arquivo ARFF: {e}")

    @Slot(str)
    def saveMetadata(self, output_path: str) -> None:
        """Saves metadata and data as a Weka-compatible ARFF file."""
        try:
            if not self._attributes:
                self.errorOccurred.emit("Não há metadados carregados")
                return

            new_attributes = []
            for i, (attr_name, _) in enumerate(self._attributes):
                selected_type = self._suggested_types.get(attr_name, 'String')
                if selected_type == 'Nominal' and self._data:
                    column_values = []
                    for row in self._data:
                        if i < len(row):
                            column_values.append(row[i])
                    unique_values = list(set(str(v) for v in column_values if v is not None))
                    if len(unique_values) == 0:
                        unique_values = ['_']
                    new_attributes.append((attr_name, unique_values))
                else:
                    mapping = {
                        'Numeric': 'NUMERIC',
                        'String': 'STRING',
                        'Date': 'DATE'
                    }
                    new_attributes.append((attr_name, mapping.get(selected_type, 'STRING')))

            processed_data = []
            for row in (self._data or []):
                processed_row = []
                for i, value in enumerate(row):
                    if i < len(self._attributes):
                        attr_name = self._attributes[i][0]
                        selected_type = self._suggested_types.get(attr_name, 'String')
                        
                        if selected_type == 'Numeric' and value is not None:
                            if isinstance(value, str):
                                value = value.replace(',', '.')
                            try:
                                value = float(value)
                            except (ValueError, TypeError):
                                pass
                    processed_row.append(value)
                processed_data.append(processed_row)

            dataset = {
                'relation': self._relation_name or 'dataset',
                'attributes': new_attributes,
                'data': processed_data
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                arff.dump(dataset, f)
            self.successOccurred.emit(f"Arquivo ARFF salvo com sucesso em: {output_path}")
        except Exception as e:
            self.errorOccurred.emit(f"Erro ao salvar metadados: {e}")
    
    @Slot(str, result=list)
    def getValidTypesForAttribute(self, attribute_name: str) -> List[str]:
        """Returns valid type conversions for an attribute based on compatibility rules."""
        if self.df is None or attribute_name not in self.df.columns:
            return ['String']
        
        column = self.df[attribute_name]
        current_type = self.getSuggestedType(attribute_name)
        
        if current_type == "Numeric":
            return ['Numeric', 'String', 'Nominal']
        elif current_type == "String":
            valid = ['String']
            unique_ratio = column.nunique() / len(column) if len(column) > 0 else 1
            if unique_ratio < 0.1:
                valid.append('Nominal')
            try:
                pd.to_datetime(column.dropna().head(5))
                valid.append('Date')
            except (ValueError, TypeError):
                pass
            return valid
        elif current_type == "Nominal":
            valid = ['Nominal', 'String']
            try:
                numeric_converted = pd.to_numeric(column.dropna(), errors='coerce')
                if not numeric_converted.isna().any():
                    valid.append('Numeric')
            except (ValueError, TypeError):
                pass
            return valid
        elif current_type == "Date":
            return ['Date', 'String']
        
        return ['String']
