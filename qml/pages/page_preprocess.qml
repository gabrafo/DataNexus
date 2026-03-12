pragma ComponentBehavior: Bound
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtQuick.Window 2.15
import QtCharts
import "../components"

/**
 * PagePreprocess - Attribute type assignment page.
 * Column type selection with statistics, charts, and type validation.
 * Saves in memory on confirm; optionally exports to disk.
 */
Page {
    id: typePage
    
    property var csvController: null
    property var arffController: null
    property var stateManager: null
    property var navController: null
    property var stack: null
    property string fileType: "csv"
    
    // Flags simplificadas para fluxo
    property bool isSecondaryBase: false
    property bool isInitialLoad: false
    property bool isMergeResult: false
    property bool returnToHub: true
    
    property var activeController: fileType === "csv" ? csvController : arffController
    
    property string selectedColumnForVisualization: ""
    property var stackedData: null
    property var lastChartData: null
    property var activeQtSeries: null
    // Histogram bin count (1-25)
    property int histogramBins: 10
    
    // Refresh chart (supports stacking by nominal attribute)
    function refreshChart() {
        if (!typePage.activeController)
            return

        var primary = typePage.selectedColumnForVisualization
        var stackBy = (typeof stackBySelector !== 'undefined' && stackBySelector && stackBySelector.visible && stackBySelector.currentText && stackBySelector.currentIndex > 0)
            ? stackBySelector.currentText
            : ""
        var bins = (typeof typePage.histogramBins === 'number') ? Math.max(1, Math.min(25, typePage.histogramBins)) : 10

        if (!primary) {
            typePage.stackedData = null
            if (typeof chartView !== 'undefined') {
                chartView.visible = false
            }
            return
        }

        // Stacked bar chart using a nominal attribute
        if (stackBy) {
            try {
                var data = typePage.activeController.getStackedHistogramData(primary, stackBy, bins)
                if (data && Object.keys(data).length > 0) {
                    typePage.stackedData = data
                    if (typeof chartView !== 'undefined') {
                        chartView.visible = true
                        chartView.xAxis.categories = (data.binLabels && data.binLabels.length) ? data.binLabels : []

                        // Reset both series and show the stacked one
                        simpleSeries.visible = false
                        stackedSeries.visible = true
                        simpleSeries.clear()
                        stackedSeries.clear()

                        // Build sets per class (AbstractBarSeries.append(label, values))
                        for (var c = 0; c < data.classNames.length; c++) {
                            var label = String(data.classNames[c])
                            var values = []
                            for (var b = 0; b < data.counts[c].length; b++)
                                values.push(Number(data.counts[c][b]))
                            var bs = stackedSeries.append(label, values)
                            // Force visible colors on dark backgrounds
                            if (bs) {
                                var pal = (typeof chartAreaColumn !== 'undefined' && chartAreaColumn.chartPalette) ? chartAreaColumn.chartPalette : []
                                bs.color = (pal.length > 0) ? pal[c % pal.length] : Material.accent
                                bs.borderColor = Material.backgroundColor
                                bs.borderWidth = 1
                            }
                        }

                        typePage.activeQtSeries = stackedSeries
                        chartView.yAxis.max = chartView.computeYAxisMaxFromStacked(data)
                        chartView.yAxis.min = 0
                        chartView.title = 'Histograma - ' + primary
                        chartView.legend.visible = true
                        chartView.legend.alignment = Qt.AlignBottom
                    }
                    return
                }
            } catch (e) {
                console.log('Erro ao obter dados empilhados:', e)
            }
        }

        // Simple bar chart (no stacking)
        try {
            var d = typePage.activeController.getHistogramChartData(primary, bins)
            typePage.stackedData = null
            typePage.lastChartData = d
            if (typeof chartView !== 'undefined') {
                chartView.visible = true
                chartView.legend.visible = false

                console.log('QML: chart data', primary, 'labels=', (d && d.labels) ? d.labels.length : 0, 'counts=', (d && d.counts) ? d.counts.length : 0)

                chartView.xAxis.categories = (d.labels && d.labels.length) ? d.labels : []

                // Reset both series and show the simple one
                stackedSeries.visible = false
                simpleSeries.visible = true
                stackedSeries.clear()
                simpleSeries.clear()

                var values2 = []
                for (var i = 0; i < d.counts.length; i++)
                    values2.push(Number(d.counts[i]))
                var bs2 = simpleSeries.append(String(primary), values2)
                if (bs2) {
                    bs2.color = Material.accent
                    bs2.borderColor = Material.backgroundColor
                    bs2.borderWidth = 1
                }

                typePage.activeQtSeries = simpleSeries
                chartView.yAxis.max = chartView.computeYAxisMaxFromCounts(d.counts)
                chartView.yAxis.min = 0
                chartView.title = (d.isNumeric ? 'Histograma - ' : 'Distribuição - ') + primary
            }
        } catch (e2) {
            console.log('Erro ao gerar chart data:', e2, e2 && e2.stack ? e2.stack : '')
            if (typeof chartView !== 'undefined') chartView.visible = false
        }
    }
    
    background: Rectangle {
        color: Material.backgroundColor
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24
        
        // Left panel - Attribute list
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.5
            color: Material.backgroundColor
            border.color: Material.frameColor
            border.width: 1
            radius: 8
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                
                Text {
                    text: qsTr("Selecting types")
                    font.pointSize: 19
                    font.weight: Font.Medium
                    color: Material.foreground
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Text {
                    text: qsTr("We suggest a type for each attribute. You can change them, but only now.")
                    font.pointSize: 10
                    color: Material.foreground
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    Layout.topMargin: 4
                }
                
                Text {
                    text: qsTr("• Nominal: predefined categorical values\n• Numeric: continuous or discrete numerical values\n• String: free text without a specific format\n• Date: date/time values")
                    font.pointSize: 9
                    color: Material.foreground
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    lineHeight: 1.3
                }
                
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    
                    ColumnLayout {
                        width: parent.width - 20
                        spacing: 12
                        
                        Repeater {
                            id: attributeRepeater
                            model: {
                                if (typePage.activeController) {
                                    var names = typePage.activeController.getAttributeNames()
                                    return names ? names.length : 0
                                }
                                return 0
                            }
                            
                            delegate: Rectangle {
                                id: attributeItem
                                required property int index
                                Layout.fillWidth: true
                                Layout.preferredHeight: attributeColumn.implicitHeight + 20
                                color: Material.backgroundColor
                                border.color: Material.frameColor
                                border.width: 1
                                radius: 6
                                
                                property string attrName: {
                                    if (typePage.activeController) {
                                        var names = typePage.activeController.getAttributeNames()
                                        return names && attributeItem.index < names.length ? names[attributeItem.index] : ""
                                    }
                                    return ""
                                }
                                
                                ColumnLayout {
                                    id: attributeColumn
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    
                                    Text {
                                        text: attributeItem.attrName || (qsTr("Column ") + (attributeItem.index + 1))
                                        font.pointSize: 13
                                        font.weight: Font.DemiBold
                                        color: Material.foreground
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    
                                    RowLayout {
                                        spacing: 10
                                        Layout.fillWidth: true
                                        
                                        Text {
                                            text: qsTr("Type:")
                                            font.pointSize: 11
                                            color: Material.foreground
                                            opacity: 0.8
                                        }

                                        ComboBox {
                                            id: typeCombo
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 32
                                            
                                            model: ['Numeric', 'String', 'Nominal', 'Date']
                                            
                                            property bool initialized: false
                                            property int previousValidIndex: -1
                                            property bool reverting: false

                                            Component.onCompleted: {
                                                if (typePage.activeController && attributeItem.attrName) {
                                                    var suggested = typePage.activeController.getSuggestedType(attributeItem.attrName)
                                                    for (var i = 0; i < model.length; i++) {
                                                        if (model[i] === suggested) {
                                                            currentIndex = i
                                                            previousValidIndex = i
                                                            break
                                                        }
                                                    }
                                                    initialized = true
                                                }
                                            }

                                            onCurrentIndexChanged: {
                                                // Skip during init or revert
                                                if (!initialized || reverting) {
                                                    return
                                                }
                                                
                                                if (!typePage.activeController || !attributeItem.attrName || currentIndex < 0) {
                                                    return
                                                }
                                                
                                                var newType = model[currentIndex]
                                                
                                                var validation = typePage.activeController.validateTypeConversion(
                                                    attributeItem.attrName, 
                                                    newType
                                                )
                                                
                                                if (validation.valid) {
                                                    typePage.activeController.setAttributeType(attributeItem.attrName, newType)
                                                    previousValidIndex = currentIndex
                                                    console.log("QML: Tipo alterado para '" + attributeItem.attrName + "': " + newType)
                                                } else {
                                                    // Invalid: show error and schedule revert
                                                    validationDialog.attributeName = attributeItem.attrName
                                                    validationDialog.attemptedType = newType
                                                    validationDialog.errorMessage = validation.message
                                                    validationDialog.open()
                                                    
                                                    revertTimer.targetCombo = typeCombo
                                                    revertTimer.targetIndex = previousValidIndex
                                                    revertTimer.start()
                                                }
                                            }
                                            
                                            // Async revert timer
                                            Timer {
                                                id: revertTimer
                                                interval: 1
                                                repeat: false
                                                property var targetCombo: null
                                                property int targetIndex: -1
                                                
                                                onTriggered: {
                                                    if (targetCombo && targetIndex >= 0) {
                                                        targetCombo.reverting = true
                                                        targetCombo.currentIndex = targetIndex
                                                        targetCombo.reverting = false
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    
                                    // Inline value examples
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        
                                        Repeater {
                                            model: {
                                                if (typePage.activeController && attributeItem.attrName) {
                                                    var examples = typePage.activeController.getAttributeExamples(attributeItem.attrName)
                                                    return examples ? Math.min(examples.length, 5) : 0
                                                }
                                                return 0
                                            }
                                            
                                            delegate: Rectangle {
                                                id: exampleItem
                                                required property int index
                                                width: Math.min(exText.implicitWidth + 12, 100)
                                                height: 22
                                                color: Qt.darker(Material.backgroundColor, 1.15)
                                                border.color: Material.frameColor
                                                border.width: 1
                                                radius: 3
                                                
                                                Text {
                                                    id: exText
                                                    anchors.centerIn: parent
                                                    text: {
                                                        if (typePage.activeController && attributeItem.attrName) {
                                                            var examples = typePage.activeController.getAttributeExamples(attributeItem.attrName)
                                                            return examples && exampleItem.index < examples.length ? examples[exampleItem.index] : ""
                                                        }
                                                        return ""
                                                    }
                                                    font.pointSize: 9
                                                    color: Material.foreground
                                                    elide: Text.ElideRight
                                                    width: parent.width - 8
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 50
                    spacing: 10

                    Button {
                        text: qsTr("Back")
                        Material.foreground: "#FFFFFF"
                        font.weight: Font.Medium
                        Layout.preferredWidth: 140
                        Layout.preferredHeight: 40
                        onClicked: {
                            if (typePage.stack) {
                                typePage.stack.pop()
                            }
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        text: qsTr("Confirm")
                        Material.background: Material.accent
                        Material.foreground: "#000000"
                        font.weight: Font.Medium
                        Layout.preferredWidth: 140
                        Layout.preferredHeight: 40
                        onClicked: {
                            // Mark as preprocessed in memory
                            if (typePage.stateManager) {
                                if (typePage.isSecondaryBase) {
                                    typePage.stateManager.markSecondaryAsPreprocessed()
                                } else {
                                    typePage.stateManager.markPrimaryAsPreprocessed()
                                }
                            }
                            
                            saveToDiskDialog.open()
                        }
                    }
                }
            }
        }
        
        // Right panel - Visualization
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.5
            color: Material.backgroundColor
            border.color: Material.frameColor
            border.width: 1
            radius: 8
            
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                
                Text {
                    text: qsTr("Visualization")
                    font.pointSize: 19
                    font.weight: Font.Medium
                    color: Material.foreground
                    Layout.alignment: Qt.AlignHCenter
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70
                    color: Material.backgroundColor
                    border.color: Material.frameColor
                    border.width: 1
                    radius: 8
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        
                        Text {
                            text: qsTr("Select a column")
                            font.pointSize: 11
                            font.weight: Font.Medium
                            color: Material.foreground
                            Layout.fillWidth: true
                        }
                        
                        ComboBox {
                            id: columnSelector
                            Layout.fillWidth: true
                            Layout.preferredHeight: 32
                            Layout.maximumWidth: parent.width
                            model: typePage.activeController ? typePage.activeController.getAttributeNames() : []
                            clip: true
                            
                            Component.onCompleted: {
                                if (model && model.length > 0) {
                                    currentIndex = 0
                                }
                            }
                            
                            onCurrentTextChanged: {
                                if (currentText) {
                                    typePage.selectedColumnForVisualization = currentText
                                    console.log("QML: Coluna selecionada:", currentText)
                                    typePage.refreshChart()
                                }
                            }
                        }
                    }
                }
                
                // Column statistics
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    color: Material.backgroundColor
                    border.color: Material.frameColor
                    border.width: 1
                    radius: 8
                    // Hidden for String columns
                    visible: {
                        if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                            return true
                        var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                        return columnType !== "String"
                    }
                    
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        
                        Text {
                            text: {
                                if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                                    return qsTr("Statistics")
                                var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                                return columnType === "Nominal" ? qsTr("Count by Class") : qsTr("Statistics")
                            }
                            font.pointSize: 12
                            font.weight: Font.Medium
                            color: Material.foreground
                            Layout.fillWidth: true
                        }
                        
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            
                            ColumnLayout {
                                width: parent.width
                                spacing: 4
                                
                                // Nominal: class counts
                                Repeater {
                                    id: nominalRepeater
                                    visible: {
                                        if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                                            return false
                                        var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                                        return columnType === "Nominal"
                                    }
                                    model: {
                                        if (!visible || !typePage.selectedColumnForVisualization || !typePage.activeController)
                                            return []
                                        return typePage.activeController.getNominalClassCounts(typePage.selectedColumnForVisualization)
                                    }
                                    
                                    delegate: RowLayout {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 4
                                        
                                        Text {
                                            text: parent.modelData.class + ":"
                                            font.pointSize: 9
                                            color: Material.foreground
                                            Layout.preferredWidth: 110
                                            elide: Text.ElideRight
                                        }
                                        
                                        Text {
                                            text: String(parent.modelData.count)
                                            font.pointSize: 9
                                            font.weight: Font.Bold
                                            color: Material.accent
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                                
                                // Non-nominal statistics
                                Repeater {
                                    visible: !nominalRepeater.visible
                                    model: {
                                        if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                                            return []
                                        
                                        var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                                        if (columnType === "Nominal")
                                            return []
                                        
                                        var stats = typePage.activeController.getColumnStatistics(typePage.selectedColumnForVisualization)
                                        var result = []
                                        
                                        if (stats.count !== undefined)
                                            result.push({key: "Contagem", value: String(stats.count)})
                                        if (stats.nullCount !== undefined)
                                            result.push({key: "Valores nulos", value: String(stats.nullCount)})
                                        if (stats.min !== undefined)
                                            result.push({key: "Mínimo", value: stats.min.toFixed(2)})
                                        if (stats.max !== undefined)
                                            result.push({key: "Máximo", value: stats.max.toFixed(2)})
                                        if (stats.mean !== undefined)
                                            result.push({key: "Média", value: stats.mean.toFixed(2)})
                                        if (stats.median !== undefined)
                                            result.push({key: "Mediana", value: stats.median.toFixed(2)})
                                        if (stats.std !== undefined)
                                            result.push({key: "Desvio padrão", value: stats.std.toFixed(2)})
                                        if (stats.mode !== undefined)
                                            result.push({key: "Moda", value: String(stats.mode)})
                                        if (stats.uniqueCount !== undefined)
                                            result.push({key: "Valores únicos", value: String(stats.uniqueCount)})
                                        
                                        return result
                                    }
                                    
                                    delegate: RowLayout {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 4
                                        
                                        Text {
                                            text: parent.modelData.key + ":"
                                            font.pointSize: 9
                                            color: Material.foreground
                                            Layout.preferredWidth: 110
                                            elide: Text.ElideRight
                                        }
                                        
                                        Text {
                                            text: parent.modelData.value
                                            font.pointSize: 9
                                            font.weight: Font.Bold
                                            color: Material.accent
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Chart visualization
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 200
                    color: Material.backgroundColor
                    border.color: Material.frameColor
                    border.width: 1
                    radius: 8
                    
                    ColumnLayout {
                        id: chartAreaColumn
                        property var chartPalette: ['#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f','#edc949','#af7aa1','#ff9da7','#9c755f','#bab0ac','#8cd17d','#b6992d']

                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6
                        
                        Text {
                            text: qsTr("Chart")
                            font.pointSize: 12
                            font.weight: Font.Medium
                            color: Material.foreground
                            Layout.fillWidth: true
                            visible: {
                                if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                                    return true
                                var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                                return columnType !== "String"
                            }
                        }

                        // Nominal attribute selector for stacked charts
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 70
                            color: Material.backgroundColor
                            border.color: Material.frameColor
                            border.width: 1
                            radius: 6
                            visible: {
                                if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                                    return false
                                var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                                return columnType !== "String"
                            }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 6

                                Text {
                                    text: qsTr("Stack by (nominal attribute)")
                                    font.pointSize: 11
                                    font.weight: Font.Medium
                                    color: Material.foreground
                                    Layout.fillWidth: true
                                }

                                ComboBox {
                                    id: stackBySelector
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 32
                                    model: typePage.activeController ? (function() {
                                        var names = typePage.activeController.getAttributeNames()
                                        var res = [qsTr("None")]
                                        for (var i = 0; i < names.length; i++) {
                                            try {
                                                if (typePage.activeController.getSuggestedType(names[i]) === 'Nominal')
                                                    res.push(names[i])
                                            } catch (e) {}
                                        }
                                        return res
                                    })() : [qsTr("None")]

                                    currentIndex: 0

                                    onCurrentTextChanged: {
                                        typePage.refreshChart()
                                    }
                                }
                            }
                        }
                        
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            ChartView {
                                id: chartView
                                anchors.fill: parent
                                antialiasing: true
                                backgroundColor: 'transparent'
                                legend.visible: true
                                theme: ChartView.ChartThemeDark
                                visible: false

                                // Track mouse to position tooltip near cursor
                                MouseArea {
                                    id: chartMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.NoButton
                                    onExited: tooltipBox.visible = false
                                }

                                Rectangle {
                                    id: tooltipBox
                                    visible: false
                                    z: 10
                                    radius: 6
                                    color: Qt.darker(Material.backgroundColor, 1.25)
                                    border.color: Material.frameColor
                                    border.width: 1
                                    opacity: 0.95
                                    implicitWidth: tipText.implicitWidth + 18
                                    implicitHeight: tipText.implicitHeight + 14

                                    Text {
                                        id: tipText
                                        anchors.centerIn: parent
                                        color: Material.foreground
                                        font.pointSize: 11
                                        text: ""
                                    }
                                }

                                // Simple tooltip on bar hover
                                ToolTip {
                                    id: chartTip
                                    visible: false
                                    delay: 0
                                    timeout: 0
                                }

                                BarCategoryAxis {
                                    id: axisX
                                    categories: []
                                    labelsAngle: categories.length > 8 ? -45 : 0
                                    labelsColor: 'white'
                                    gridVisible: false
                                }

                                ValueAxis {
                                    id: axisY
                                    min: 0
                                    max: 1
                                    labelsColor: 'white'
                                    gridVisible: true
                                }

                                // Avoid name collision with ChartView.axisX(axisSeries) / axisY(axisSeries) methods
                                property alias xAxis: axisX
                                property alias yAxis: axisY

                                // Series are declared statically for reliable rendering;
                                // we clear() and repopulate on each refresh.
                                BarSeries {
                                    id: simpleSeries
                                    axisX: axisX
                                    axisY: axisY
                                    visible: true
                                }

                                StackedBarSeries {
                                    id: stackedSeries
                                    axisX: axisX
                                    axisY: axisY
                                    visible: false
                                }

                                // Hover -> tooltip (uses series hovered signal + stored data)
                                Connections {
                                    target: typePage.activeQtSeries
                                    function onHovered(status, index, barset) {
                                        if (!status) {
                                            tooltipBox.visible = false
                                            return
                                        }

                                        var label = (chartView.xAxis.categories && index < chartView.xAxis.categories.length)
                                            ? String(chartView.xAxis.categories[index])
                                            : String(index)

                                        // Stacked: show class + count + total
                                        if (typePage.stackedData && typePage.stackedData.classNames) {
                                            var clsLabel = barset ? String(barset.label) : ""
                                            var clsIndex = -1
                                            for (var i = 0; i < typePage.stackedData.classNames.length; i++) {
                                                if (String(typePage.stackedData.classNames[i]) === clsLabel) { clsIndex = i; break }
                                            }

                                            var v = 0
                                            if (clsIndex >= 0 && typePage.stackedData.counts && typePage.stackedData.counts[clsIndex])
                                                v = Number(typePage.stackedData.counts[clsIndex][index])

                                            var total = 0
                                            for (var c = 0; c < typePage.stackedData.counts.length; c++)
                                                total += Number(typePage.stackedData.counts[c][index])

                                            tipText.text = label + "\n" + clsLabel + ": " + String(v) + "\nTotal: " + String(total)
                                        } else if (typePage.lastChartData && typePage.lastChartData.counts) {
                                            var v2 = Number(typePage.lastChartData.counts[index])
                                            tipText.text = label + "\nContagem: " + String(v2)
                                        } else {
                                            tipText.text = label
                                        }

                                        // Position tooltip near cursor, clamped to chart area
                                        var x = chartMouse.mouseX + 12
                                        var y = chartMouse.mouseY + 12
                                        x = Math.min(x, chartView.width - tooltipBox.implicitWidth - 8)
                                        y = Math.min(y, chartView.height - tooltipBox.implicitHeight - 8)
                                        tooltipBox.x = Math.max(8, x)
                                        tooltipBox.y = Math.max(8, y)
                                        tooltipBox.visible = true
                                    }
                                }

                                function computeYAxisMaxFromCounts(counts) {
                                    if (!counts || counts.length === 0) return 1
                                    var m = 0
                                    for (var i = 0; i < counts.length; i++) m = Math.max(m, Number(counts[i]))
                                    return (m <= 0) ? 1 : m
                                }

                                function computeYAxisMaxFromStacked(data) {
                                    if (!data || !data.counts || data.counts.length === 0) return 1
                                    var bins = data.binLabels ? data.binLabels.length : (data.binLefts ? data.binLefts.length : 0)
                                    var m = 0
                                    for (var b = 0; b < bins; b++) {
                                        var s = 0
                                        for (var c = 0; c < data.counts.length; c++) s += Number(data.counts[c][b])
                                        m = Math.max(m, s)
                                    }
                                    return (m <= 0) ? 1 : m
                                }

                                Component.onCompleted: {
                                    // Ensure we render once the ChartView exists
                                    try { typePage.refreshChart() } catch (e) {}
                                }
                            }
                        }
                    }
                }

                // Histogram bin count control
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 48
                    spacing: 8
                    visible: {
                        if (!typePage.selectedColumnForVisualization || !typePage.activeController)
                            return false
                        var columnType = typePage.activeController.getSuggestedType(typePage.selectedColumnForVisualization)
                        return columnType === "Numeric"
                    }

                    Text {
                        text: qsTr("Number of bars:")
                        font.pointSize: 12
                        color: Material.foreground
                        Layout.alignment: Qt.AlignVCenter
                    }

                    RowLayout {
                        Layout.preferredWidth: 220
                        spacing: 8

                        Slider {
                            id: binsSlider
                            from: 1
                            to: 25
                            stepSize: 1
                            value: typePage.histogramBins
                            Layout.fillWidth: true
                            onValueChanged: {
                                var v = Math.round(value)
                                typePage.histogramBins = v
                                // refresh on change (fast but acceptable for small datasets)
                                try { typePage.refreshChart() } catch (e) { console.log('Erro ao atualizar bins (slider):', e) }
                            }
                        }

                        TextField {
                            id: binsInput
                            text: String(typePage.histogramBins)
                            inputMethodHints: Qt.ImhDigitsOnly
                            validator: IntValidator { bottom: 1; top: 25 }
                            placeholderText: "1-25"
                            Layout.preferredWidth: 56
                            onEditingFinished: {
                                var v = parseInt(text)
                                if (isNaN(v)) v = 10
                                v = Math.max(1, Math.min(25, v))
                                typePage.histogramBins = v
                                binsSlider.value = v
                                text = String(v)
                                try { typePage.refreshChart() } catch (e) { console.log('Erro ao atualizar bins (input):', e) }
                            }
                            // Keep the text in sync when histogramBins changed elsewhere
                            Binding {
                                target: binsInput
                                property: "text"
                                value: String(typePage.histogramBins)
                            }
                        }
                    }
                }
            }
        }
    }
    
    FileDialog {
        id: saveFileDialog
        title: qsTr("Save ARFF")
        fileMode: FileDialog.SaveFile
        nameFilters: ["ARFF files (*.arff)", "All files (*)"]
        defaultSuffix: "arff"
        
        onAccepted: {
            if (typePage.activeController) {
                var path = selectedFile.toString()
                if (path.startsWith("file://")) {
                    path = path.substring(7)
                }
                if (typePage.activeController.saveMetadata) {
                    typePage.activeController.saveMetadata(path)
                }
            }
            
            navigateAfterConfirm()
        }
    }
    
    StandardDialog {
        id: saveToDiskDialog
        titleText: qsTr("Types saved in memory!")
        messageText: qsTr("Attribute types have been confirmed and saved in memory.\n\nDo you also want to export the database to a file on disk?")
        primaryButtonText: qsTr("Yes, export file")
        secondaryButtonText: qsTr("No, continue")
        dialogWidth: 480
        
        onPrimaryClicked: {
            saveFileDialog.open()
        }
        
        onSecondaryClicked: {
            navigateAfterConfirm()
        }
    }
    
    /** Navigate after type confirmation based on origin flags. */
    function navigateAfterConfirm() {
        if (!typePage.stack) return
        
        // Reset loadingTarget to primary
        if (typePage.stateManager) {
            typePage.stateManager.setLoadingPrimary()
        }
        
        if (typePage.isInitialLoad) {
            // Initial load: replace stack (no back to page_load)
            typePage.stack.replace("page_hub.qml", {
                "csvController": typePage.csvController,
                "arffController": typePage.arffController,
                "stateManager": typePage.stateManager,
                "navController": typePage.navController,
                "stack": typePage.stack
            })
        } else if (typePage.isMergeResult) {
            // Merge result: clear secondary and return to hub
            if (typePage.stateManager) {
                typePage.stateManager.clearSecondaryBase()
            }
            typePage.stack.replace("page_hub.qml", {
                "csvController": typePage.csvController,
                "arffController": typePage.arffController,
                "stateManager": typePage.stateManager,
                "navController": typePage.navController,
                "stack": typePage.stack
            })
        } else {
            // Default: pop back to previous page
            typePage.stack.pop()
        }
    }
    
    MessageDialog {
        id: messageDialog
        title: "Informação"
        text: ""
        buttons: MessageDialog.Ok
    }
    
    MessageDialog {
        id: validationDialog
        title: "Conversão Inválida"
        buttons: MessageDialog.Ok
        
        property string attributeName: ""
        property string attemptedType: ""
        property string errorMessage: ""
        property var comboBoxToRevert: null
        
        text: {
            if (errorMessage) {
                return qsTr("Cannot convert column '%1' to type '%2'.\n\n%3")
                    .arg(attributeName)
                    .arg(attemptedType)
                    .arg(errorMessage)
            }
            return ""
        }
    }
    
    Connections {
        target: typePage.activeController
        function onErrorOccurred(message) {
            messageDialog.title = "Erro"
            messageDialog.text = message
            messageDialog.open()
        }
        
        function onMetadataChanged() {
            console.log("QML: Metadata changed, forçando atualização do Repeater")
            // Force Repeater refresh
            attributeRepeater.model = 0
            attributeRepeater.model = Qt.binding(function() {
                if (typePage.activeController) {
                    var names = typePage.activeController.getAttributeNames()
                    return names ? names.length : 0
                }
                return 0
            })
            // Update stacking ComboBox
            try {
                if (typeof stackBySelector !== 'undefined' && typePage.activeController) {
                    stackBySelector.model = []
                    stackBySelector.model = (function() {
                        var names = typePage.activeController.getAttributeNames()
                        var res = [qsTr("None")]
                        for (var i = 0; i < names.length; i++) {
                            try {
                                if (typePage.activeController.getSuggestedType(names[i]) === 'Nominal')
                                    res.push(names[i])
                            } catch (e) {}
                        }
                        return res
                    })()
                    stackBySelector.currentIndex = 0
                }
            } catch (e) {}

            // Refresh chart after type change
            try { typePage.refreshChart() } catch (e) {}
        }
    }
}