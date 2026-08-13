"""DataNexus — Desktop app for CSV/ARFF dataset manipulation and merging."""

import sys
import os
import logging

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from PySide6.QtCore import QObject, Signal, Slot, Property, QTranslator, QLocale
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from controllers.csv_controller import CSVController
from controllers.arff_controller import ARFFController
from controllers.state_controller import StateController
from controllers.navigation_controller import NavigationController

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")


class LanguageManager(QObject):
    """Manages runtime language switching via QTranslator."""

    languageChanged = Signal()

    _LANGUAGES = [
        {"code": "br", "name": "Português"},
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Español"},
    ]

    def __init__(self, engine: QQmlApplicationEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._translator = QTranslator(self)
        self._current = "en"
        self._ts_dir = os.path.join(ROOT_DIR, "resources", "translations")

        # English is the source language — no translator needed at startup

    @Property(str, notify=languageChanged)
    def currentLanguage(self) -> str:
        """Active language code."""
        return self._current

    @Property(list, constant=True)
    def languages(self) -> list:
        """Available language descriptors [{code, name}]."""
        return self._LANGUAGES

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        """Switch the application language at runtime."""
        if code == self._current:
            return
        app = QApplication.instance()
        app.removeTranslator(self._translator)

        # English is the source language — no translator needed
        if code != "en":
            self._translator = QTranslator(self)
            qm = os.path.join(self._ts_dir, f"datanexus_{code}.qm")
            if self._translator.load(qm):
                app.installTranslator(self._translator)

        self._current = code
        self.languageChanged.emit()
        self._engine.retranslate()


def main() -> int:
    """Initialize the Qt application and load the QML UI."""
    app = QApplication(sys.argv)

    qmlRegisterType(CSVController, "App", 1, 0, "CSVController")
    qmlRegisterType(ARFFController, "App", 1, 0, "ARFFController")
    qmlRegisterType(StateController, "App", 1, 0, "StateController")
    qmlRegisterType(NavigationController, "App", 1, 0, "NavigationController")

    engine = QQmlApplicationEngine()

    lang_manager = LanguageManager(engine)
    engine.rootContext().setContextProperty("languageManager", lang_manager)

    qml_dir = os.path.join(ROOT_DIR, "qml")
    engine.addImportPath(qml_dir)
    engine.load(os.path.join(qml_dir, "main.qml"))

    if not engine.rootObjects():
        print("Error: failed to load QML UI.")
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
