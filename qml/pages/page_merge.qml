import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../components"

/**
 * PageMerge - Merge configuration and execution on a single screen.
 * Optional single column pair (with type check) or no mapping (cross join only).
 */
Page {
    id: mergePage

    property var csvController: null
    property var arffController: null
    property var stateManager: null
    property var navController: null
    property var stack: null

    property var previewData: null
    property bool hasJoinMapping: false

    // Keep `hasJoinMapping` in sync when a stateManager is assigned or changes
    onStateManagerChanged: {
        if (mergePage.stateManager && typeof mergePage.stateManager.getColumnMappings === "function") {
            mergePage.hasJoinMapping = mergePage.stateManager.getColumnMappings().length > 0
            // Also refresh models if combos exist
            if (typeof primaryColumnCombo !== "undefined" && primaryColumnCombo)
                primaryColumnCombo.model = mergePage.stateManager.getMappablePrimaryColumns()
            if (typeof secondaryColumnCombo !== "undefined" && secondaryColumnCombo)
                secondaryColumnCombo.model = mergePage.stateManager.getSecondaryColumns()
        } else {
            mergePage.hasJoinMapping = false
        }
    }

    /** 0–3 = INNER..CROSS when a mapping exists; without mapping, merge always behaves as cross (3). */
    property int joinTypeIndex: 0
    property int resolvedJoinType: mergePage.hasJoinMapping ? mergePage.joinTypeIndex : 3
    property bool canExecuteMerge: mergePage.resolvedJoinType === 3 || mergePage.mergeKeyPrimary() !== ""

    function mergeKeyPrimary() {
        if (!mergePage.stateManager || !mergePage.hasJoinMapping)
            return ""
        var m = mergePage.stateManager.getColumnMappings()
        return m.length > 0 ? m[0].primary : ""
    }

    property string mappingWarning: {
        if (!mergePage.stateManager)
            return ""
        if (typeof primaryColumnCombo === "undefined" || typeof secondaryColumnCombo === "undefined")
            return ""
        if (!primaryColumnCombo || !secondaryColumnCombo)
            return ""
        if (primaryColumnCombo.currentText === "" || secondaryColumnCombo.currentText === "")
            return ""
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
            if (mergePage.stateManager)
                mergePage.stateManager.clearAllBases()
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
            if (mergePage.stack)
                mergePage.stack.pop()
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
        }

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

        ScrollView {
            id: mergeScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AsNeeded
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            ColumnLayout {
                width: Math.max(mergeScroll.availableWidth > 0 ? mergeScroll.availableWidth : mergeScroll.width - 8, 400)
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: mergeKeyBlock.implicitHeight + 32
                    color: Qt.darker(Material.backgroundColor, 1.1)
                    border.color: Material.frameColor
                    radius: 12

                    ColumnLayout {
                        id: mergeKeyBlock
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 16
                        spacing: Theme.spacing.sm

                        Text {
                            text: qsTr("Join key (column pair)")
                            font.pointSize: Theme.fontSize.h3
                            font.weight: Font.Bold
                            color: Material.foreground
                        }

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("Required for inner, left, or right join. Not needed for a Cartesian product.")
                            font.pointSize: Theme.fontSize.caption
                            color: Material.foreground
                            opacity: 0.7
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("Pick one column in each base. Types must be compatible.")
                            font.pointSize: Theme.fontSize.caption
                            color: Material.foreground
                            opacity: 0.65
                            wrapMode: Text.WordWrap
                        }

                        RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 100
                                    color: Qt.darker(Material.backgroundColor, 1.15)
                                    border.color: Material.frameColor
                                    radius: 8

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 8

                                        Text {
                                            text: qsTr("Dataset 1 column")
                                            font.pointSize: 11
                                            font.weight: Font.Medium
                                            color: Material.accent
                                        }

                                        ComboBox {
                                            id: primaryColumnCombo
                                            Layout.fillWidth: true
                                            flat: true
                                            implicitHeight: 40
                                            padding: 8
                                            leftPadding: 12
                                            rightPadding: 36
                                            font.pointSize: Theme.fontSize.label
                                            model: mergePage.stateManager ? mergePage.stateManager.getMappablePrimaryColumns() : []
                                            contentItem: Text {
                                                anchors.fill: parent
                                                anchors.leftMargin: 12
                                                anchors.rightMargin: primaryColumnCombo.indicator
                                                                   ? primaryColumnCombo.indicator.width + primaryColumnCombo.spacing
                                                                   : 36
                                                text: primaryColumnCombo.displayText
                                                font: primaryColumnCombo.font
                                                color: Material.foreground
                                                opacity: primaryColumnCombo.enabled ? 1 : 0.45
                                                elide: Text.ElideRight
                                                wrapMode: Text.NoWrap
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            delegate: ItemDelegate {
                                                required property int index
                                                required property string modelData
                                                width: primaryColumnCombo.width
                                                implicitHeight: 44
                                                leftPadding: 12
                                                rightPadding: 12
                                                topPadding: 8
                                                bottomPadding: 8
                                                text: modelData
                                                font.pointSize: Theme.fontSize.label
                                            }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.preferredWidth: 120
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 6

                                    Button {
                                        id: mapButton
                                        Layout.alignment: Qt.AlignHCenter
                                        Layout.preferredWidth: 110
                                        text: qsTr("Apply")
                                        enabled: primaryColumnCombo.currentText !== ""
                                                 && secondaryColumnCombo.currentText !== ""
                                                 && mergePage.mappingWarning === ""
                                        Material.background: enabled ? Material.accent : Material.Grey
                                        Material.foreground: "#000000"
                                        onClicked: {
                                            if (!mergePage.stateManager)
                                                return

                                            // Replace any existing mapping via stateManager (it already replaces internally)
                                            var ok = mergePage.stateManager.addColumnMapping(
                                                secondaryColumnCombo.currentText,
                                                primaryColumnCombo.currentText
                                            )

                                            console.log("QML: addColumnMapping returned", ok)
                                            if (typeof mergePage.stateManager.getColumnMappings === "function")
                                                console.log("QML: mappings now", JSON.stringify(mergePage.stateManager.getColumnMappings()))

                                            if (!ok) {
                                                // errorOccurred will show the message from backend
                                                return
                                            }

                                            // Update UI: set ComboBox selections to the applied mapping
                                            function setComboSelection(combo, value) {
                                                if (!combo || !combo.model)
                                                    return
                                                for (var i = 0; i < combo.count; i++) {
                                                    if (combo.model[i] === value) {
                                                        combo.currentIndex = i
                                                        return
                                                    }
                                                }
                                            }

                                            setComboSelection(primaryColumnCombo, primaryColumnCombo.currentText)
                                            setComboSelection(secondaryColumnCombo, secondaryColumnCombo.currentText)

                                            // Ensure models are refreshed
                                            primaryColumnCombo.model = mergePage.stateManager.getMappablePrimaryColumns()
                                            secondaryColumnCombo.model = mergePage.stateManager.getSecondaryColumns()

                                            mergePage.hasJoinMapping = (typeof mergePage.stateManager.getColumnMappings === "function")
                                                                        && mergePage.stateManager.getColumnMappings().length > 0
                                            joinTypeCombo.currentIndex = 0
                                            mergePage.joinTypeIndex = 0
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 100
                                    color: Qt.darker(Material.backgroundColor, 1.15)
                                    border.color: Material.frameColor
                                    radius: 8

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 8

                                        Text {
                                            text: qsTr("Dataset 2 column")
                                            font.pointSize: 11
                                            font.weight: Font.Medium
                                            color: Material.accent
                                        }

                                        ComboBox {
                                            id: secondaryColumnCombo
                                            Layout.fillWidth: true
                                            flat: true
                                            implicitHeight: 40
                                            padding: 8
                                            leftPadding: 12
                                            rightPadding: 36
                                            font.pointSize: Theme.fontSize.label
                                            model: mergePage.stateManager ? mergePage.stateManager.getSecondaryColumns() : []
                                                contentItem: Text {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 12
                                                    anchors.rightMargin: secondaryColumnCombo.indicator
                                                                       ? secondaryColumnCombo.indicator.width + secondaryColumnCombo.spacing
                                                                       : 36
                                                    text: secondaryColumnCombo.displayText
                                                    font: secondaryColumnCombo.font
                                                    color: Material.foreground
                                                    opacity: secondaryColumnCombo.enabled ? 1 : 0.45
                                                    elide: Text.ElideRight
                                                    wrapMode: Text.NoWrap
                                                    verticalAlignment: Text.AlignVCenter
                                                }

                                                delegate: ItemDelegate {
                                                    required property int index
                                                    required property string modelData
                                                    width: secondaryColumnCombo.width
                                                    implicitHeight: 44
                                                    leftPadding: 12
                                                    rightPadding: 12
                                                    topPadding: 8
                                                    bottomPadding: 8
                                                    text: modelData
                                                    font.pointSize: Theme.fontSize.label
                                                }
                                        }
                                    }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: mergePage.mappingWarning !== ""
                                text: "⚠ " + mergePage.mappingWarning
                                font.pointSize: 10
                                font.weight: Font.Medium
                                color: Material.color(Material.DeepOrange)
                                wrapMode: Text.WordWrap
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12

                                Item { Layout.fillWidth: true }

                                Rectangle {
                                    Layout.preferredWidth: 320
                                    Layout.alignment: Qt.AlignVCenter
                                    color: "transparent"
                                    border.width: 0

                                    Text {
                                        anchors.left: parent.left
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.leftMargin: 4
                                        text: {
                                            // reference hasMappings so binding updates when backend emits columnMappingChanged
                                            if (!mergePage.stateManager || !mergePage.stateManager.hasMappings)
                                                return ""
                                            var list = []
                                            if (typeof mergePage.stateManager.getMappingsForDropdown === "function")
                                                list = mergePage.stateManager.getMappingsForDropdown()
                                            if (!list || list.length === 0)
                                                return ""
                                            return list[0].replace(" / ", "/")
                                        }
                                        font.pointSize: 11
                                        font.weight: Font.Medium
                                        color: Material.accent
                                        elide: Text.ElideRight
                                    }
                                }

                                Button {
                                    text: qsTr("Remove pair")
                                    flat: true
                                    font.pointSize: Theme.fontSize.caption
                                    onClicked: {
                                        if (mergePage.stateManager && typeof mergePage.stateManager.clearColumnMappings === "function")
                                            mergePage.stateManager.clearColumnMappings()

                                        // Update UI immediately
                                        primaryColumnCombo.model = mergePage.stateManager ? mergePage.stateManager.getMappablePrimaryColumns() : []
                                        secondaryColumnCombo.model = mergePage.stateManager ? mergePage.stateManager.getSecondaryColumns() : []
                                        mergePage.hasJoinMapping = false
                                        joinTypeCombo.currentIndex = 0
                                        mergePage.joinTypeIndex = 0
                                    }
                                }
                            }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 172
                    color: Qt.darker(Material.backgroundColor, 1.1)
                    border.color: Material.frameColor
                    radius: 12

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 14

                        Text {
                            text: qsTr("Join type")
                            font.pointSize: 15
                            font.weight: Font.Bold
                            color: Material.foreground
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: !mergePage.hasJoinMapping
                            text: qsTr("Define a column pair above to enable inner, left, or right join.")
                            font.pointSize: Theme.fontSize.caption
                            color: Material.foreground
                            opacity: 0.65
                            wrapMode: Text.WordWrap
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 24

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
                                    flat: true
                                    implicitHeight: 48
                                    topPadding: 0
                                    bottomPadding: 0
                                    leftPadding: 0
                                    rightPadding: 0
                                    font.pointSize: Theme.fontSize.label

                                    model: mergePage.hasJoinMapping ? [
                                        qsTr("Inner join"),
                                        qsTr("Left join"),
                                        qsTr("Right join"),
                                        qsTr("Cartesian product")
                                    ] : [
                                        qsTr("Cartesian product")
                                    ]
                                    currentIndex: 0

                                    Component.onCompleted: mergePage.joinTypeIndex = currentIndex

                                    onCurrentIndexChanged: mergePage.joinTypeIndex = currentIndex

                                    contentItem: Text {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: joinTypeCombo.indicator
                                                               ? joinTypeCombo.indicator.width + joinTypeCombo.spacing
                                                               : 36
                                        text: joinTypeCombo.displayText
                                        font: joinTypeCombo.font
                                        color: Material.foreground
                                        opacity: joinTypeCombo.enabled ? 1 : 0.45
                                        elide: Text.ElideRight
                                        wrapMode: Text.NoWrap
                                        verticalAlignment: Text.AlignVCenter
                                    }

                                    delegate: ItemDelegate {
                                        required property int index
                                        required property string modelData
                                        width: joinTypeCombo.width
                                        implicitHeight: 44
                                        leftPadding: 12
                                        rightPadding: 12
                                        topPadding: 8
                                        bottomPadding: 8
                                        text: modelData
                                        font.pointSize: Theme.fontSize.label
                                    }
                                }
                            }
                        }
                    }
                }

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
                            switch (mergePage.resolvedJoinType) {
                            case 0:
                                return qsTr("💡 Keeps only rows where the join column value exists in BOTH databases.")
                            case 1:
                                return qsTr("💡 Keeps all rows from Dataset 1. If a row has no match in Dataset 2, those fields are left empty.")
                            case 2:
                                return qsTr("💡 Keeps all rows from Dataset 2. If a row has no match in Dataset 1, those fields are left empty.")
                            case 3:
                                return qsTr("💡 Combines ALL rows from both (no join column needed).")
                            default:
                                return ""
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
                    Layout.preferredHeight: 320
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
                                enabled: mergePage.canExecuteMerge
                                onClicked: {
                                    if (mergePage.stateManager) {
                                        var joinTypes = ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"]
                                        var jt = mergePage.resolvedJoinType
                                        var keyColumn = jt === 3 ? "" : mergePage.mergeKeyPrimary()
                                        mergePage.previewData = mergePage.stateManager.previewMerge(
                                            keyColumn,
                                            joinTypes[jt]
                                        )
                                        console.log("QML: previewData:", JSON.stringify(mergePage.previewData))
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

                RowLayout {
                    Layout.fillWidth: true

                    Item { Layout.fillWidth: true }

                    Button {
                        id: executeMergeButton
                        text: qsTr("Execute")
                        enabled: mergePage.canExecuteMerge
                        font.pointSize: Theme.fontSize.body
                        font.weight: Font.Bold
                        Material.background: Material.accent
                        Material.foreground: "#000000"
                        Layout.preferredHeight: 40
                        Layout.preferredWidth: 148
                        leftPadding: 14
                        rightPadding: 14
                        topPadding: 0
                        bottomPadding: 0

                        contentItem: Text {
                            text: executeMergeButton.text
                            font: executeMergeButton.font
                            opacity: executeMergeButton.enabled ? 1 : 0.38
                            color: executeMergeButton.Material.foreground
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            width: executeMergeButton.availableWidth
                            height: executeMergeButton.availableHeight
                        }

                        onClicked: {
                            if (mergePage.stateManager) {
                                // Ensure any manual type edits in the controllers are persisted
                                // into the DatasetState before executing the merge.
                                var priFmt = mergePage.stateManager.primaryFormat
                                if (priFmt === "csv" && mergePage.csvController) {
                                    mergePage.stateManager.syncTypesFromController(mergePage.csvController, "primary")
                                } else if (priFmt === "arff" && mergePage.arffController) {
                                    mergePage.stateManager.syncTypesFromController(mergePage.arffController, "primary")
                                }
                                var secFmt = mergePage.stateManager.secondaryFormat
                                if (secFmt === "csv" && mergePage.csvController) {
                                    mergePage.stateManager.syncTypesFromController(mergePage.csvController, "secondary")
                                } else if (secFmt === "arff" && mergePage.arffController) {
                                    mergePage.stateManager.syncTypesFromController(mergePage.arffController, "secondary")
                                }

                                var joinTypes = ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"]
                                var jt = mergePage.resolvedJoinType
                                var keyColumn = jt === 3 ? "" : mergePage.mergeKeyPrimary()
                                var success = mergePage.stateManager.executeMerge(
                                    keyColumn,
                                    joinTypes[jt]
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

    Connections {
        target: mergePage.stateManager

        function onColumnMappingChanged() {
            primaryColumnCombo.model = mergePage.stateManager.getMappablePrimaryColumns()
            secondaryColumnCombo.model = mergePage.stateManager.getSecondaryColumns()
            var mappings = mergePage.stateManager.getColumnMappings()
            var has = mappings && mappings.length > 0
            mergePage.hasJoinMapping = has
            joinTypeCombo.currentIndex = 0
            mergePage.joinTypeIndex = 0
        }

        function onErrorOccurred(message) {
            errorPopup.messageText = message
            errorPopup.open()
        }
    }
}
