import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#14161b"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            color: "#1e222a"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 14
                text: "LOGS"
                color: "#9aa0a6"
                font.pixelSize: 11
                font.letterSpacing: 0.8
                font.weight: Font.DemiBold
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: "#333845"
            }
        }

        Flickable {
            id: logFlick
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: logText.height + 12
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick

            SelectableText {
                id: logText
                x: 14
                y: 6
                width: logFlick.width - 28
                height: contentHeight
                text: loggingService ? loggingService.plainText : ""
                color: "#9aa0a6"
                font.pixelSize: 12
                font.family: "monospace"
                flickable: logFlick
            }

            Connections {
                target: loggingService
                function onLogAdded() {
                    Qt.callLater(function () {
                        logFlick.contentY = Math.max(0, logFlick.contentHeight - logFlick.height)
                    })
                }
            }
        }
    }
}
