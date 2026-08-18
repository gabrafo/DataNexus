# DataNexus

Desktop application for loading, visualizing, preprocessing, and merging datasets in CSV and ARFF formats. Built with Python, PySide6, and QML.

## Features

- **Data loading** — CSV and ARFF files with automatic delimiter / type detection
- **Auto-typification** — Types inferred automatically for CSV; manual typification also available via "Typify" action
- **Visualization** — Paginated tables with horizontal/vertical scroll, column/row deletion, statistics, and charts (histograms, stacked bars)
- **Merge** — Combine two datasets using different JOIN strategies (inner, left, right, cross); explicit column mapping with type-compatibility validation
- **Export** — Save results to CSV or ARFF
- **Internationalization** — UI available in Portuguese (default), English, and Spanish; switchable at runtime

A demonstration video is available at repo root.

## Project Structure

```
IC/
├── main.py                           # Application entry point + LanguageManager
├── requirements.txt
├── README.md
│
├── src/                              # Python source code
│   ├── models/                       # Data layer
│   │   ├── dataset.py              # Dataset + type inference utilities
│   │   └── dataframe_adapter.py               # QAbstractTableModel for QML TableView
│   ├── services/                     # Business logic (Qt-free)
│   │   ├── arff_file_service.py      # ARFF parsing
│   │   ├── arff_writer_service.py    # ARFF serialization for file controllers
│   │   ├── analysis_service.py       # Facade for analysis services
│   │   ├── chart_service.py          # Chart rendering and chart data
│   │   ├── column_type_service.py    # Type suggestions and validation helpers
│   │   ├── csv_file_service.py       # CSV parsing and delimiter detection
│   │   ├── dataset_sync_service.py   # Controller ↔ Dataset synchronization
│   │   ├── merge_mapping_service.py  # Merge-key mapping and compatibility
│   │   ├── merge_service.py          # Merge verification, preview, execution
│   │   ├── serialization_service.py  # Save to CSV / ARFF
│   │   ├── statistics_service.py     # Descriptive statistics
│   │   └── type_validation_service.py # Safe type-conversion checks
│   └── controllers/                  # QML-facing controllers
│       ├── base_controller.py            # QML facade for shared analysis
│       ├── csv_controller.py             # CSV operations
│       ├── arff_controller.py            # ARFF operations
│       ├── state_controller.py              # Central state facade (QML ↔ services)
│       └── navigation_controller.py      # Page navigation state machine
│
├── qml/                              # User interface (QML / Qt Quick)
│   ├── main.qml                          # Main window + StackView
│   ├── components/                       # Reusable UI components
│   │   ├── Theme.qml                        # Design tokens (type scale, spacing, radii)
│   │   ├── ActionCard.qml                   # Clickable card with icon + title
│   │   ├── SectionCard.qml                  # Titled panel container
│   │   ├── StandardDialog.qml               # Modal dialog with primary/secondary actions
│   │   └── qmldir                           # Module manifest
│   └── pages/
│       ├── page_hub.qml                     # Central hub (dataset slots + actions)
│       ├── page_load.qml                    # Splash / file picker
│       ├── page_view.qml                    # Data table viewer
│       ├── page_merge.qml                   # Merge configuration & preview
│       └── page_preprocess.qml              # Type selection & chart visualization
│
└── resources/
    ├── data/                             # Sample datasets for testing
    └── translations/                     # i18n (Qt Linguist)
        ├── datanexus_br.ts / .qm                # Portuguese (pt-BR)
        └── datanexus_es.ts / .qm                # Spanish
```

## Getting Started

### Requirements

- Python 3.10+
- Qt 6.x (bundled with PySide6)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| PySide6 | 6.x | Qt framework — QML UI, signals/slots, models |
| pandas | 2.x | DataFrame manipulation, merge, export |
| numpy | 1.x | Numeric computation (histograms, bins, statistics) |
| liac-arff | 2.x | ARFF file I/O (Weka format) |
| matplotlib | 3.x | Chart generation (histograms, stacked bars) |

## The Role of ARFF in DataNexus

The **ARFF** (Attribute-Relation File Format) standard is a cornerstone of this project. Created by the [Weka](https://www.cs.waikato.ac.nz/ml/weka/) machine-learning workbench at the University of Waikato, ARFF enriches tabular data with explicit **type metadata** for every column — each `@ATTRIBUTE` declaration states whether a column is `NUMERIC`, `STRING`, `DATE`, or a list of nominal values. This metadata is what makes type-safe merging possible: DataNexus can validate that two columns are compatible *before* joining them.

### How CSV uses ARFF under the hood

CSV files carry no type information — every value is plain text. When a CSV is loaded, DataNexus transparently applies the same type categories used by ARFF through the `infer_types_from_df()` function in `dataset.py`:

1. **Numeric** — columns whose pandas dtype is numeric.
2. **Nominal** — low-cardinality string columns (≤ 10 unique values, < 10 % of total rows).
3. **Date** — columns already represented in memory with a `datetime64` dtype; in the current CSV loading flow, date-like text values usually remain textual until manually typified.
4. **Textual** — everything else (free-form strings).

The result is a `selected_types` dictionary and an `arff_attributes` list stored in `Dataset` — the exact same structures used when loading a native ARFF file. From that point on, every downstream operation (column mapping, type-compatibility checks, merge execution, and serialization) works identically regardless of the original file format.

In short, **ARFF provides the type system** and **CSV data is promoted into it automatically**, giving users a seamless experience while preserving the type safety required for reliable dataset merging.

## Architecture

The application follows an **MVC + Services** pattern:

- **Models** (`Dataset`, `DataFrameAdapter`) — `Dataset` stores data and metadata, while `DataFrameAdapter` adapts a pandas `DataFrame` for display in QML.
- **Services** (`MergeService`, `DatasetSyncService`, `DataAnalysisService`, `SerializationService`) — cohesive business logic with no Qt dependency.
- **Controllers** (`StateController`, `CSVController`, `ARFFController`, `NavigationController`) — QML-facing layer exposing `@Slot` / `Property` for the UI.

The controllers act as facades: they expose Qt properties and signals, while analysis, type handling, synchronization, mapping, merging, and serialization remain in focused services. `StateController` owns two `Dataset` instances and coordinates those services.

### Column Mapping for Merge

| Scenario | Available JOIN options |
|----------|----------------------|
| No mappings | Only "All data from both" (cross join) |
| With mappings | 3 options (inner, left, right) |

### Type Compatibility

| Base 1 | Base 2 | Compatible |
|--------|--------|------------|
| Numeric | Numeric | ✅ |
| Textual | Textual | ✅ |
| Textual | Nominal | ✅ |
| Nominal | Nominal | ✅ |
| Date | Date | ✅ |
| Numeric | Textual | ❌ |
| Date | Numeric | ❌ |
