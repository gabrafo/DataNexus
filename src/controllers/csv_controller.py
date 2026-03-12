"""Controller for CSV file handling."""

import os
import csv
import logging
from typing import Optional, List, Dict

import pandas as pd
from PySide6.QtCore import QObject, Signal, Slot, QUrl, Property
from models.table_model import DataFrameModel
from .base_controller import BaseDataController

logger = logging.getLogger(__name__)


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
        self._dialect: Optional[csv.Dialect] = None
        self._model = DataFrameModel()
        self._selected_types: Dict[str, str] = {}
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

    def _detect_header(self, file_path: str) -> bool:
        """Detect whether the first row contains column names."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                sample = f.read(8192)
                
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(sample)
            
            logger.warning(f"[CSV] Header detection: {has_header}")
            return has_header
            
        except Exception as e:
            # Defaults to True since most CSVs have headers
            return True

    def _detect_dialect(self, file_path: str) -> Optional[csv.Dialect]:
        """Auto-detect CSV format (delimiter, quoting, etc.)."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                sample = f.read(8192)

            # Restrict to common delimiters to avoid false positives
            common_delims = ",\t;|:"
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=common_delims)
            
            delim = getattr(dialect, 'delimiter', None)
            logger.warning(f"[CSV] Detected delimiter: {repr(delim)}")
            return dialect
        except Exception:
            return None

    @Slot(QUrl, str)
    def loadCsv(self, file_url: QUrl, user_delimiter: str = "") -> None:
        """Load a CSV file and initialize data structures."""
        try:
            if file_url.scheme() == "file":
                file_path = file_url.toLocalFile()
            else:
                file_path = file_url.toString()

            self._file_name = os.path.basename(file_path)
            self.fileNameChanged.emit()

            self._has_header = self._detect_header(file_path)
            
            if user_delimiter:
                if user_delimiter.lower() == "tab":
                    self._delimiter = "\t"
                elif user_delimiter.lower() == "espaço":
                    self._delimiter = " "
                else:
                    self._delimiter = user_delimiter
                logger.warning(f"[CSV] Using user-specified delimiter: {repr(self._delimiter)}")
            else:
                self._dialect = self._detect_dialect(file_path)
                self._delimiter = getattr(self._dialect, 'delimiter', None) if self._dialect else None
            
            read_kwargs = {}
            if self._delimiter:
                read_kwargs['sep'] = self._delimiter
            else:
                read_kwargs['sep'] = None
                read_kwargs['engine'] = 'python'

            if self._has_header:
                self.df = pd.read_csv(file_path, **read_kwargs)
            else:
                self.df = pd.read_csv(file_path, header=None, **read_kwargs)
                self.df.columns = [f"Coluna_{i}" for i in range(len(self.df.columns))]
            
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
        """Suggest a semantic type based on heuristic analysis of the column."""
        if attribute_name in getattr(self, "_selected_types", {}):
            return self._selected_types[attribute_name]

        if self.df is None or attribute_name not in self.df.columns:
            return "String"
        
        dtype = self.df[attribute_name].dtype
        
        if pd.api.types.is_numeric_dtype(dtype):
            return "Numeric"
        
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "Date"
        
        else:
            # Low unique count relative to total suggests nominal type
            unique_count = self.df[attribute_name].nunique()
            total_count = len(self.df[attribute_name])
            if unique_count <= 10 and unique_count / total_count < 0.1:
                return "Nominal"
            return "String"
    
    @Slot(str, result=list)
    def getAttributeExamples(self, attribute_name: str) -> List[str]:
        """Return up to 5 random non-empty values from the column for preview."""
        import random
        if self.df is None or attribute_name not in self.df.columns:
            return []
        
        non_empty = [str(v) for v in self.df[attribute_name] if not pd.isna(v) and str(v).strip() != ""]
        if not non_empty:
            return []
        
        rng = random.Random(hash(attribute_name))
        sampled = rng.sample(non_empty, min(5, len(non_empty)))
        
        examples: List[str] = []
        for text in sampled:
            if len(text) > 30:
                text = text[:27] + "..."
            examples.append(text)
        return examples
    
    @Property(list, constant=True)
    def availableTypes(self) -> List[str]:
        """Available types for manual selection by the user."""
        return ['Numeric', 'String', 'Nominal', 'Date']
    
    @Slot(str, str)
    def setAttributeType(self, attribute_name: str, new_type: str) -> None:
        """Override the suggested type for an attribute."""
        if not attribute_name:
            return
        if not hasattr(self, "_selected_types"):
            self._selected_types = {}
        self._selected_types[attribute_name] = new_type
        # Forces re-render of dependent QML components
        self.metadataChanged.emit()
    
    
    @Slot(str, result=list)
    def getValidTypesForAttribute(self, attribute_name: str) -> List[str]:
        """Determine allowed type conversions based on semantic compatibility."""
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
            
            # Sample-based date parsing to avoid blocking on large datasets
            try:
                pd.to_datetime(column.dropna().head(5))
                valid.append('Date')
            except (ValueError, TypeError):
                pass
            
            return valid
        
        elif current_type == "Nominal":
            valid = ['Nominal', 'String']
            
            # Check if nominal values are actually numbers stored as strings
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
    
    @Slot(str)
    def generateArff(self, output_path: str) -> None:
        """Generate an ARFF file from the loaded CSV data."""
        try:
            if self.df is None:
                self.errorOccurred.emit("Nenhum dado carregado para gerar ARFF")
                return
            
            import arff
            
            attributes = []
            for col in self.df.columns:
                selected = self._selected_types.get(col) if hasattr(self, "_selected_types") else None
                if selected == 'Numeric':
                    attributes.append((col, 'NUMERIC'))
                elif selected == 'Date':
                    attributes.append((col, 'DATE'))
                elif selected == 'Nominal':
                    uniques = list(set(str(v) for v in self.df[col].dropna().unique().tolist()))[:50]
                    attributes.append((col, uniques if uniques else 'STRING'))
                elif selected == 'Relational':
                    attributes.append((col, 'STRING'))
                else:
                    dtype = self.df[col].dtype
                    if pd.api.types.is_numeric_dtype(dtype):
                        attributes.append((col, 'NUMERIC'))
                    else:
                        attributes.append((col, 'STRING'))
            
            data = []
            for _, row in self.df.iterrows():
                data_row = []
                for col in self.df.columns:
                    value = row[col]
                    if pd.isna(value):
                        data_row.append(None)
                    else:
                        data_row.append(value)
                data.append(data_row)
            
            dataset = {
                'relation': self._file_name.replace('.csv', ''),
                'attributes': attributes,
                'data': data
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                arff.dump(dataset, f)
            
            self.successOccurred.emit(f"Arquivo ARFF salvo com sucesso em: {output_path}")
            
        except Exception as e:
            self.errorOccurred.emit(f"Erro ao gerar arquivo ARFF: {e}")

    @Slot(str)
    def saveMetadata(self, output_path: str) -> None:
        """Save metadata and data as a Weka-compatible ARFF file."""
        try:
            if self.df is None:
                self.errorOccurred.emit("Nenhum dado carregado para salvar metadados")
                return

            import arff

            attributes = []
            for col in self.df.columns:
                selected = self._selected_types.get(col) if hasattr(self, "_selected_types") else None
                chosen = selected or self.getSuggestedType(col)
                if chosen == 'Numeric':
                    attributes.append((col, 'NUMERIC'))
                elif chosen == 'Date':
                    attributes.append((col, 'DATE'))
                elif chosen == 'Nominal':
                    uniques = list(set(str(v) for v in self.df[col].dropna().unique().tolist()))[:50]
                    attributes.append((col, uniques if uniques else 'STRING'))
                else:
                    attributes.append((col, 'STRING'))

            # Numeric columns may use comma as decimal separator, convert to dot
            data = []
            for _, row in self.df.iterrows():
                row_list = []
                for col in self.df.columns:
                    v = row[col]
                    if pd.isna(v):
                        row_list.append(None)
                    else:
                        selected = self._selected_types.get(col) if hasattr(self, "_selected_types") else None
                        chosen = selected or self.getSuggestedType(col)
                        if chosen == 'Numeric':
                            if isinstance(v, str):
                                v = v.replace(',', '.')
                            try:
                                v = float(v)
                            except (ValueError, TypeError):
                                pass
                        row_list.append(v)
                data.append(row_list)

            dataset = {
                'relation': self._file_name.replace('.csv', '') or 'dataset',
                'attributes': attributes,
                'data': data
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                arff.dump(dataset, f)

            self.successOccurred.emit(f"Arquivo ARFF salvo em: {output_path}")
        except Exception as e:
            self.errorOccurred.emit(f"Erro ao salvar metadados: {e}")