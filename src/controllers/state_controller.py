"""Global application state controller.

Acts as a facade over MergeService and SerializationService,
exposing Qt Properties and Slots for QML consumption.
"""

import gc
from typing import Optional, List, Dict, Any

import pandas as pd
from PySide6.QtCore import QObject, Signal, Slot, Property, QCoreApplication

from models.dataset import Dataset, build_arff_attributes
from services.merge_service import MergeService
from services.serialization_service import SerializationService
from services.dataset_sync_service import DatasetSyncService

class StateController(QObject):
    """Central state controller and QML facade.

    Owns two Dataset instances (primary and secondary) and
    delegates merge, serialization, and type-inference logic to
    dedicated service classes.
    """

    primaryBaseChanged = Signal()
    secondaryBaseChanged = Signal()
    mergeCompleted = Signal(str)
    errorOccurred = Signal(str)
    columnMappingChanged = Signal()
    canMergeChanged = Signal()
    loadingTargetChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._primary = Dataset()
        self._secondary = Dataset()
        self._column_mapping: Dict[str, str] = {}
        self._loading_target: str = "primary"
        self._sync = DatasetSyncService()
        self._merge = MergeService(
            self._primary, self._secondary, self._column_mapping,
            translator=self._merge_tr,
        )

    @staticmethod
    def _tr(text: str) -> str:
        return QCoreApplication.translate("StateController", text)

    @staticmethod
    def _merge_tr(text: str) -> str:
        return QCoreApplication.translate("MergeService", text)

    def _rebuild_merge_service(self) -> None:
        """Recreate MergeService after primary/secondary reassignment."""
        self._merge = MergeService(
            self._primary, self._secondary, self._column_mapping,
            translator=self._merge_tr,
        )

    # ------------------------------------------------------------------ #
    #  Properties                                                         #
    # ------------------------------------------------------------------ #

    @Property(bool, notify=primaryBaseChanged)
    def hasPrimaryBase(self) -> bool:
        """Whether a primary dataset is loaded."""
        return self._primary.is_loaded()

    @Property(bool, notify=primaryBaseChanged)
    def isPrimaryPreprocessed(self) -> bool:
        """Whether the primary dataset has been preprocessed."""
        return self._primary.is_preprocessed

    @Property(str, notify=primaryBaseChanged)
    def primaryFileName(self) -> str:
        """Source file name of the primary dataset."""
        return self._primary.source_file

    @Property(int, notify=primaryBaseChanged)
    def primaryInstanceCount(self) -> int:
        """Row count of the primary dataset."""
        return len(self._primary.df) if self._primary.df is not None else 0

    @Property(int, notify=primaryBaseChanged)
    def primaryAttributeCount(self) -> int:
        """Column count of the primary dataset."""
        return len(self._primary.df.columns) if self._primary.df is not None else 0

    @Property(str, notify=primaryBaseChanged)
    def primaryFormat(self) -> str:
        """Original file format of the primary dataset."""
        return self._primary.original_format

    @Property(bool, notify=secondaryBaseChanged)
    def hasSecondaryBase(self) -> bool:
        """Whether a secondary dataset is loaded."""
        return self._secondary.is_loaded()

    @Property(bool, notify=secondaryBaseChanged)
    def isSecondaryPreprocessed(self) -> bool:
        """Whether the secondary dataset has been preprocessed."""
        return self._secondary.is_preprocessed

    @Property(str, notify=secondaryBaseChanged)
    def secondaryFileName(self) -> str:
        """Source file name of the secondary dataset."""
        return self._secondary.source_file

    @Property(int, notify=secondaryBaseChanged)
    def secondaryInstanceCount(self) -> int:
        """Row count of the secondary dataset."""
        return len(self._secondary.df) if self._secondary.df is not None else 0

    @Property(int, notify=secondaryBaseChanged)
    def secondaryAttributeCount(self) -> int:
        """Column count of the secondary dataset."""
        return len(self._secondary.df.columns) if self._secondary.df is not None else 0

    @Property(str, notify=secondaryBaseChanged)
    def secondaryFormat(self) -> str:
        """Original file format of the secondary dataset."""
        return self._secondary.original_format

    @Property(bool, notify=canMergeChanged)
    def canMerge(self) -> bool:
        """Whether both datasets are loaded and preprocessed."""
        return (
            self._primary.is_loaded() and self._primary.is_preprocessed
            and self._secondary.is_loaded() and self._secondary.is_preprocessed
        )

    @Property(str, notify=loadingTargetChanged)
    def loadingTarget(self) -> str:
        """Which slot is the target for the next load: 'primary' or 'secondary'."""
        return self._loading_target

    # ------------------------------------------------------------------ #
    #  Loading target                                                     #
    # ------------------------------------------------------------------ #

    @Slot(str)
    def setLoadingTarget(self, target: str) -> None:
        """Set the loading target to 'primary' or 'secondary'."""
        if target in ("primary", "secondary") and target != self._loading_target:
            self._loading_target = target
            self.loadingTargetChanged.emit()

    @Slot()
    def setLoadingPrimary(self) -> None:
        """Shortcut to set loading target to primary."""
        self.setLoadingTarget("primary")

    @Slot()
    def setLoadingSecondary(self) -> None:
        """Shortcut to set loading target to secondary."""
        self.setLoadingTarget("secondary")

    # ------------------------------------------------------------------ #
    #  Column queries                                                     #
    # ------------------------------------------------------------------ #

    @Slot(result=list)
    def getPrimaryColumns(self) -> List[str]:
        """Return column names of the primary dataset."""
        return list(self._primary.df.columns) if self._primary.df is not None else []

    @Slot(result=list)
    def getSecondaryColumns(self) -> List[str]:
        """Return column names of the secondary dataset."""
        return list(self._secondary.df.columns) if self._secondary.df is not None else []

    @Slot(result=list)
    def getCommonColumns(self) -> List[str]:
        """Return columns usable as merge key, including mapped ones."""
        return self._merge.get_common_columns()

    @Slot(result=list)
    def getMappablePrimaryColumns(self) -> List[str]:
        """Return primary columns available for mapping."""
        return list(self._primary.df.columns) if self._primary.df is not None else []

    @Slot(result=list)
    def getMappableSecondaryColumns(self) -> List[str]:
        """Return secondary columns not yet mapped."""
        return self._merge.get_mappable_secondary_columns()

    # ------------------------------------------------------------------ #
    #  Column mapping                                                     #
    # ------------------------------------------------------------------ #

    @Slot(str, str, result=str)
    def checkMappingCompatibility(self, secondary_col: str, primary_col: str) -> str:
        """Return error message if types are incompatible, empty string otherwise."""
        return self._merge.check_mapping_compatibility(secondary_col, primary_col)

    @Slot(str, str, result=bool)
    def addColumnMapping(self, secondary_col: str, primary_col: str) -> bool:
        """Set the single column mapping after type check (replaces any previous pair)."""
        ok, err = self._merge.add_mapping(secondary_col, primary_col)
        if not ok:
            self.errorOccurred.emit(err)
        else:
            self.columnMappingChanged.emit()
        return ok

    @Slot(str)
    def removeColumnMapping(self, secondary_col: str) -> None:
        """Remove a column mapping."""
        self._merge.remove_mapping(secondary_col)
        self.columnMappingChanged.emit()

    @Slot()
    def clearColumnMappings(self) -> None:
        """Clear all column mappings."""
        self._merge.clear_mappings()
        self.columnMappingChanged.emit()

    @Slot(result=list)
    def getColumnMappings(self) -> List[Dict[str, str]]:
        """Return current column mappings."""
        return self._merge.get_mappings()

    @Property(bool, notify=columnMappingChanged)
    def hasMappings(self) -> bool:
        """Return True if any column mappings exist (QML bindings refresh on change)."""
        return self._merge.has_mappings()

    @Slot(result=list)
    def getMappingsForDropdown(self) -> List[str]:
        """Return mappings formatted for dropdown display."""
        return self._merge.get_mappings_for_dropdown()

    @Slot(str, result=str)
    def getMappingPrimaryColumn(self, formatted: str) -> str:
        """Extract primary column name from formatted mapping string."""
        return MergeService.extract_primary_column(formatted)

    # ------------------------------------------------------------------ #
    #  State mutations                                                    #
    # ------------------------------------------------------------------ #

    @Slot()
    def markPrimaryAsPreprocessed(self) -> None:
        """Mark the primary dataset as preprocessed."""
        self._primary.is_preprocessed = True
        self.primaryBaseChanged.emit()
        self.canMergeChanged.emit()

    @Slot()
    def markSecondaryAsPreprocessed(self) -> None:
        """Mark the secondary dataset as preprocessed."""
        self._secondary.is_preprocessed = True
        self.secondaryBaseChanged.emit()
        self.canMergeChanged.emit()

    @Slot()
    def clearSecondaryBase(self) -> None:
        """Clear the secondary dataset and mappings."""
        self._secondary.clear()
        self._column_mapping.clear()
        self.secondaryBaseChanged.emit()
        self.columnMappingChanged.emit()
        self.canMergeChanged.emit()

    @Slot()
    def clearPrimaryBase(self) -> None:
        """Clear the primary dataset."""
        self._primary.clear()
        self.primaryBaseChanged.emit()
        self.canMergeChanged.emit()

    @Slot()
    def clearAllBases(self) -> None:
        """Clear both datasets and all mappings."""
        self._primary.clear()
        self._secondary.clear()
        self._column_mapping.clear()
        self.primaryBaseChanged.emit()
        self.secondaryBaseChanged.emit()
        self.columnMappingChanged.emit()
        self.canMergeChanged.emit()

    @Slot()
    def swapBases(self) -> None:
        """Swap primary and secondary datasets."""
        if not self._secondary.is_loaded():
            return
        self._primary, self._secondary = self._secondary, self._primary
        self._rebuild_merge_service()
        self.primaryBaseChanged.emit()
        self.secondaryBaseChanged.emit()
        self.columnMappingChanged.emit()
        self.canMergeChanged.emit()

    @Slot(str, result=str)
    def keepBase(self, which: str) -> str:
        """Keep one base as primary, discard the other.

        Args:
            which: 'primary' or 'secondary'.

        Returns:
            File name of the kept base.
        """
        if which == "secondary" and self._secondary.is_loaded():
            self._primary = self._secondary
            self._secondary = Dataset()
            self._column_mapping.clear()
            self._rebuild_merge_service()
            self.primaryBaseChanged.emit()
            self.secondaryBaseChanged.emit()
            self.columnMappingChanged.emit()
            gc.collect()
            return self._primary.source_file

        self._secondary.clear()
        self._column_mapping.clear()
        self.secondaryBaseChanged.emit()
        self.columnMappingChanged.emit()
        gc.collect()
        return self._primary.source_file

    # ------------------------------------------------------------------ #
    #  Merge                                                              #
    # ------------------------------------------------------------------ #

    @Slot(str, str, result='QVariantMap')
    def checkMergeCompatibility(self, key_column: str, join_type: str) -> Dict[str, Any]:
        """Check merge compatibility without performing the merge."""
        return self._merge.check_compatibility(key_column, join_type)

    @Slot(str, str, result='QVariantMap')
    def previewMerge(self, key_column: str, join_type: str) -> Dict[str, Any]:
        """Generate a merge preview using sampled data."""
        return self._merge.preview(key_column, join_type)

    @Slot(str, str, result=bool)
    def executeMerge(self, key_column: str, join_type: str) -> bool:
        """Execute the merge. Result replaces the primary dataset."""
        ok, msg = self._merge.execute(key_column, join_type)
        if ok:
            self.primaryBaseChanged.emit()
            self.secondaryBaseChanged.emit()
            self.columnMappingChanged.emit()
            self.mergeCompleted.emit(msg)
        else:
            self.errorOccurred.emit(msg)
        return ok

    # ------------------------------------------------------------------ #
    #  Serialization                                                      #
    # ------------------------------------------------------------------ #

    @Slot(str, result=bool)
    def saveToFile(self, file_path: str) -> bool:
        """Save the primary dataset to file (format detected from extension)."""
        return self.saveBaseToFile("primary", file_path)

    @Slot(str, str, result=bool)
    def saveBaseToFile(self, which: str, file_path: str) -> bool:
        """Save a specific dataset to file.

        Args:
            which: 'primary' or 'secondary'.
            file_path: Destination path.
        """
        target = self._primary if which == "primary" else self._secondary
        if not target.is_loaded():
            self.errorOccurred.emit(self._tr("No data to save"))
            return False
        ok, err = SerializationService.save(target, file_path)
        if not ok:
            self.errorOccurred.emit(err)
        return ok

    # ------------------------------------------------------------------ #
    #  Info                                                               #
    # ------------------------------------------------------------------ #

    @Slot(str, result='QVariantMap')
    def getBaseInfo(self, which: str) -> Dict[str, Any]:
        """Return metadata about a specific dataset."""
        b = self._primary if which == "primary" else self._secondary
        return {
            'loaded': b.is_loaded(),
            'preprocessed': b.is_preprocessed,
            'fileName': b.source_file,
            'instanceCount': len(b.df) if b.df is not None else 0,
            'attributeCount': len(b.df.columns) if b.df is not None else 0,
            'format': b.original_format,
            'relationName': b.relation_name,
        }

    # ------------------------------------------------------------------ #
    #  Controller synchronization                                         #
    # ------------------------------------------------------------------ #

    def _sync_controller(
        self,
        target: Dataset,
        controller,
        source_file: str,
        file_format: str,
        clear_mapping: bool,
    ) -> None:
        """Delegate controller-to-state synchronization and report errors."""
        error = self._sync.sync_from_controller(
            target,
            controller,
            source_file,
            file_format,
            clear_mapping,
            self._column_mapping,
        )
        if error:
            self.errorOccurred.emit(self._tr("Sync error: {error}").format(error=error))

    @Slot('QVariant', str, str)
    def syncPrimaryFromCSV(self, controller, source_file: str, file_type: str) -> None:
        """Sync primary state from a CSVController."""
        if controller is None:
            return
        self._sync_controller(self._primary, controller, source_file, "csv", False)
        self.primaryBaseChanged.emit()
        self.canMergeChanged.emit()

    @Slot('QVariant', str, str)
    def syncPrimaryFromARFF(self, controller, source_file: str, file_type: str) -> None:
        """Sync primary state from an ARFFController."""
        if controller is None:
            return
        self._sync_controller(self._primary, controller, source_file, "arff", False)
        self.primaryBaseChanged.emit()
        self.canMergeChanged.emit()

    @Slot('QVariant', str, str)
    def syncSecondaryFromCSV(self, controller, source_file: str, file_type: str) -> None:
        """Sync secondary state from a CSVController."""
        if controller is None:
            return
        self._sync_controller(self._secondary, controller, source_file, "csv", True)
        self.secondaryBaseChanged.emit()
        self.columnMappingChanged.emit()
        self.canMergeChanged.emit()

    @Slot('QVariant', str, str)
    def syncSecondaryFromARFF(self, controller, source_file: str, file_type: str) -> None:
        """Sync secondary state from an ARFFController."""
        if controller is None:
            return
        self._sync_controller(self._secondary, controller, source_file, "arff", True)
        self.secondaryBaseChanged.emit()
        self.columnMappingChanged.emit()
        self.canMergeChanged.emit()

    @Slot('QVariant', str)
    def syncFromCSV(self, controller, source_file: str) -> None:
        """Sync from CSVController using current loading target."""
        if self._loading_target == "secondary":
            self.syncSecondaryFromCSV(controller, source_file, "csv")
        else:
            self.syncPrimaryFromCSV(controller, source_file, "csv")

    @Slot('QVariant', str)
    def syncFromARFF(self, controller, source_file: str) -> None:
        """Sync from ARFFController using current loading target."""
        if self._loading_target == "secondary":
            self.syncSecondaryFromARFF(controller, source_file, "arff")
        else:
            self.syncPrimaryFromARFF(controller, source_file, "arff")

    # ------------------------------------------------------------------ #
    #  Push state to controllers                                          #
    # ------------------------------------------------------------------ #

    def _push_state_to_controller(self, state: Dataset, controller) -> None:
        """Delegate state-to-controller synchronization and report errors."""
        error = self._sync.push_to_controller(state, controller)
        if error:
            self.errorOccurred.emit(f"Controller sync error: {error}")

    @Slot('QVariant')
    def pushPrimaryToController(self, controller) -> None:
        """Push primary state to a controller."""
        self._push_state_to_controller(self._primary, controller)

    @Slot('QVariant')
    def pushSecondaryToController(self, controller) -> None:
        """Push secondary state to a controller."""
        self._push_state_to_controller(self._secondary, controller)

    # ------------------------------------------------------------------ #
    #  Internal helpers used by other controllers                         #
    # ------------------------------------------------------------------ #

    def get_primary_df(self) -> Optional[pd.DataFrame]:
        """Return the primary DataFrame."""
        return self._primary.df

    def get_secondary_df(self) -> Optional[pd.DataFrame]:
        """Return the secondary DataFrame."""
        return self._secondary.df

    @Slot('QVariant', str)
    def syncTypesFromController(self, controller, which: str = "") -> None:
        """Sync user-selected types from a controller into a dataset state.

        Args:
            controller: CSVController or ARFFController instance.
            which: 'primary' or 'secondary'. If empty, uses loadingTarget.
        """
        if controller is None:
            return

        if which == 'primary':
            target = self._primary
        elif which == 'secondary':
            target = self._secondary
        else:
            target = self._secondary if self._loading_target == 'secondary' else self._primary

        if not self._sync.sync_types_from_controller(target, controller):
            return

        if target is self._secondary:
            self.secondaryBaseChanged.emit()
        else:
            self.primaryBaseChanged.emit()
        self.canMergeChanged.emit()

    def update_primary_types(self, selected_types: Dict[str, str]) -> None:
        """Update selected types for the primary dataset."""
        self._primary.selected_types = selected_types.copy()
        self._primary.arff_attributes = build_arff_attributes(self._primary)
        self._primary.is_preprocessed = True
        self.primaryBaseChanged.emit()
        self.canMergeChanged.emit()

    def update_secondary_types(self, selected_types: Dict[str, str]) -> None:
        """Update selected types for the secondary dataset."""
        self._secondary.selected_types = selected_types.copy()
        self._secondary.arff_attributes = build_arff_attributes(self._secondary)
        self._secondary.is_preprocessed = True
        self.secondaryBaseChanged.emit()
        self.canMergeChanged.emit()
