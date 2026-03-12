import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../components"

pragma ComponentBehavior: Bound

/**
 * PageView - Paginated data viewing and editing.
 * Supports row/column deletion. Returns to hub on save/finish.
 */
Page {
    id: dataPage
    
    property var csvController: null
    property var arffController: null
    property var stateManager: null
    property var navController: null
    property var stack: null
    
    property string targetBase: "primary"
    property bool viewOnly: true
    
    // Resolve file type from StateManager
    property string fileType: {
        if (stateManager) {
            if (targetBase === "secondary") {
                return stateManager.secondaryFormat || "csv"
            } else {
                return stateManager.primaryFormat || "csv"
            }
        }
        return "csv"
    }
    
    property var activeController: fileType === "csv" ? csvController : arffController
    
    property string baseName: {
        if (stateManager) {
            if (targetBase === "secondary") {
                return stateManager.secondaryFileName || "Dataset 2"
            } else {
                return stateManager.primaryFileName || "Dataset 1"
            }
        }
        return "Sem nome"
    }
    
    property int totalInstances: {
        if (stateManager) {
            if (targetBase === "secondary") {
                return stateManager.secondaryInstanceCount
            } else {
                return stateManager.primaryInstanceCount
            }
        }
        return 0
    }
    
    property int totalAttributes: {
        if (stateManager) {
            if (targetBase === "secondary") {
                return stateManager.secondaryAttributeCount
            } else {
                return stateManager.primaryAttributeCount
            }
        }
        return 0
    }
    
    background: Rectangle {
        color: Material.backgroundColor
    }

    // Confirm deletion dialog (row or column)
    Dialog {
        id: confirmDeleteDialog
        modal: true
        title: qsTr("Confirm deletion")
        standardButtons: Dialog.Ok | Dialog.Cancel

        // Explicit size avoids implicit-width binding loop in Material style.
        width: 420
        implicitWidth: 420

        property string deleteMode: ""   // "row" | "column"
        property int targetIndex: -1
        property string messageText: ""

        contentItem: Text {
            text: confirmDeleteDialog.messageText
            color: Material.foreground
            wrapMode: Text.WordWrap
            width: confirmDeleteDialog.width - 40
        }

        onAccepted: {
            if (!dataPage.activeController)
                return
            if (deleteMode === "row") {
                dataPage.activeController.deleteRow(targetIndex)
            } else if (deleteMode === "column") {
                dataPage.activeController.deleteColumn(targetIndex)
            }
        }
    }
    
    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 24
        
        // Left side - Table
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Material.backgroundColor
            border.color: Material.frameColor
            border.width: 1
            radius: 8
            
            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                
                Text {
                    text: dataPage.baseName
                    font.pointSize: 17
                    font.weight: Font.Medium
                    color: Material.foreground
                    width: parent.width
                    anchors.horizontalCenter: parent.horizontalCenter
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideMiddle
                }
                
                ScrollView {
                    id: scrollView
                    width: parent.width
                    height: parent.height - 40
                    clip: true
                    
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOn
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    
                    contentWidth: fullContentWidth
                    contentHeight: contentColumn.height

                    property int indexColWidth: 56
                    property int dataColWidth: 120
                    property int actionColWidth: 44
                    // Uses attributeCount property (with notify) to avoid stale header after deletions
                    property int dataCols: dataPage.activeController ? dataPage.activeController.attributeCount : 0
                    property int tableTotalWidth: dataCols * dataColWidth

                    property int fullContentWidth: actionColWidth + indexColWidth + tableTotalWidth

                    property int pageRowCount: {
                        if (!dataPage.activeController)
                            return 0
                        var start = dataPage.activeController.currentPage * dataPage.activeController.pageSize
                        var total = dataPage.totalInstances
                        var remaining = total - start
                        if (remaining < 0)
                            return 0
                        return Math.min(dataPage.activeController.pageSize, remaining)
                    }
                    
                    Column {
                        id: contentColumn
                        spacing: 0
                        width: scrollView.fullContentWidth

                        // Header actions row: delete column buttons
                        Row {
                            id: headerActionsRow
                            spacing: 0
                            width: parent.width
                            height: 24

                            Item {
                                width: scrollView.actionColWidth
                                height: parent.height
                            }

                            Item {
                                width: scrollView.indexColWidth
                                height: parent.height
                            }

                            Repeater {
                                model: dataPage.activeController ? dataPage.activeController.attributeCount : 0

                                Item {
                                    id: headerActionCell
                                    required property int index
                                    width: scrollView.dataColWidth
                                    height: parent.height

                                    ToolButton {
                                        anchors.centerIn: parent
                                        display: AbstractButton.IconOnly
                                        icon.name: "edit-delete"
                                        icon.color: Material.color(Material.DeepOrange)
                                        padding: 0
                                        implicitWidth: 20
                                        implicitHeight: 20
                                        onClicked: {
                                            if (!dataPage.activeController)
                                                return
                                            var _dep = dataPage.activeController.attributeCount
                                            var colName = dataPage.activeController.headerForColumn(headerActionCell.index)
                                            confirmDeleteDialog.deleteMode = "column"
                                            confirmDeleteDialog.targetIndex = headerActionCell.index
                                            confirmDeleteDialog.messageText = qsTr("Delete column '%1' (column %2)?")
                                                .arg(colName)
                                                .arg(headerActionCell.index + 1)
                                            confirmDeleteDialog.open()
                                        }
                                    }
                                }
                            }
                        }

                            Row {
                                id: headerRow
                                spacing: 0
                                width: parent.width

                                Rectangle {
                                    width: scrollView.actionColWidth
                                    height: 44
                                    color: "transparent"
                                }

                                Rectangle {
                                    width: scrollView.indexColWidth
                                    height: 44
                                    color: Material.accent
                                    border.color: Qt.darker(Material.accent, 1.2)
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: qsTr("Row")
                                        color: "#000000"
                                        font.pointSize: 10
                                        font.weight: Font.Bold
                                        horizontalAlignment: Text.AlignHCenter
                                    }
                                }

                                Repeater {
                                    model: dataPage.activeController ? dataPage.activeController.attributeCount : 0

                                    Rectangle {
                                        id: headerCell
                                        required property int index
                                        width: scrollView.dataColWidth
                                        height: 44
                                        color: Material.accent
                                        border.color: Qt.darker(Material.accent, 1.2)
                                        border.width: 1

                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 4
                                            spacing: 2

                                            Text {
                                                anchors.horizontalCenter: parent.horizontalCenter
                                                width: parent.width
                                                text: {
                                                    if (!dataPage.activeController)
                                                        return ""
                                                    var _dep = dataPage.activeController.attributeCount
                                                    return (headerCell.index + 1) + ": " + dataPage.activeController.headerForColumn(headerCell.index)
                                                }
                                                color: "#000000"
                                                font.pointSize: 10
                                                font.weight: Font.Bold
                                                elide: Text.ElideRight
                                                horizontalAlignment: Text.AlignHCenter
                                            }
                                        }
                                    }
                                }
                            }

                            // Data content (actions + index + table)
                            Row {
                                spacing: 0
                                width: parent.width

                                // Fixed row-delete action column
                                Flickable {
                                    id: rowDeleteFlick
                                    width: scrollView.actionColWidth
                                    height: dataTable.height
                                    interactive: false
                                    clip: true

                                    contentY: dataTable.contentY
                                    contentWidth: width
                                    contentHeight: scrollView.pageRowCount * 32

                                    Column {
                                        width: parent.width
                                        spacing: 0

                                        Repeater {
                                            model: scrollView.pageRowCount

                                            Rectangle {
                                                id: rowDeleteCell
                                                required property int index
                                                width: rowDeleteFlick.width
                                                height: 32
                                                color: "transparent"

                                                ToolButton {
                                                    anchors.centerIn: parent
                                                    display: AbstractButton.IconOnly
                                                    icon.name: "edit-delete"
                                                    icon.color: Material.color(Material.DeepOrange)
                                                    padding: 0
                                                    implicitWidth: 20
                                                    implicitHeight: 20
                                                    onClicked: {
                                                        if (!dataPage.activeController)
                                                            return
                                                        var globalRow = (dataPage.activeController.currentPage * dataPage.activeController.pageSize) + rowDeleteCell.index
                                                        confirmDeleteDialog.deleteMode = "row"
                                                        confirmDeleteDialog.targetIndex = globalRow
                                                        confirmDeleteDialog.messageText = qsTr("Delete row %1?")
                                                            .arg(globalRow + 1)
                                                        confirmDeleteDialog.open()
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // Fixed row-index column
                                Flickable {
                                    id: rowIndexFlick
                                    width: scrollView.indexColWidth
                                    height: dataTable.height
                                    interactive: false
                                    clip: true

                                    contentY: dataTable.contentY
                                    contentWidth: width
                                    contentHeight: scrollView.pageRowCount * 32

                                    Column {
                                        width: parent.width
                                        spacing: 0

                                        Repeater {
                                            model: scrollView.pageRowCount

                                            Rectangle {
                                                id: rowIndexCell
                                                required property int index
                                                width: rowIndexFlick.width
                                                height: 32
                                                color: (index % 2 === 0)
                                                    ? Qt.darker(Material.backgroundColor, 1.12)
                                                    : Qt.darker(Material.backgroundColor, 1.18)
                                                border.color: Material.frameColor
                                                border.width: 0.5

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: {
                                                        if (!dataPage.activeController)
                                                            return ""
                                                        var start = dataPage.activeController.currentPage * dataPage.activeController.pageSize
                                                        return String(start + rowIndexCell.index + 1)
                                                    }
                                                    color: Material.foreground
                                                    font.pointSize: 10
                                                    font.weight: Font.DemiBold
                                                    horizontalAlignment: Text.AlignHCenter
                                                }
                                            }
                                        }
                                    }
                                }

                                // Data table (data columns only)
                                TableView {
                                    id: dataTable
                                    width: scrollView.tableTotalWidth
                                    height: dataPage.height - 200
                                    model: dataPage.activeController ? dataPage.activeController.tableModel : null
                                    clip: true

                                    delegate: Rectangle {
                                        id: cell
                                        required property int row
                                        required property int column
                                        required property string display

                                        implicitWidth: scrollView.dataColWidth
                                        implicitHeight: 32
                                        color: (cell.row % 2 === 0) ? Material.backgroundColor : Qt.darker(Material.backgroundColor, 1.05)
                                        border.color: Material.frameColor
                                        border.width: 0.5

                                        Text {
                                            anchors.centerIn: parent
                                            text: cell.display || ""
                                            color: Material.foreground
                                            font.pointSize: 10
                                            elide: Text.ElideRight
                                            width: parent.width - 4
                                            horizontalAlignment: Text.AlignHCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        // Right side - Info panel
        Rectangle {
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            color: Material.backgroundColor
            border.color: Material.frameColor
            border.width: 1
            radius: 8
            
            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 20
                
                Text {
                    text: qsTr("Database info")
                    font.pointSize: 17
                    font.weight: Font.Medium
                    color: Material.foreground
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                
                Column {
                    width: parent.width
                    spacing: 12
                    
                    Row {
                        width: parent.width
                        spacing: 8
                        
                        Text {
                            text: qsTr("Total instances:")
                            color: Material.foreground
                            font.pointSize: 12
                        }
                        
                        Text {
                            text: dataPage.totalInstances
                            color: Material.accent
                            font.pointSize: 12
                            font.weight: Font.Medium
                        }
                    }
                    
                    Row {
                        width: parent.width
                        spacing: 8
                        
                        Text {
                            text: qsTr("Total attributes:")
                            color: Material.foreground
                            font.pointSize: 12
                        }
                        
                        Text {
                            text: dataPage.totalAttributes
                            color: Material.accent
                            font.pointSize: 12
                            font.weight: Font.Medium
                        }
                    }
                    
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Material.frameColor
                    }
                    
                    Text {
                        text: qsTr("Pagination")
                        font.pointSize: 13
                        font.weight: Font.Medium
                        color: Material.foreground
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    
                    Text {
                        width: parent.width
                        text: qsTr("Page %1 of %2")
                            .arg(dataPage.activeController ? dataPage.activeController.currentPage + 1 : 0)
                            .arg(dataPage.activeController ? dataPage.activeController.totalPages : 0)
                        color: Material.foreground
                        font.pointSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                    ComboBox {
                        width: parent.width
                        model: [10, 25, 50, 100, 200]
                        currentIndex: {
                            if (!dataPage.activeController)
                                return 2
                            var v = dataPage.activeController.pageSize
                            for (var i = 0; i < model.length; i++) {
                                if (model[i] === v)
                                    return i
                            }
                            return 2
                        }
                        onActivated: {
                            if (dataPage.activeController)
                                dataPage.activeController.setPageSize(model[currentIndex])
                        }
                    }
                    
                    Text {
                        width: parent.width
                        text: qsTr("(%1 rows per page)")
                            .arg(dataPage.activeController ? dataPage.activeController.pageSize : 0)
                        color: Material.foreground
                        font.pointSize: 10
                        opacity: 0.7
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 8
                        
                        Button {
                            text: "◄"
                            enabled: dataPage.activeController && dataPage.activeController.currentPage > 0
                            onClicked: {
                                if (dataPage.activeController) {
                                    dataPage.activeController.previousPage()
                                }
                            }
                            Material.elevation: 2
                        }
                        
                        Button {
                            text: "►"
                            enabled: dataPage.activeController && dataPage.activeController.currentPage < dataPage.activeController.totalPages - 1
                            onClicked: {
                                if (dataPage.activeController) {
                                    dataPage.activeController.nextPage()
                                }
                            }
                            Material.elevation: 2
                        }
                    }
                }
                
                Item {
                    width: parent.width
                    height: 40
                }
                
                Column {
                    width: parent.width
                    spacing: 12
                    
                    Button {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width
                        text: qsTr("Back")
                        Material.foreground: "#FFFFFF"
                        font.weight: Font.Medium
                        Material.elevation: 6
                        onClicked: {
                            if (dataPage.stack) {
                                dataPage.stack.pop()
                            }
                        }
                    }
                    
                    Button {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width
                        text: qsTr("Finish")
                        Material.background: Material.accent
                        Material.foreground: "#000000"
                        font.weight: Font.Medium
                        Material.elevation: 4
                        onClicked: {
                            saveDialog.open()
                        }
                    }
                }
            }
        }
    }
    
    // Dialog: ask to save changes before leaving (viewOnly mode)
    StandardDialog {
        id: saveDialog
        titleText: qsTr("Save changes?")
        messageText: qsTr("Export the current database to a file on disk?")
        primaryButtonText: qsTr("Yes, export")
        secondaryButtonText: qsTr("No, just go back")
        dialogWidth: 420
        
        onPrimaryClicked: {
            saveFileDialog.open()
        }
        
        onSecondaryClicked: {
            if (dataPage.stack) {
                dataPage.stack.pop()
            }
        }
    }
    
    FileDialog {
        id: saveFileDialog
        title: qsTr("Save database")
        fileMode: FileDialog.SaveFile
        nameFilters: ["ARFF (*.arff)", "CSV (*.csv)"]
        defaultSuffix: "arff"
        
        onAccepted: {
            if (dataPage.stateManager) {
                dataPage.stateManager.saveToFile(selectedFile.toString())
            }
            // Save and return to hub
            if (dataPage.stack) {
                dataPage.stack.pop()
            }
        }
    }
}