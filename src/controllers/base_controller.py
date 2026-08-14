"""QML facade for operations shared by the file controllers."""

from typing import Dict, List

from PySide6.QtCore import QObject, Slot

from services.analysis_service import DataAnalysisService


class BaseDataController(QObject):
    """Expose analysis operations to QML without owning their implementation.

    Concrete controllers provide the current DataFrame and the selected column
    types. ``DataAnalysisService`` performs the pandas/NumPy/Matplotlib work.
    """

    def __init__(self) -> None:
        super().__init__()
        self._analysis = DataAnalysisService(self)

    @Slot(str, str, result='QVariantMap')
    def validateTypeConversion(self, attribute_name: str, new_type: str) -> Dict:
        return self._analysis.validateTypeConversion(attribute_name, new_type)

    @Slot(str, result='QVariantMap')
    def getColumnStatistics(self, attribute_name: str) -> Dict:
        return self._analysis.getColumnStatistics(attribute_name)

    @Slot(str, int, result=str)
    def generateChartImage(self, attribute_name: str, bins: int = 10) -> str:
        return self._analysis.generateChartImage(attribute_name, bins)

    @Slot(str, int, int, int, result=str)
    def generateChartImageSized(
        self,
        attribute_name: str,
        bins: int,
        width_px: int,
        height_px: int,
    ) -> str:
        return self._analysis.generateChartImageSized(
            attribute_name, bins, width_px, height_px
        )

    @Slot(str, int, result=str)
    def generateChartSvg(self, attribute_name: str, bins: int = 10) -> str:
        return self._analysis.generateChartSvg(attribute_name, bins)

    @Slot(str, int, result='QVariantList')
    def getHistogramData(self, attribute_name: str, bins: int = 10) -> List:
        return self._analysis.getHistogramData(attribute_name, bins)

    @Slot(str, int, result='QVariantMap')
    def getHistogramChartData(self, attribute_name: str, bins: int = 10) -> Dict:
        return self._analysis.getHistogramChartData(attribute_name, bins)

    @Slot(str, result='QVariantList')
    def getBarChartData(self, attribute_name: str) -> List:
        return self._analysis.getBarChartData(attribute_name)

    @Slot(str, result='QVariantList')
    def getNominalClassCounts(self, attribute_name: str) -> List:
        return self._analysis.getNominalClassCounts(attribute_name)

    @Slot(str, str, int, result=str)
    def generateStackedChart(
        self,
        primary_attribute: str,
        class_attribute: str,
        bins: int = 10,
    ) -> str:
        return self._analysis.generateStackedChart(
            primary_attribute, class_attribute, bins
        )

    @Slot(str, str, int, result='QVariantMap')
    def getStackedHistogramData(
        self,
        primary_attribute: str,
        class_attribute: str,
        bins: int = 10,
    ) -> Dict:
        return self._analysis.getStackedHistogramData(
            primary_attribute, class_attribute, bins
        )
