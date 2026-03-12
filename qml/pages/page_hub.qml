import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../components"

/**
 * PageHub - Central operations hub.
 * Two database slots (primary/secondary) with click-to-select.
 * Actions depend on selection: 1 slot = View/Tipify/Export, 2 slots = Merge.
 */
Page {
    id: hubPage
    
    property var csvController: null
    property var arffController: null
    property var stateManager: null
    property var navController: null
    property var stack: null
    
    property bool hasPrimary: stateManager ? stateManager.hasPrimaryBase : false
    property bool hasSecondary: stateManager ? stateManager.hasSecondaryBase : false
    property bool canMerge: stateManager ? stateManager.canMerge : false
    
    property string loadingTarget: "primary"
    
    property bool primarySelected: false
    property bool secondarySelected: false
    
    property int selectedCount: (primarySelected ? 1 : 0) + (secondarySelected ? 1 : 0)
    
    property bool canVisualize: selectedCount === 1
    property bool canExport: selectedCount === 1
    property bool canMergeNow: selectedCount === 2 && canMerge
    
    property string selectedBase: {
        if (primarySelected && !secondarySelected) return "primary"
        if (secondarySelected && !primarySelected) return "secondary"
        return ""
    }
    
    function toggleSelection(which) {
        if (which === "primary") {
            primarySelected = !primarySelected
        } else if (which === "secondary") {
            secondarySelected = !secondarySelected
        }
    }
    
    function clearSelection() {
        primarySelected = false
        secondarySelected = false
    }
    
    background: Rectangle {
        color: Material.backgroundColor
    }
    
    FileDialog {
        id: loadFileDialog
        title: qsTr("Select a database")
        nameFilters: ["Databases (*.csv *.arff)"]
        
        onAccepted: {
            var path = selectedFile.toString().toLowerCase()
            if (path.endsWith(".csv")) {
                delimiterDialog.selectedFile = selectedFile
                delimiterDialog.open()
            } else if (path.endsWith(".arff")) {
                loadArffFile(selectedFile)
            }
        }
    }
    
    Dialog {
        id: delimiterDialog
        property var selectedFile: null
        title: qsTr("CSV Separator")
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        
        Column {
            spacing: 10
            width: 280
            
            RadioButton { id: autoRadio; text: qsTr("Auto-detect"); checked: true }
            RadioButton { id: semiRadio; text: qsTr("Semicolon (;)") }
            RadioButton { id: commaRadio; text: qsTr("Comma (,)") }
            RadioButton { id: tabRadio; text: qsTr("Tab") }
        }
        
        onAccepted: {
            var delim = ""
            if (semiRadio.checked) delim = ";"
            else if (commaRadio.checked) delim = ","
            else if (tabRadio.checked) delim = "tab"
            
            loadCsvFile(delimiterDialog.selectedFile, delim)
        }
    }
    
    StandardDialog {
        id: exportDialog
        titleText: qsTr("Export database")
        messageText: qsTr("Choose the format to export the selected database.")
        primaryButtonText: qsTr("ARFF")
        secondaryButtonText: qsTr("CSV")
        dialogWidth: 400
        
        onPrimaryClicked: {
            saveFileDialog.defaultSuffix = "arff"
            saveFileDialog.nameFilters = ["ARFF (*.arff)"]
            saveFileDialog.open()
        }
        
        onSecondaryClicked: {
            saveFileDialog.defaultSuffix = "csv"
            saveFileDialog.nameFilters = ["CSV (*.csv)"]
            saveFileDialog.open()
        }
    }
    
    FileDialog {
        id: saveFileDialog
        title: qsTr("Export database")
        fileMode: FileDialog.SaveFile
        nameFilters: ["ARFF (*.arff)", "CSV (*.csv)"]
        defaultSuffix: "arff"
        
        onAccepted: {
            if (hubPage.stateManager && hubPage.selectedBase) {
                hubPage.stateManager.saveBaseToFile(hubPage.selectedBase, selectedFile.toString())
            }
        }
    }
    
    MessageDialog {
        id: errorDialog
        title: qsTr("Error")
        text: ""
    }
    
    function loadCsvFile(fileUrl, delimiter) {
        if (hubPage.csvController) {
            hubPage.csvController.loadCsv(fileUrl, delimiter)
        }
    }
    
    function loadArffFile(fileUrl) {
        if (hubPage.arffController) {
            hubPage.arffController.loadArff(fileUrl)
        }
    }
    
    function startLoadPrimary() {
        // Set target on StateManager (single source of truth)
        if (hubPage.stateManager) {
            hubPage.stateManager.setLoadingPrimary()
        }
        hubPage.loadingTarget = "primary"
        if (hubPage.navController) {
            hubPage.navController.startLoadPrimary()
        }
        loadFileDialog.open()
    }
    
    function startLoadSecondary() {
        // Set target on StateManager (single source of truth)
        if (hubPage.stateManager) {
            hubPage.stateManager.setLoadingSecondary()
        }
        hubPage.loadingTarget = "secondary"
        if (hubPage.navController) {
            hubPage.navController.startLoadSecondary()
        }
        loadFileDialog.open()
    }
    
    function navigateToView(which) {
        if (hubPage.stack && hubPage.stateManager) {
            // Sync controller with StateManager data before viewing
            var format = (which === "secondary") ? hubPage.stateManager.secondaryFormat : hubPage.stateManager.primaryFormat
            if (which === "primary") {
                if (format === "arff") {
                    hubPage.stateManager.pushPrimaryToController(hubPage.arffController)
                } else {
                    hubPage.stateManager.pushPrimaryToController(hubPage.csvController)
                }
            } else {
                if (format === "arff") {
                    hubPage.stateManager.pushSecondaryToController(hubPage.arffController)
                } else {
                    hubPage.stateManager.pushSecondaryToController(hubPage.csvController)
                }
            }
            
            hubPage.stack.push("page_view.qml", {
                "csvController": hubPage.csvController,
                "arffController": hubPage.arffController,
                "stateManager": hubPage.stateManager,
                "navController": hubPage.navController,
                "stack": hubPage.stack,
                "targetBase": which,
                "viewOnly": true
            })
        }
    }
    
    function navigateToMerge() {
        if (hubPage.stack && hubPage.canMerge) {
            hubPage.stack.push("page_merge.qml", {
                "csvController": hubPage.csvController,
                "arffController": hubPage.arffController,
                "stateManager": hubPage.stateManager,
                "navController": hubPage.navController,
                "stack": hubPage.stack
            })
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.xl
        spacing: Theme.spacing.lg
        
        RowLayout {
            Layout.fillWidth: true
            
            Text {
                text: "MIDAS"
                color: Material.accent
                font.pointSize: Theme.fontSize.h1
                font.weight: Font.Bold
                font.letterSpacing: 4
            }
            
            Item { Layout.fillWidth: true }
            
            Text {
                visible: hubPage.hasPrimary && hubPage.selectedCount === 0
                text: qsTr("Select databases to see available actions")
                font.pointSize: Theme.fontSize.label
                color: Material.foreground
                opacity: 0.5
            }

            Text {
                text: qsTr("Language")
                font.pointSize: Theme.fontSize.label
                color: Material.accent
                font.weight: Font.Medium
            }

            ComboBox {
                id: langCombo
                Layout.preferredWidth: 130
                model: languageManager ? languageManager.languages : []
                textRole: "name"
                currentIndex: {
                    if (!languageManager) return 0
                    var langs = languageManager.languages
                    for (var i = 0; i < langs.length; i++) {
                        if (langs[i].code === languageManager.currentLanguage)
                            return i
                    }
                    return 0
                }
                onActivated: function(index) {
                    if (languageManager) {
                        languageManager.setLanguage(languageManager.languages[index].code)
                    }
                }
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 200
            spacing: 20
            
            Rectangle {
                id: primarySlot
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Qt.darker(Material.backgroundColor, 1.1)
                border.color: hubPage.primarySelected ? Material.accent : 
                              (hubPage.hasPrimary ? Qt.rgba(1,1,1,0.3) : Material.frameColor)
                border.width: hubPage.primarySelected ? 3 : 1
                radius: 12
                
                MouseArea {
                    anchors.fill: parent
                    enabled: hubPage.hasPrimary
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: hubPage.toggleSelection("primary")
                }
                
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12
                    
                    RowLayout {
                        Layout.fillWidth: true
                        
                        Text {
                            text: hubPage.primarySelected ? qsTr("✓ Dataset 1") : qsTr("📁 Dataset 1")
                            font.pointSize: 12
                            font.weight: Font.Bold
                            color: hubPage.primarySelected ? Material.accent : 
                                   (hubPage.hasPrimary ? Material.foreground : Material.foreground)
                            opacity: hubPage.hasPrimary ? 1.0 : 0.5
                        }
                        
                        Item { Layout.fillWidth: true }
                    }
                    
                    ColumnLayout {
                        visible: hubPage.hasPrimary
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        
                        Text {
                            text: hubPage.stateManager ? hubPage.stateManager.primaryFileName : ""
                            font.pointSize: 14
                            font.weight: Font.Medium
                            color: Material.foreground
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        
                        Item { Layout.fillHeight: true }
                        
                        Text {
                            text: qsTr("%1 rows • %2 columns")
                                .arg(hubPage.stateManager ? hubPage.stateManager.primaryInstanceCount : 0)
                                .arg(hubPage.stateManager ? hubPage.stateManager.primaryAttributeCount : 0)
                            font.pointSize: 11
                            color: Material.foreground
                            opacity: 0.7
                        }
                        
                        Text {
                            visible: !hubPage.primarySelected
                            text: qsTr("Click to select")
                            font.pointSize: 10
                            font.italic: true
                            color: Material.foreground
                            opacity: 0.4
                        }
                        
                        Button {
                            visible: hubPage.primarySelected
                            text: qsTr("Replace")
                            flat: true
                            font.pointSize: 10
                            onClicked: startLoadPrimary()
                        }
                    }
                    
                    ColumnLayout {
                        visible: !hubPage.hasPrimary
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.alignment: Qt.AlignCenter
                        
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: qsTr("No database loaded")
                            font.pointSize: 12
                            color: Material.foreground
                            opacity: 0.5
                        }
                        
                        Button {
                            Layout.alignment: Qt.AlignHCenter
                            text: qsTr("Load database")
                            Material.background: Material.accent
                            Material.foreground: "#000000"
                            onClicked: startLoadPrimary()
                        }
                    }
                }
            }
            
            ColumnLayout {
                Layout.preferredWidth: 60
                Layout.alignment: Qt.AlignVCenter
                
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "⇄"
                    font.pointSize: 29
                    color: hubPage.selectedCount === 2 ? Material.accent : Material.foreground
                    opacity: hubPage.canMerge ? 0.7 : 0.3
                }
            }
            
            Rectangle {
                id: secondarySlot
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Qt.darker(Material.backgroundColor, 1.1)
                border.color: hubPage.secondarySelected ? Material.accent : 
                              (hubPage.hasSecondary ? Qt.rgba(1,1,1,0.3) : Material.frameColor)
                border.width: hubPage.secondarySelected ? 3 : 1
                radius: 12
                
                MouseArea {
                    anchors.fill: parent
                    enabled: hubPage.hasSecondary
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: hubPage.toggleSelection("secondary")
                }
                
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12
                    
                    RowLayout {
                        Layout.fillWidth: true
                        
                        Text {
                            text: hubPage.secondarySelected ? qsTr("✓ Dataset 2") : qsTr("📂 Dataset 2")
                            font.pointSize: 12
                            font.weight: Font.Bold
                            color: hubPage.secondarySelected ? Material.accent : 
                                   (hubPage.hasSecondary ? Material.foreground : Material.foreground)
                            opacity: hubPage.hasSecondary ? 1.0 : 0.5
                        }
                        
                        Item { Layout.fillWidth: true }
                        
                        Item { Layout.fillWidth: true }
                    }
                    
                    ColumnLayout {
                        visible: hubPage.hasSecondary
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        
                        Text {
                            text: hubPage.stateManager ? hubPage.stateManager.secondaryFileName : ""
                            font.pointSize: 14
                            font.weight: Font.Medium
                            color: Material.foreground
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        
                        Item { Layout.fillHeight: true }
                        
                        Text {
                            text: qsTr("%1 rows • %2 columns")
                                .arg(hubPage.stateManager ? hubPage.stateManager.secondaryInstanceCount : 0)
                                .arg(hubPage.stateManager ? hubPage.stateManager.secondaryAttributeCount : 0)
                            font.pointSize: 11
                            color: Material.foreground
                            opacity: 0.7
                        }
                        
                        Text {
                            visible: !hubPage.secondarySelected
                            text: qsTr("Click to select")
                            font.pointSize: 10
                            font.italic: true
                            color: Material.foreground
                            opacity: 0.4
                        }
                        
                        RowLayout {
                            visible: hubPage.secondarySelected
                            spacing: 8
                            
                            Button {
                                text: qsTr("Replace")
                                flat: true
                                font.pointSize: 10
                                onClicked: startLoadSecondary()
                            }
                            
                            Button {
                                text: qsTr("✕ Remove")
                                flat: true
                                font.pointSize: 10
                                Material.foreground: Material.color(Material.DeepOrange)
                                onClicked: {
                                    if (hubPage.stateManager) {
                                        hubPage.stateManager.clearSecondaryBase()
                                        hubPage.secondarySelected = false
                                    }
                                }
                            }
                        }
                    }
                    
                    ColumnLayout {
                        visible: !hubPage.hasSecondary
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.alignment: Qt.AlignCenter
                        spacing: 12
                        
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "📂"
                            font.pointSize: 33
                            opacity: 0.3
                        }
                        
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: qsTr("Empty slot")
                            font.pointSize: 12
                            color: Material.foreground
                            opacity: 0.5
                        }
                        
                        Button {
                            Layout.alignment: Qt.AlignHCenter
                            text: qsTr("+ Load second database")
                            enabled: hubPage.hasPrimary
                            Material.background: enabled ? Material.accent : "transparent"
                            Material.foreground: enabled ? "#000000" : Material.foreground
                            opacity: enabled ? 1.0 : 0.4
                            onClicked: startLoadSecondary()
                        }
                        
                        Text {
                            visible: !hubPage.hasPrimary
                            Layout.alignment: Qt.AlignHCenter
                            text: qsTr("Load Dataset 1 first")
                            font.pointSize: 10
                            color: Material.foreground
                            opacity: 0.4
                        }
                    }
                }
            }
        }
        
        // Action area - varies based on selection
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            spacing: 20
            
            // No slots selected
            Rectangle {
                visible: hubPage.selectedCount === 0
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Qt.rgba(1,1,1,0.02)
                border.color: Material.frameColor
                radius: 12
                
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "👆"
                        font.pointSize: 29
                        opacity: 0.5
                    }
                    
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("Select one or two databases above")
                        font.pointSize: 13
                        color: Material.foreground
                        opacity: 0.6
                    }
                    
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("1 base = View/Typify/Export  •  2 bases = Merge")
                        font.pointSize: 11
                        color: Material.foreground
                        opacity: 0.4
                    }
                }
            }
            
            // 1 slot selected: View, Typify, Export
            ActionCard {
                visible: hubPage.selectedCount === 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: parent.width / 3 - 10
                icon: "◉"
                title: qsTr("View")
                subtitle: qsTr("View and edit the selected database")
                onClicked: navigateToView(hubPage.selectedBase)
            }
            
            ActionCard {
                visible: hubPage.selectedCount === 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: parent.width / 3 - 10
                icon: "⚙"
                title: qsTr("Typify")
                subtitle: qsTr("Define attribute types")
                onClicked: navigateToTypify()
            }
            
            ActionCard {
                visible: hubPage.selectedCount === 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: parent.width / 3 - 10
                icon: "⬇"
                title: qsTr("Export")
                subtitle: qsTr("Save database to disk")
                onClicked: exportDialog.open()
            }
            
            // 2 slots selected: Merge only
            ActionCard {
                visible: hubPage.selectedCount === 2
                Layout.fillWidth: true
                Layout.fillHeight: true
                icon: "⊕"
                title: qsTr("Merge Databases")
                subtitle: hubPage.canMergeNow
                          ? qsTr("Combine the two selected databases")
                          : qsTr("Both databases must be typified")
                highlighted: hubPage.canMergeNow
                enabled: hubPage.canMergeNow
                disabledHint: ""
                onClicked: navigateToMerge()
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            opacity: hubPage.selectedCount > 0 ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: qsTr("Clear selection")
                flat: true
                font.pointSize: 11
                enabled: hubPage.selectedCount > 0
                onClicked: hubPage.clearSelection()
            }
            
            Item { Layout.fillWidth: true }
        }
        
        Item { Layout.fillHeight: true }
    }
    
    onHasPrimaryChanged: {
        if (!hasPrimary) {
            primarySelected = false
        }
    }
    
    onHasSecondaryChanged: {
        if (!hasSecondary) {
            secondarySelected = false
        }
    }
    
    Connections {
        target: hubPage.csvController
        enabled: hubPage.visible
        
        function onDataframeChanged() {
            // syncFromCSV checks loadingTarget automatically; auto-typification is handled by StateManager
            if (hubPage.stateManager && hubPage.csvController) {
                hubPage.stateManager.syncFromCSV(
                    hubPage.csvController,
                    hubPage.csvController.fileName
                )
            }
        }
    }
    
    Connections {
        target: hubPage.arffController
        enabled: hubPage.visible
        
        function onDataLoaded() {
            // syncFromARFF checks loadingTarget automatically; ARFF already has type definitions
            if (hubPage.stateManager && hubPage.arffController) {
                hubPage.stateManager.syncFromARFF(
                    hubPage.arffController,
                    hubPage.arffController.fileName
                )
            }
        }
    }
    
    function navigateToPreprocess(fileType) {
        var isSecondary = hubPage.stateManager ? hubPage.stateManager.loadingTarget === "secondary" : false
        
        if (hubPage.stack) {
            hubPage.stack.push("page_preprocess.qml", {
                "csvController": hubPage.csvController,
                "arffController": hubPage.arffController,
                "stateManager": hubPage.stateManager,
                "navController": hubPage.navController,
                "stack": hubPage.stack,
                "fileType": fileType,
                "isSecondaryBase": isSecondary,
                "isInitialLoad": false,
                "returnToHub": true
            })
        }
    }
    
    // Navigate to typification for the selected base
    function navigateToTypify() {
        if (!hubPage.selectedBase || !hubPage.stack) return
        
        var isSecondary = hubPage.selectedBase === "secondary"
        var format = isSecondary 
            ? (hubPage.stateManager ? hubPage.stateManager.secondaryFormat : "csv")
            : (hubPage.stateManager ? hubPage.stateManager.primaryFormat : "csv")
        
        // Update loadingTarget so preprocess knows which base to edit
        if (hubPage.stateManager) {
            if (isSecondary) {
                hubPage.stateManager.setLoadingSecondary()
            } else {
                hubPage.stateManager.setLoadingPrimary()
            }
        }
        
        if (hubPage.stateManager) {
            if (isSecondary) {
                if (format === "arff") {
                    hubPage.stateManager.pushSecondaryToController(hubPage.arffController)
                } else {
                    hubPage.stateManager.pushSecondaryToController(hubPage.csvController)
                }
            } else {
                if (format === "arff") {
                    hubPage.stateManager.pushPrimaryToController(hubPage.arffController)
                } else {
                    hubPage.stateManager.pushPrimaryToController(hubPage.csvController)
                }
            }
        }
        
        hubPage.stack.push("page_preprocess.qml", {
            "csvController": hubPage.csvController,
            "arffController": hubPage.arffController,
            "stateManager": hubPage.stateManager,
            "navController": hubPage.navController,
            "stack": hubPage.stack,
            "fileType": format === "arff" ? "arff" : "csv",
            "isSecondaryBase": isSecondary,
            "isInitialLoad": false,
            "returnToHub": true
        })
    }
    
    Connections {
        target: hubPage.stateManager
        
        function onErrorOccurred(message) {
            errorDialog.text = message
            errorDialog.open()
        }
    }
}
