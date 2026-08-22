import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#1e222a"

    readonly property color statusColor: {
        const state = agentController ? agentController.agentStatus : "IDLE"
        if (state === "THINKING" || state === "PROCESSING" || state === "WAITING")
            return "#e6b84d"
        if (state === "ERROR")
            return "#e05d5d"
        if (state === "COMPLETED")
            return "#3ecf8e"
        return "#9aa0a6"
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: "#333845"
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 16

        Row {
            spacing: 8

            Rectangle {
                width: 7
                height: 7
                radius: 4
                color: root.statusColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Agent: " + (agentController ? agentController.agentStatus : "IDLE")
                color: root.statusColor
                font.pixelSize: 12
                font.weight: Font.Medium
            }
        }

        Item { Layout.fillWidth: true }
    }
}
