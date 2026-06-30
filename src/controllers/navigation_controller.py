"""Centralized navigation controller for DataNexus."""

from enum import Enum, auto
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, Slot, Property


class AppPage(Enum):
    """Available application pages."""
    LOAD = auto()
    PREPROCESS = auto()
    HUB = auto()
    VIEW = auto()
    MERGE = auto()


class NavigationContext(Enum):
    """Navigation context — origin and destination of a transition."""
    INITIAL_LOAD = auto()
    HUB_LOAD_PRIMARY = auto()
    HUB_LOAD_SECONDARY = auto()
    HUB_TO_VIEW = auto()
    HUB_TO_MERGE = auto()
    MERGE_COMPLETE = auto()
    PREPROCESS_COMPLETE = auto()


class NavigationController(QObject):
    """Centralized navigation controller.

    Manages the navigation state machine and emits signals
    for QML page transitions.
    """
    
    navigateToLoad = Signal()
    navigateToPreprocess = Signal('QVariantMap')
    navigateToHub = Signal('QVariantMap')
    navigateToView = Signal('QVariantMap')
    navigateToMerge = Signal('QVariantMap')
    
    contextChanged = Signal()
    canMergeChanged = Signal()
    
    replaceWithHub = Signal('QVariantMap')
    popNavigation = Signal()
    popToHub = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = AppPage.LOAD
        self._context = NavigationContext.INITIAL_LOAD
        self._navigation_params: Dict[str, Any] = {}
        
        self._state_manager = None
        
        self._is_navigating = False
        self._pending_navigation = None
    
    @Property(str, notify=contextChanged)
    def currentContext(self) -> str:
        """Current context as a string for QML."""
        return self._context.name
    
    @Property(bool, notify=contextChanged)
    def isLoadingSecondary(self) -> bool:
        """Whether the secondary dataset is being loaded."""
        return self._context == NavigationContext.HUB_LOAD_SECONDARY
    
    @Property(bool, notify=contextChanged)
    def isInitialLoad(self) -> bool:
        """Whether this is the initial load."""
        return self._context == NavigationContext.INITIAL_LOAD
    
    @Property(bool, notify=contextChanged)
    def isMergeFlow(self) -> bool:
        """Whether the current flow is a merge operation."""
        return self._context in [
            NavigationContext.HUB_TO_MERGE,
            NavigationContext.MERGE_COMPLETE
        ]
    
    @Slot('QVariant')
    def setStateManager(self, state_manager) -> None:
        """Injects a reference to the StateManager."""
        self._state_manager = state_manager
    
    @Slot(str)
    def onDataLoaded(self, file_type: str) -> None:
        """Called when a file is loaded successfully. Navigates based on context."""
        if self._is_navigating:
            self._pending_navigation = ('data_loaded', file_type)
            return
        
        self._is_navigating = True
        
        try:
            params = {
                'fileType': file_type,
                'context': self._context.name,
                'isSecondaryBase': self._context == NavigationContext.HUB_LOAD_SECONDARY,
                'isInitialLoad': self._context == NavigationContext.INITIAL_LOAD,
                'returnToHub': self._context in [
                    NavigationContext.HUB_LOAD_PRIMARY,
                    NavigationContext.HUB_LOAD_SECONDARY
                ]
            }
            
            self.navigateToPreprocess.emit(params)
            self._current_page = AppPage.PREPROCESS
            
        finally:
            self._is_navigating = False
    
    @Slot(bool)
    def onPreprocessComplete(self, saved_to_disk: bool) -> None:
        """Called when preprocessing is complete. Navigates based on context."""
        if self._is_navigating:
            return
        
        self._is_navigating = True
        
        try:
            params = {
                'savedToDisk': saved_to_disk
            }
            
            if self._context == NavigationContext.INITIAL_LOAD:
                # Replace to clear navigation stack
                self._context = NavigationContext.PREPROCESS_COMPLETE
                self.contextChanged.emit()
                self.replaceWithHub.emit(params)
                self._current_page = AppPage.HUB
                
            elif self._context == NavigationContext.HUB_LOAD_PRIMARY:
                self._context = NavigationContext.PREPROCESS_COMPLETE
                self.contextChanged.emit()
                self.popNavigation.emit()
                self._current_page = AppPage.HUB
                
            elif self._context == NavigationContext.HUB_LOAD_SECONDARY:
                self._context = NavigationContext.PREPROCESS_COMPLETE
                self.contextChanged.emit()
                self.popNavigation.emit()
                self._current_page = AppPage.HUB
                
            elif self._context == NavigationContext.MERGE_COMPLETE:
                self._context = NavigationContext.PREPROCESS_COMPLETE
                self.contextChanged.emit()
                self.popToHub.emit()
                self._current_page = AppPage.HUB
                
            else:
                # Fallback
                self.popNavigation.emit()
                
        finally:
            self._is_navigating = False
    
    @Slot()
    def startLoadPrimary(self) -> None:
        """Starts the flow to load a new primary dataset."""
        self._context = NavigationContext.HUB_LOAD_PRIMARY
        self.contextChanged.emit()
    
    @Slot()
    def startLoadSecondary(self) -> None:
        """Starts the flow to load a secondary dataset."""
        self._context = NavigationContext.HUB_LOAD_SECONDARY
        self.contextChanged.emit()
    
    @Slot()
    def goToView(self) -> None:
        """Navigates to the view page."""
        if self._is_navigating:
            return
        
        self._is_navigating = True
        self._context = NavigationContext.HUB_TO_VIEW
        self.contextChanged.emit()
        
        try:
            params = {
                'context': self._context.name
            }
            self.navigateToView.emit(params)
            self._current_page = AppPage.VIEW
        finally:
            self._is_navigating = False
    
    @Slot()
    def goToMerge(self) -> None:
        """Navigates to the merge page."""
        if self._is_navigating:
            return
        
        self._is_navigating = True
        self._context = NavigationContext.HUB_TO_MERGE
        self.contextChanged.emit()
        
        try:
            params = {
                'context': self._context.name
            }
            self.navigateToMerge.emit(params)
            self._current_page = AppPage.MERGE
        finally:
            self._is_navigating = False
    
    @Slot()
    def onMergeExecuted(self) -> None:
        """Called after a successful merge. Navigates to preprocess."""
        if self._is_navigating:
            return
        
        self._is_navigating = True
        self._context = NavigationContext.MERGE_COMPLETE
        self.contextChanged.emit()
        
        try:
            params = {
                'fileType': 'arff',  # Merge always produces ARFF
                'context': self._context.name,
                'isSecondaryBase': False,
                'isInitialLoad': False,
                'isMergeResult': True,
                'returnToHub': True
            }
            self.navigateToPreprocess.emit(params)
            self._current_page = AppPage.PREPROCESS
        finally:
            self._is_navigating = False
    
    @Slot()
    def onViewComplete(self) -> None:
        """Called when leaving the view page."""
        if self._is_navigating:
            return
        
        self._is_navigating = True
        try:
            self.popNavigation.emit()
            self._current_page = AppPage.HUB
            self._context = NavigationContext.PREPROCESS_COMPLETE
            self.contextChanged.emit()
        finally:
            self._is_navigating = False
    
    @Slot()
    def cancelNavigation(self) -> None:
        """Cancels ongoing navigation and returns to the hub."""
        self._context = NavigationContext.PREPROCESS_COMPLETE
        self.contextChanged.emit()
        self.popToHub.emit()
        self._current_page = AppPage.HUB
    
    @Slot()
    def resetToInitial(self) -> None:
        """Resets the navigation state to initial."""
        self._context = NavigationContext.INITIAL_LOAD
        self._current_page = AppPage.LOAD
        self._is_navigating = False
        self._pending_navigation = None
        self.contextChanged.emit()
