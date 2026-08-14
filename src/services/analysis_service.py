"""Qt-independent facade for analysis-related services."""

from typing import Dict, List

from .chart_service import ChartService
from .statistics_service import StatisticsService
from .type_validation_service import TypeValidationService


class DataAnalysisService:
    """Compose focused services used by the QML-facing data controllers."""

    def __init__(self, data_provider) -> None:
        self._validation = TypeValidationService(data_provider)
        self._statistics = StatisticsService(data_provider)
        self._charts = ChartService(data_provider)

    def validateTypeConversion(self, attribute_name: str, new_type: str) -> Dict:
        return self._validation.validate(attribute_name, new_type)

    def getColumnStatistics(self, attribute_name: str) -> Dict:
        return self._statistics.get_column_statistics(attribute_name)

    def generateChartImage(self, attribute_name: str, bins: int = 10) -> str:
        return self._charts.generateChartImage(attribute_name, bins)

    def generateChartImageSized(
        self,
        attribute_name: str,
        bins: int,
        width_px: int,
        height_px: int,
    ) -> str:
        return self._charts.generateChartImageSized(
            attribute_name, bins, width_px, height_px
        )

    def generateChartSvg(self, attribute_name: str, bins: int = 10) -> str:
        return self._charts.generateChartSvg(attribute_name, bins)

    def getHistogramData(self, attribute_name: str, bins: int = 10) -> List:
        return self._charts.getHistogramData(attribute_name, bins)

    def getHistogramChartData(self, attribute_name: str, bins: int = 10) -> Dict:
        return self._charts.getHistogramChartData(attribute_name, bins)

    def getBarChartData(self, attribute_name: str) -> List:
        return self._charts.getBarChartData(attribute_name)

    def getNominalClassCounts(self, attribute_name: str) -> List:
        return self._charts.getNominalClassCounts(attribute_name)

    def generateStackedChart(
        self,
        primary_attribute: str,
        class_attribute: str,
        bins: int = 10,
    ) -> str:
        return self._charts.generateStackedChart(
            primary_attribute, class_attribute, bins
        )

    def getStackedHistogramData(
        self,
        primary_attribute: str,
        class_attribute: str,
        bins: int = 10,
    ) -> Dict:
        return self._charts.getStackedHistogramData(
            primary_attribute, class_attribute, bins
        )
