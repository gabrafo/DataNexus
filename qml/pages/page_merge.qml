import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../components"

/**
 * PageMerge - Merge configuration and execution.
 * Requires two loaded and typified databases. Supports column mapping,
 * key column selection, join type, preview, and merge execution.
 */
Page {
    id: mergePage
    
    property var csvController: null
    property var arffController: null
    property var stateManager: null
    property var navController: null
    property var stack: null
    
    property int currentStep: 1
    property var previewData: null
    
    // Type compatibility warning (dynamically computed)
    property string mappingWarning: {
        if (!mergePage.stateManager) return ""
        if (typeof primaryColumnCombo === "undefined" || typeof secondaryColumnCombo === "undefined") return ""
        if (!primaryColumnCombo || !secondaryColumnCombo) return ""
        if (primaryColumnCombo.currentText === "" || secondaryColumnCombo.currentText === "") return ""
        return mergePage.stateManager.checkMappingCompatibility(
            secondaryColumnCombo.currentText,
            primaryColumnCombo.currentText
        )
    }
    
    background: Rectangle {
        color: Material.backgroundColor
    }
    
    StandardDialog {
        id: errorPopup
        titleText: qsTr("Error")
        primaryButtonText: qsTr("OK")
        dialogWidth: 400
    }
    
    StandardDialog {
        id: successPopup
        titleText: qsTr("✅ Merge completed!")
        primaryButtonText: qsTr("Export")
        secondaryButtonText: qsTr("Return without saving")
        dialogWidth: 480
        
        property int resultRows: 0
        property int resultCols: 0
        
        messageText: qsTr("The databases were merged successfully!\n\n%1 rows • %2 columns\n\nDo you want to export the result?")
            .arg(resultRows)
            .arg(resultCols)
        
        onPrimaryClicked: {
            mergeExportDialog.open()
        }

        onSecondaryClicked: {
            // Clear all and return to hub without saving
            if (mergePage.stateManager) mergePage.stateManager.clearAllBases()
            if (mergePage.stack) {
                mergePage.stack.replace("page_hub.qml", {
                    "csvController": mergePage.csvController,
                    "arffController": mergePage.arffController,
                    "stateManager": mergePage.stateManager,
                    "navController": mergePage.navController,
                    "stack": mergePage.stack
                })
            }
        }
    }

    FileDialog {
        id: mergeExportDialog
        title: qsTr("Export merged database")
        fileMode: FileDialog.SaveFile
        nameFilters: ["ARFF (*.arff)", "CSV (*.csv)"]
        defaultSuffix: "arff"

        onAccepted: {
            if (mergePage.stateManager) {
                mergePage.stateManager.saveToFile(selectedFile.toString())
                mergePage.stateManager.clearAllBases()
            }
            if (mergePage.stack) {
                mergePage.stack.replace("page_hub.qml", {
                    "csvController": mergePage.csvController,
                    "arffController": mergePage.arffController,
                    "stateManager": mergePage.stateManager,
                    "navController": mergePage.navController,
                    "stack": mergePage.stack
                })
            }
        }
    }
    
    StandardDialog {
        id: confirmBackPopup
        titleText: qsTr("Cancel merge?")
        messageText: qsTr("Return to the main menu? Loaded databases will be kept.")
        primaryButtonText: qsTr("Yes, go back")
        secondaryButtonText: qsTr("No, continue")
        dialogWidth: 400
        
        onPrimaryClicked: {
            if (mergePage.stack) mergePage.stack.pop()
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20
        
        RowLayout {
            Layout.fillWidth: true
            
            Button {
                text: qsTr("◀ Back")
                flat: true
                onClicked: confirmBackPopup.open()
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                text: qsTr("CONFIGURE MERGE")
                font.pointSize: 19
                font.weight: Font.Bold
                font.letterSpacing: 2
                color: Material.accent
            }
            
            Item { Layout.fillWidth: true }
            
            // Step indicator
            Row {
                spacing: 8
                
                Repeater {
                    model: [qsTr("Map"), qsTr("Merge")]
                    
                    Rectangle {
                        required property int index
                        required property string modelData
                        width: stepText.implicitWidth + 24
                        height: 32
                        radius: 16
                        color: (index + 1) <= mergePage.currentStep ? Material.accent : Qt.rgba(1,1,1,0.1)
                        border.color: (index + 1) <= mergePage.currentStep ? Material.accent : Material.frameColor
                        
                        Text {
                            id: stepText
                            anchors.centerIn: parent
                            text: (parent.index + 1) + ". " + parent.modelData
                            font.pointSize: 11
                            font.weight: Font.Medium
                            color: (parent.index + 1) <= mergePage.currentStep ? "#000000" : Material.foreground
                        }
                    }
                }
            }
        }
        
        // Database summary
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 70
            color: Qt.rgba(1, 1, 1, 0.02)
            border.color: Material.frameColor
            radius: 8
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 20
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    
                    Text {
                        text: qsTr("Dataset 1:")
                        font.pointSize: 10
                        color: Material.foreground
                        opacity: 0.6
                    }
                    Text {
                        text: mergePage.stateManager ? mergePage.stateManager.primaryFileName : ""
                        font.pointSize: 12
                        font.weight: Font.Medium
                        color: Material.accent
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }
                
                Text {
                    text: "+"
                    font.pointSize: 21
                    color: Material.foreground
                    opacity: 0.5
                }
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    
                    Text {
                        text: qsTr("Dataset 2:")
                        font.pointSize: 10
                        color: Material.foreground
                        opacity: 0.6
                    }
                    Text {
                        text: mergePage.stateManager ? mergePage.stateManager.secondaryFileName : ""
                        font.pointSize: 12
                        font.weight: Font.Medium
                        color: Material.accent
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }
            }
        }
        
        // Step content
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: mergePage.currentStep - 1
            
            // Step 1: Column mapping
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 16
                    
                    // Explanation - simple text without box
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        
                        Text {
                            text: qsTr("Match columns")
                            font.pointSize: 12
                            font.weight: Font.DemiBold
                            color: Material.foreground
                        }
                        
                        Text {
                            Layout.fillWidth: true
                            text: qsTr("Choose columns that represent the same information in both datasets.")
                            font.pointSize: 11
                            color: Material.foreground
                            opacity: 0.6
                            wrapMode: Text.WordWrap
                        }
                    }
                    
                    // Mapping area - fixed height for stable layout
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        spacing: 16
                        
                        // Primary base column
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Qt.darker(Material.backgroundColor, 1.1)
                            border.color: Material.frameColor
                            radius: 8
                            
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 12
                                
                                Text {
                                    text: qsTr("Dataset 1 column")
                                    font.pointSize: 12
                                    font.weight: Font.Medium
                                    color: Material.accent
                                }
                                
                                ComboBox {
                                    id: primaryColumnCombo
                                    Layout.fillWidth: true
                                    model: mergePage.stateManager ? mergePage.stateManager.getMappablePrimaryColumns() : []
                                }
                            }
                        }
                        
                        // Map button
                        ColumnLayout {
                            Layout.preferredWidth: 140
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 8
                            
                            Button {
                                id: mapButton
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 120
                                text: qsTr("↔ Map")
                                enabled: primaryColumnCombo.currentText !== "" && 
                                         secondaryColumnCombo.currentText !== "" &&
                                         mergePage.mappingWarning === ""
                                Material.background: enabled ? Material.accent : Material.Grey
                                Material.foreground: "#000000"
                                onClicked: {
                                    if (mergePage.stateManager) {
                                        mergePage.stateManager.addColumnMapping(
                                            secondaryColumnCombo.currentText,
                                            primaryColumnCombo.currentText
                                        )
                                    }
                                }
                            }
                            
                            // Incompatible types warning - always reserve space
                            Item {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 130
                                Layout.preferredHeight: warningText.visible ? warningText.implicitHeight : 0
                                
                                Text {
                                    id: warningText
                                    visible: mergePage.mappingWarning !== ""
                                    anchors.fill: parent
                                    text: "⚠ " + mergePage.mappingWarning
                                    font.pointSize: 10
                                    font.weight: Font.Medium
                                    color: Material.color(Material.DeepOrange)
                                    horizontalAlignment: Text.AlignHCenter
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                        
                        // Secondary base column
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: Qt.darker(Material.backgroundColor, 1.1)
                            border.color: Material.frameColor
                            radius: 8
                            
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 12
                                
                                Text {
                                    text: qsTr("Dataset 2 column")
                                    font.pointSize: 12
                                    font.weight: Font.Medium
                                    color: Material.accent
                                }
                                
                                ComboBox {
                                    id: secondaryColumnCombo
                                    Layout.fillWidth: true
                                    model: mergePage.stateManager ? mergePage.stateManager.getMappableSecondaryColumns() : []
                                }
                            }
                        }
                    }
                    
                    // Defined mappings - fills remaining space
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 140
                        color: Qt.darker(Material.backgroundColor, 1.1)
                        border.color: Material.frameColor
                        radius: 8
                        clip: true
                        
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            
                            RowLayout {
                                Layout.fillWidth: true
                                
                                Text {
                                    text: qsTr("Defined mappings")
                                    font.pointSize: 12
                                    font.weight: Font.Medium
                                    color: Material.foreground
                                }
                                
                                Item { Layout.fillWidth: true }
                                
                                // Badge with count
                                Rectangle {
                                    visible: mappingsRepeater.count > 0
                                    width: 24
                                    height: 24
                                    radius: 12
                                    color: Material.accent
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: mappingsRepeater.count
                                        font.pointSize: 11
                                        font.weight: Font.Bold
                                        color: "#000000"
                                    }
                                }
                            }
                            
                            // Content area - always fills remaining height
                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                
                                // Empty state message - centered
                                Text {
                                    anchors.centerIn: parent
                                    visible: !mappingsRepeater.model || mappingsRepeater.model.length === 0
                                    text: qsTr("No mappings defined.\nWithout mappings, only 'All data from both' will be available.")
                                    font.pointSize: 11
                                    color: Material.foreground
                                    opacity: 0.5
                                    horizontalAlignment: Text.AlignHCenter
                                    wrapMode: Text.WordWrap
                                }
                                
                                // Mapping chips with scroll
                                Flickable {
                                    anchors.fill: parent
                                    visible: mappingsRepeater.count > 0
                                    contentWidth: width
                                    contentHeight: mappingFlow.implicitHeight
                                    clip: true
                                    flickableDirection: Flickable.VerticalFlick
                                    boundsBehavior: Flickable.StopAtBounds

                                    Flow {
                                        id: mappingFlow
                                        width: parent.width
                                        spacing: 8
                                        
                                        Repeater {
                                            id: mappingsRepeater
                                            model: mergePage.stateManager ? mergePage.stateManager.getColumnMappings() : []
                                            
                                            delegate: Rectangle {
                                                required property var modelData
                                                required property int index
                                                
                                                width: mappingRow.implicitWidth + 24
                                                height: 36
                                                color: Qt.rgba(Material.accent.r, Material.accent.g, Material.accent.b, 0.15)
                                                border.color: Material.accent
                                                border.width: 1
                                                radius: 18
                                                
                                                RowLayout {
                                                    id: mappingRow
                                                    anchors.centerIn: parent
                                                    spacing: 6
                                                    
                                                    Text {
                                                        text: modelData.primary
                                                        font.pointSize: 11
                                                        font.weight: Font.Medium
                                                        color: Material.accent
                                                    }
                                                    
                                                    Text {
                                                        text: "="
                                                        font.pointSize: 12
                                                        font.weight: Font.Bold
                                                        color: Material.foreground
                                                        opacity: 0.7
                                                    }
                                                    
                                                    Text {
                                                        text: modelData.secondary
                                                        font.pointSize: 11
                                                        font.weight: Font.Medium
                                                        color: Material.foreground
                                                    }
                                                    
                                                    Rectangle {
                                                        width: 18
                                                        height: 18
                                                        radius: 9
                                                        color: "transparent"
                                                        
                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: "✕"
                                                            font.pointSize: 10
                                                            color: Material.foreground
                                                            opacity: 0.6
                                                        }
                                                        
                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: {
                                                                if (mergePage.stateManager) {
                                                                    mergePage.stateManager.removeColumnMapping(modelData.secondary)
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Navigation buttons
                    RowLayout {
                        Layout.fillWidth: true
                        
                        Item { Layout.fillWidth: true }
                        
                        Button {
                            text: qsTr("Next ▶")
                            font.pointSize: 13
                            Material.background: Material.accent
                            Material.foreground: "#000000"
                            Layout.preferredHeight: 44
                            Layout.preferredWidth: 140
                            onClicked: mergePage.currentStep = 2
                        }
                    }
                }
            }
            
            // Step 2: Configure and execute
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 16
                    
                    // Configuration
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        color: Qt.darker(Material.backgroundColor, 1.1)
                        border.color: Material.frameColor
                        radius: 12
                        
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 16
                            
                            Text {
                                text: qsTr("Merge configuration")
                                font.pointSize: 15
                                font.weight: Font.Bold
                                color: Material.foreground
                            }
                            
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 24
                                
                                // Join type - depends on existing mappings
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    
                                    Text {
                                        text: qsTr("How to combine:")
                                        font.pointSize: 12
                                        color: Material.foreground
                                    }
                                    
                                    ComboBox {
                                        id: joinTypeCombo
                                        Layout.fillWidth: true
                                        
                                        // Reactive: uses mappingsRepeater.count which updates automatically
                                        property bool hasMappings: mappingsRepeater.count > 0
                                        
                                        model: hasMappings ? [
                                            qsTr("Only matching rows (both must match)"),
                                            qsTr("All rows from Dataset 1 + matches from Dataset 2"),
                                            qsTr("All rows from Dataset 2 + matches from Dataset 1"),
                                            qsTr("All data from both")
                                        ] : [
                                            qsTr("All data from both")
                                        ]
                                        currentIndex: 0
                                        
                                        // Without mappings, only cross join is available
                                        property int effectiveJoinType: hasMappings ? currentIndex : 3
                                    }
                                }
                                
                                // Key column - uses defined mappings
                                ColumnLayout {
                                    visible: joinTypeCombo.hasMappings && joinTypeCombo.currentIndex !== 3
                                    Layout.fillWidth: true
                                    spacing: 8
                                    
                                    Text {
                                        text: qsTr("Join column:")
                                        font.pointSize: 12
                                        color: Material.foreground
                                    }
                                    
                                    ComboBox {
                                        id: keyColumnCombo
                                        Layout.fillWidth: true
                                        model: mergePage.stateManager ? mergePage.stateManager.getMappingsForDropdown() : []
                                    }
                                }
                            }
                        }
                    }
                    
                    // Join type explanation
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        color: Qt.rgba(1, 1, 1, 0.02)
                        border.color: Material.frameColor
                        radius: 8
                        
                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            text: {
                                switch (joinTypeCombo.effectiveJoinType) {
                                    case 0: return qsTr("💡 Keeps only rows where the join column value exists in BOTH databases.")
                                    case 1: return qsTr("💡 Keeps all rows from Dataset 1. If a row has no match in Dataset 2, those fields are left empty.")
                                    case 2: return qsTr("💡 Keeps all rows from Dataset 2. If a row has no match in Dataset 1, those fields are left empty.")
                                    case 3: return qsTr("💡 Combines ALL rows from both (no join column needed).")
                                    default: return ""
                                }
                            }
                            font.pointSize: 11
                            color: Material.foreground
                            opacity: 0.8
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: Qt.darker(Material.backgroundColor, 1.1)
                        border.color: Material.frameColor
                        radius: 12
                        
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            
                            RowLayout {
                                Layout.fillWidth: true
                                
                                Text {
                                    text: qsTr("Result preview")
                                    font.pointSize: 13
                                    font.weight: Font.Medium
                                    color: Material.foreground
                                }
                                
                                Item { Layout.fillWidth: true }
                                
                                Button {
                                    text: qsTr("🔄 Refresh")
                                    flat: true
                                    enabled: joinTypeCombo.effectiveJoinType === 3 || keyColumnCombo.currentText !== ""
                                    onClicked: {
                                        if (mergePage.stateManager) {
                                            var joinTypes = ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"]
                                            var keyColumn = joinTypeCombo.effectiveJoinType === 3 ? "" : 
                                                mergePage.stateManager.getMappingPrimaryColumn(keyColumnCombo.currentText)
                                            mergePage.previewData = mergePage.stateManager.previewMerge(
                                                keyColumn,
                                                joinTypes[joinTypeCombo.effectiveJoinType]
                                            )
                                        }
                                    }
                                }
                            }
                            
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: Material.backgroundColor
                                border.color: Material.frameColor
                                radius: 8
                                
                                ScrollView {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    clip: true
                                    
                                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                    
                                    Column {
                                        spacing: 0
                                        property int colCount: mergePage.previewData && mergePage.previewData.columns 
                                                              ? mergePage.previewData.columns.length : 0
                                        width: Math.max(parent.width, colCount * 120)
                                        
                                        Text {
                                            visible: (mergePage.previewData && mergePage.previewData.error) ? true : false
                                            text: (mergePage.previewData && mergePage.previewData.error) ? mergePage.previewData.error : qsTr("Click 'Refresh' to see a preview")
                                            font.pointSize: 12
                                            color: Material.foreground
                                            opacity: 0.6
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            padding: 20
                                        }
                                        
                                        Row {
                                            visible: (mergePage.previewData && mergePage.previewData.columns) ? true : false
                                            spacing: 0
                                            
                                            Repeater {
                                                model: mergePage.previewData ? mergePage.previewData.columns : []
                                                
                                                Rectangle {
                                                    required property string modelData
                                                    width: 120
                                                    height: 32
                                                    color: Material.accent
                                                    border.color: Qt.darker(Material.accent, 1.2)
                                                    
                                                    Text {
                                                        anchors.centerIn: parent
                                                        text: parent.modelData
                                                        font.pointSize: 10
                                                        font.weight: Font.Bold
                                                        color: "#000000"
                                                        elide: Text.ElideRight
                                                        width: parent.width - 8
                                                    }
                                                }
                                            }
                                        }
                                        
                                        Repeater {
                                            model: mergePage.previewData && mergePage.previewData.data 
                                                   ? mergePage.previewData.data : []
                                            
                                            Row {
                                                required property var modelData
                                                required property int index
                                                spacing: 0
                                                
                                                Repeater {
                                                    model: parent.modelData
                                                    
                                                    Rectangle {
                                                        required property string modelData
                                                        required property int index
                                                        width: 120
                                                        height: 28
                                                        color: parent.parent.index % 2 === 0 
                                                               ? Material.backgroundColor 
                                                               : Qt.darker(Material.backgroundColor, 1.05)
                                                        border.color: Material.frameColor
                                                        border.width: 0.5
                                                        
                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: parent.modelData
                                                            font.pointSize: 10
                                                            color: Material.foreground
                                                            elide: Text.ElideRight
                                                            width: parent.width - 8
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        
                                        Text {
                                            visible: mergePage.previewData && mergePage.previewData.totalRows
                                            text: qsTr("Showing %1 of ~%2 rows (estimated)")
                                                .arg(mergePage.previewData ? mergePage.previewData.previewRows : 0)
                                                .arg(mergePage.previewData ? mergePage.previewData.totalRows : 0)
                                            font.pointSize: 10
                                            color: Material.foreground
                                            opacity: 0.7
                                            padding: 8
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // Navigation buttons
                    RowLayout {
                        Layout.fillWidth: true
                        
                        Button {
                            text: qsTr("◀ Back")
                            Layout.preferredHeight: 44
                            onClicked: mergePage.currentStep = 1
                        }
                        
                        Item { Layout.fillWidth: true }
                        
                        Button {
                            text: qsTr("🔗 Execute")
                            // Enabled if: cross join OR (has mapping AND key column selected)
                            enabled: joinTypeCombo.effectiveJoinType === 3 || keyColumnCombo.currentText !== ""
                            font.pointSize: 13
                            font.weight: Font.Bold
                            Material.background: Material.accent
                            Material.foreground: "#000000"
                            Layout.preferredHeight: 48
                            Layout.preferredWidth: 180
                            
                            onClicked: {
                                if (mergePage.stateManager) {
                                    var joinTypes = ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"]
                                    // For cross join, no key column needed
                                    var keyColumn = joinTypeCombo.effectiveJoinType === 3 ? "" : 
                                        mergePage.stateManager.getMappingPrimaryColumn(keyColumnCombo.currentText)
                                    var success = mergePage.stateManager.executeMerge(
                                        keyColumn,
                                        joinTypes[joinTypeCombo.effectiveJoinType]
                                    )
                                    if (success) {
                                        successPopup.resultRows = mergePage.stateManager.primaryInstanceCount
                                        successPopup.resultCols = mergePage.stateManager.primaryAttributeCount
                                        successPopup.open()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    Connections {
        target: mergePage.stateManager
        
        function onColumnMappingChanged() {
            mappingsRepeater.model = mergePage.stateManager.getColumnMappings()
            secondaryColumnCombo.model = mergePage.stateManager.getMappableSecondaryColumns()
            keyColumnCombo.model = mergePage.stateManager.getMappingsForDropdown()
        }
        
        function onErrorOccurred(message) {
            errorPopup.messageText = message
            errorPopup.open()
        }
    }
}
