import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    color: "#ffffff"

    Theme { id: theme }

    readonly property color statusColor: {
        const state = agentController ? agentController.agentStatus : "IDLE"
        if (state === "THINKING" || state === "PROCESSING" || state === "WAITING")
            return theme.warning
        if (state === "ERROR")
            return theme.danger
        return theme.success
    }

    readonly property string statusLabel: {
        const state = agentController ? agentController.agentStatus : "IDLE"
        if (state === "THINKING")
            return "thinking"
        if (state === "PROCESSING")
            return "working"
        if (state === "WAITING")
            return "waiting"
        if (state === "ERROR")
            return "ERROR"
        return "READY"
    }

    readonly property string summaryText: {
        if (analysisController && analysisController.analyzing)
            return "analyzing circuit"
        if (agentController && agentController.issueCount > 0)
            return agentController.issueCount + " checks"
        if (analysisController && analysisController.hasAnalysis)
            return "analysis ready"
        if (projectController && projectController.projectStatus)
            return projectController.projectStatus
        return ""
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 1
        color: theme.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 24

        Text {
            text: "●  Agent " + root.statusLabel
            color: root.statusColor
            font.pixelSize: 9
            font.family: theme.mono
            font.weight: Font.Medium
        }

        Text {
            visible: root.summaryText.length > 0
            text: root.summaryText
            color: theme.muted
            font.pixelSize: 9
            font.family: theme.mono
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Item { Layout.fillWidth: true; visible: root.summaryText.length === 0 }

        Text {
            text: "Logs " + (loggingService ? loggingService.logCount : 0)
            color: theme.brand
            font.pixelSize: 9
            font.family: theme.mono
            font.weight: Font.Medium

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (appController) appController.toggleLogs()
            }
        }

        Text {
            text: "UTF-8"
            color: theme.muted
            font.pixelSize: 9
            font.family: theme.mono
        }

        Text {
            text: "KiCad bridge"
            color: theme.muted
            font.pixelSize: 9
            font.family: theme.mono
        }
    }
}
