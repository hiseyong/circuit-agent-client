import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import "views"
import "components"

ApplicationWindow {
    id: root
    width: 1440
    height: 900
    minimumWidth: 1080
    minimumHeight: 640
    visible: true
    title: appController ? appController.title : "TraceCircuit"
    color: "#ffffff"

    MainView {
        anchors.fill: parent
    }

    PdfPreviewPopup {}
}
