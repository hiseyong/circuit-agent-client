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

        ListView {
            id: logList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: loggingService ? loggingService.logModel : null
            leftMargin: 14
            rightMargin: 14
            topMargin: 6
            bottomMargin: 6
            spacing: 2

            onCountChanged: Qt.callLater(function () {
                logList.positionViewAtEnd()
            })

            delegate: Text {
                required property string line
                required property string level
                width: logList.width - logList.leftMargin - logList.rightMargin
                text: line
                color: level === "ERROR" ? "#e05d5d" : (level === "WARNING" ? "#e6b84d" : "#9aa0a6")
                font.pixelSize: 12
                font.family: "monospace"
                wrapMode: Text.Wrap
            }
        }
    }
}
