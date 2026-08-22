import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import "views"
import "components"

ApplicationWindow {
    id: root
    width: 1280
    height: 800
    minimumWidth: 960
    minimumHeight: 600
    visible: true
    title: appController ? appController.title : "Circuit Agent"
    color: "#16181d"

    MainView {
        anchors.fill: parent
    }

    PdfPreviewPopup {}
}
