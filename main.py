"""DataNexus — Desktop app for CSV/ARFF dataset manipulation and merging."""

import sys
import os
import logging
import xml.etree.ElementTree as ET

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


class TsTranslator(QTranslator):
    """Small runtime fallback for source translations when .qm is unavailable.

    The repository keeps the editable .ts catalogs under version control while
    compiled .qm files are ignored. Loading the .ts directly keeps language
    switching functional in a fresh checkout as well as in packaged builds.
    """

    def __init__(self, ts_path: str, parent=None):
        super().__init__(parent)
        self._translations: dict[tuple[str, str], str] = {}

        root = ET.parse(ts_path).getroot()
        for context in root.findall("context"):
            context_name = context.findtext("name", "")
            for message in context.findall("message"):
                source = message.findtext("source", "")
                translation_node = message.find("translation")
                translation = (
                    translation_node.text.strip()
                    if translation_node is not None and translation_node.text
                    else ""
                )

                # Empty/unfinished entries should fall back to the source text.
                if source and translation and translation_node.get("type") != "unfinished":
                    self._translations[(context_name, source)] = translation

    def translate(
        self,
        context: str,
        source_text: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        del disambiguation, n
        return self._translations.get((context or "", source_text or ""), "")


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
        self._translator = None
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

        supported_codes = {language["code"] for language in self._LANGUAGES}
        if code not in supported_codes:
            logging.warning("Unsupported language requested: %s", code)
            return

        app = QApplication.instance()

        new_translator = None
        # English is the source language — no translator needed.
        if code != "en":
            qm = os.path.join(self._ts_dir, f"datanexus_{code}.qm")
            if os.path.isfile(qm):
                candidate = QTranslator(self)
                if candidate.load(qm):
                    new_translator = candidate

            # .qm files are intentionally ignored by git. Use the editable
            # catalog when the project is run from a fresh checkout.
            if new_translator is None:
                ts = os.path.join(self._ts_dir, f"datanexus_{code}.ts")
                if os.path.isfile(ts):
                    try:
                        new_translator = TsTranslator(ts, self)
                    except (ET.ParseError, OSError) as exc:
                        logging.warning("Could not load translation %s: %s", code, exc)

            if new_translator is None:
                logging.warning("Translation catalog not found for language: %s", code)
                return

        if self._translator is not None:
            app.removeTranslator(self._translator)

        if new_translator is not None:
            app.installTranslator(new_translator)

        self._translator = new_translator
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
