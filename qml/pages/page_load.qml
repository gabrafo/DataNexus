import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Dialogs

/** Initial file loading page (CSV or ARFF). */
Rectangle {
    id: loadPage
    property var csvController: null
    property var arffController: null
    property var onDataLoaded: null
    
    anchors.fill: parent
    color: Material.backgroundColor

    FileDialog {
        id: fileDialog
        title: "Selecione um arquivo de dados"
        nameFilters: ["Arquivos de dados (*.csv *.arff)", "CSV (*.csv)", "ARFF (*.arff)"]
        onAccepted: {
            var filePath = selectedFile.toString()
            if (filePath.toLowerCase().endsWith(".csv")) {
                // CSV: open delimiter selection dialog
                delimiterDialog.visible = true
            } else if (filePath.toLowerCase().endsWith(".arff")) {
                // ARFF: load directly
                if (loadPage.arffController) {
                    loadPage.arffController.loadArff(selectedFile)
                }
            }
        }
    }
    
    Dialog {
        id: delimiterDialog
        title: "Escolha o separador do CSV"
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        
        Column {
            spacing: 16
            width: 400
            
            Text {
                text: "Qual caractere separa as colunas do seu arquivo?"
                font.pointSize: 11
                color: Material.foreground
                wrapMode: Text.WordWrap
                width: parent.width
            }
            
            Column {
                spacing: 12
                width: parent.width
                
                RadioButton {
                    id: autoDetectRadio
                    text: "Detectar automaticamente"
                    checked: true
                }
                
                RadioButton {
                    id: semicolonRadio
                    text: "Ponto e vírgula (;)"
                }
                
                RadioButton {
                    id: commaRadio
                    text: "Vírgula (,)"
                }
                
                RadioButton {
                    id: tabRadio
                    text: "Tab (\\t)"
                }
                
                RadioButton {
                    id: pipeRadio
                    text: "Pipe (|)"
                }
                
                Row {
                    spacing: 8
                    width: parent.width
                    
                    RadioButton {
                        id: customRadio
                        text: "Personalizado:"
                    }
                    
                    TextField {
                        id: customDelimiterField
                        width: 60
                        placeholderText: ":"
                        enabled: customRadio.checked
                        maximumLength: 1
                    }
                }
            }
        }
        
        onAccepted: {
            var delimiter = ""
            
            if (autoDetectRadio.checked) {
                delimiter = ""
            } else if (semicolonRadio.checked) {
                delimiter = ";"
            } else if (commaRadio.checked) {
                delimiter = ","
            } else if (tabRadio.checked) {
                delimiter = "tab"
            } else if (pipeRadio.checked) {
                delimiter = "|"
            } else if (customRadio.checked) {
                delimiter = customDelimiterField.text
            }
            
            if (loadPage.csvController) {
                loadPage.csvController.loadCsv(fileDialog.selectedFile, delimiter)
            }
        }
        
        onRejected: {
            autoDetectRadio.checked = true
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: Theme.spacing.xl
        width: parent.width

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: qsTr("DataNexus")
            color: Material.accent
            font.pointSize: Theme.fontSize.display
            font.weight: Font.Bold
            font.letterSpacing: 6
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: qsTr("Give a golden touch to your data")
            font.pointSize: Theme.fontSize.h3
            color: Material.foreground
            opacity: 0.6
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 60
            height: 2
            color: Material.accent
            opacity: 0.5
        }

        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 280
            height: 56
            text: qsTr("LOAD FILE")
            font.pointSize: Theme.fontSize.subtitle
            font.weight: Font.Medium
            font.letterSpacing: 1
            Material.background: Material.accent
            Material.foreground: "#000000"
            Material.elevation: 4
            onClicked: fileDialog.open()
        }

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: Theme.spacing.sm

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Supported formats")
                font.pointSize: Theme.fontSize.label
                color: Material.foreground
                opacity: 0.4
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.spacing.md
                
                Text { 
                    text: "CSV" 
                    font.pointSize: Theme.fontSize.body
                    font.weight: Font.Medium
                    color: Material.accent 
                    opacity: 0.8
                }
                Text { 
                    text: "•" 
                    font.pointSize: Theme.fontSize.body
                    color: Material.foreground 
                    opacity: 0.3 
                }
                Text { 
                    text: "ARFF" 
                    font.pointSize: Theme.fontSize.body
                    font.weight: Font.Medium
                    color: Material.accent 
                    opacity: 0.8
                }
            }
        }
    }

    // onDataLoaded callback is set by main.qml and runs once on initial load
    Connections {
        target: loadPage.csvController
        function onDataframeChanged() {
            if (loadPage.onDataLoaded) loadPage.onDataLoaded("csv")
        }
    }
    
    Connections {
        target: loadPage.arffController
        function onDataLoaded() {
            if (loadPage.onDataLoaded) loadPage.onDataLoaded("arff")
        }
    }
}
