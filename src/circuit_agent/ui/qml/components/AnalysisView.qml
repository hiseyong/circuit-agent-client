import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    color: "#ffffff"

    Theme { id: theme }

    function statusColor(status) {
        if (status === "pending")
            return theme.warning
        if (status === "accepted")
            return theme.success
        if (status === "rejected")
            return theme.danger
        if (status === "reverted")
            return theme.muted
        return theme.brand
    }

    function statusLabel(status) {
        if (status === "pending")
            return "PENDING"
        if (status === "accepted")
            return "COMMITTED"
        if (status === "rejected")
            return "REJECTED"
        if (status === "reverted")
            return "REVERTED"
        return "INFO"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: theme.surface

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 20
                spacing: 8

                Text {
                    text: "ANALYSIS"
                    color: theme.muted
                    font.pixelSize: 12
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: analysisController && analysisController.pendingCount > 0
                    text: analysisController ? (analysisController.pendingCount + " pending") : ""
                    color: theme.warning
                    font.pixelSize: 11
                    font.family: theme.mono
                }

                OutlineButton {
                    text: analysisController && analysisController.analyzing ? "Analyzing…" : "Refresh"
                    enabled: analysisController && !analysisController.analyzing
                    implicitWidth: 82
                    implicitHeight: 28
                    labelColor: theme.text
                    onClicked: analysisController.refresh()
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: theme.border
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical

            Rectangle {
                SplitView.preferredHeight: 220
                SplitView.minimumHeight: 140
                color: theme.surface

                Column {
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 10

                    Text {
                        text: "CIRCUIT PURPOSE"
                        color: theme.muted
                        font.pixelSize: 11
                        font.family: theme.mono
                        font.weight: Font.DemiBold
                    }

                    Text {
                        width: parent.width
                        text: {
                            if (!analysisController)
                                return ""
                            if (analysisController.analyzing)
                                return "Sending components and connections to the backend…"
                            if (analysisController.hasAnalysis)
                                return analysisController.purpose
                            return "Open a KiCad project to analyze the circuit."
                        }
                        color: theme.text
                        font.pixelSize: 16
                        font.family: theme.sans
                        font.weight: Font.Bold
                        wrapMode: Text.Wrap
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: theme.border
                    }

                    Text {
                        width: parent.width
                        text: analysisController ? analysisController.summary : ""
                        color: theme.text
                        font.pixelSize: 11
                        font.family: theme.sans
                        wrapMode: Text.Wrap
                    }
                }
            }

            Rectangle {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 180
                color: theme.surface

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        color: theme.surface

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 22
                            text: "REVISION TIMELINE"
                            color: theme.muted
                            font.pixelSize: 11
                            font.family: theme.mono
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: theme.border
                        }
                    }

                    ListView {
                        id: historyList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 0
                        model: analysisController ? analysisController.historyModel : null
                        leftMargin: 14
                        rightMargin: 14
                        topMargin: 12
                        bottomMargin: 12

                        onCountChanged: Qt.callLater(function () {
                            historyList.positionViewAtEnd()
                        })

                        delegate: Item {
                            required property string revisionId
                            required property string kind
                            required property string title
                            required property string summary
                            required property string status
                            required property string timestamp
                            required property bool pending
                            required property int index

                            width: historyList.width - historyList.leftMargin - historyList.rightMargin
                            height: entryBody.implicitHeight + 20

                            Rectangle {
                                x: 7
                                width: 2
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                color: theme.border
                                visible: index < historyList.count - 1
                            }

                            Rectangle {
                                x: 2
                                y: 12
                                width: 12
                                height: 12
                                radius: 6
                                color: root.statusColor(status)
                                border.color: theme.surface
                                border.width: 2
                            }

                            Column {
                                id: entryBody
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.leftMargin: 28
                                anchors.topMargin: 6
                                spacing: 4

                                Row {
                                    spacing: 8

                                    Text {
                                        text: root.statusLabel(status)
                                        color: root.statusColor(status)
                                        font.pixelSize: 10
                                        font.family: theme.mono
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        text: timestamp
                                        color: theme.muted
                                        font.pixelSize: 10
                                        font.family: theme.mono
                                    }
                                }

                                Text {
                                    width: parent.width
                                    text: title
                                    color: theme.text
                                    font.pixelSize: 13
                                    font.family: theme.sans
                                    font.weight: Font.Bold
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    visible: summary.length > 0
                                    width: parent.width
                                    text: summary
                                    color: theme.muted
                                    font.pixelSize: 11
                                    font.family: theme.sans
                                    wrapMode: Text.Wrap
                                }

                                Row {
                                    visible: !pending && analysisController
                                             && revisionId === analysisController.revertableRevisionId
                                    spacing: 8
                                    topPadding: 4

                                    OutlineButton {
                                        text: "Revert"
                                        implicitWidth: 64
                                        implicitHeight: 24
                                        labelColor: theme.danger
                                        onClicked: analysisController.revertLatest()
                                    }
                                }

                                Row {
                                    visible: pending
                                    spacing: 8
                                    topPadding: 4

                                    OutlineButton {
                                        text: "Commit"
                                        implicitWidth: 64
                                        implicitHeight: 24
                                        labelColor: "#ffffff"
                                        fill: theme.success
                                        stroke: theme.success
                                        onClicked: analysisController.acceptRevision(revisionId)
                                    }

                                    OutlineButton {
                                        text: "Reject"
                                        implicitWidth: 64
                                        implicitHeight: 24
                                        labelColor: theme.danger
                                        onClicked: analysisController.rejectRevision(revisionId)
                                    }
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: historyList.count === 0 && !(analysisController && analysisController.analyzing)
                            text: "No revision history yet"
                            color: theme.muted
                            font.pixelSize: 12
                            font.family: theme.sans
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 1
        color: theme.border
    }
}
