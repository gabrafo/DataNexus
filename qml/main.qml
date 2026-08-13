import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Dialogs
import QtQuick.Window 2.15
import App 1.0

/**
 * DataNexus - Main application window.
 * Flow: page_hub -> (page_view | page_merge -> page_preprocess)
 */
ApplicationWindow {
    id: mainWindow
    width: 1000
    height: 700
    visible: true
    visibility: Window.Maximized
    title: "DataNexus"
    
    Material.theme: Material.Dark
    Material.primary: Material.BlueGrey
    Material.accent: Material.Amber

    CSVController {
        id: csvController
        onErrorOccurred: msg => showMessage("Erro", msg)
        onSuccessOccurred: msg => showMessage("Sucesso", msg)
    }
    
    ARFFController {
        id: arffController
        onErrorOccurred: msg => showMessage("Erro", msg)
        onSuccessOccurred: msg => showMessage("Sucesso", msg)
    }
    
    StateController {
        id: stateController
        onErrorOccurred: msg => showMessage("Erro", msg)
        onMergeCompleted: msg => showMessage("Sucesso", msg)
    }
    
    NavigationController {
        id: navController
    }

    function showMessage(title, text) {
        messageDialog.title = title
        messageDialog.text = text
        messageDialog.open()
    }
    
    MessageDialog {
        id: messageDialog
        text: ""
    }

    StackView {
        id: navigationStack
        anchors.fill: parent
        
        Component.onCompleted: {
            push("pages/page_hub.qml", {
                "csvController": csvController,
                "arffController": arffController,
                "stateController": stateController,
                "navController": navController,
                "stack": navigationStack
            })
        }
    }
}
