import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#16181d"

    function statusColor(status) {
        if (status === "pending")
            return "#e6b84d"
        if (status === "accepted")
            return "#3ecf8e"
        if (status === "rejected")
            return "#e05d5d"
        return "#5b9fd4"
    }

    function statusLabel(status) {
        if (status === "pending")
            return "PENDING"
        if (status === "accepted")
            return "COMMITTED"
        if (status === "rejected")
            return "REJECTED"
        return "INFO"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: "#1e222a"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 10
                spacing: 8

                Text {
                    text: "ANALYSIS"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.letterSpacing: 0.8
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: analysisController && analysisController.pendingCount > 0
                    text: analysisController ? (analysisController.pendingCount + " pending") : ""
                    color: "#e6b84d"
                    font.pixelSize: 11
                }

                Button {
                    text: analysisController && analysisController.analyzing ? "Analyzing…" : "Refresh"
                    enabled: analysisController && !analysisController.analyzing
                    onClicked: analysisController.refresh()
                    background: Rectangle {
                        color: parent.down ? "#2c3340" : (parent.hovered ? "#2a303b" : "#252a33")
                        border.color: "#333845"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: parent.enabled ? "#e8eaed" : "#6d737c"
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitHeight: 22
                    implicitWidth: 88
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: "#333845"
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical

            Rectangle {
                SplitView.preferredHeight: 220
                SplitView.minimumHeight: 140
                color: "#16181d"

                Column {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    Text {
                        text: "CIRCUIT PURPOSE"
                        color: "#9aa0a6"
                        font.pixelSize: 10
                        font.letterSpacing: 0.7
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
                        color: "#e8eaed"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        wrapMode: Text.Wrap
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: "#333845"
                    }

                    Text {
                        width: parent.width
                        text: analysisController ? analysisController.summary : ""
                        color: "#c5cad3"
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                    }
                }
            }

            Rectangle {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 180
                color: "#16181d"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        color: "#1e222a"

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 14
                            text: "REVISION TIMELINE"
                            color: "#9aa0a6"
                            font.pixelSize: 10
                            font.letterSpacing: 0.7
                            font.weight: Font.DemiBold
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: "#333845"
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
                                color: "#333845"
                                visible: index < historyList.count - 1
                            }

                            Rectangle {
                                x: 2
                                y: 12
                                width: 12
                                height: 12
                                radius: 6
                                color: root.statusColor(status)
                                border.color: "#16181d"
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
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        text: timestamp
                                        color: "#6d737c"
                                        font.pixelSize: 11
                                        font.family: "monospace"
                                    }
                                }

                                Text {
                                    width: parent.width
                                    text: title
                                    color: "#e8eaed"
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    visible: summary.length > 0
                                    width: parent.width
                                    text: summary
                                    color: "#c5cad3"
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }

                                Row {
                                    visible: pending
                                    spacing: 8
                                    topPadding: 4

                                    Button {
                                        text: "Commit"
                                        onClicked: analysisController.acceptRevision(revisionId)
                                        background: Rectangle {
                                            color: parent.down ? "#2f7a52" : (parent.hovered ? "#35946a" : "#2d6b4f")
                                            radius: 4
                                        }
                                        contentItem: Text {
                                            text: parent.text
                                            color: "#ffffff"
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        implicitWidth: 64
                                        implicitHeight: 24
                                    }

                                    Button {
                                        text: "Reject"
                                        onClicked: analysisController.rejectRevision(revisionId)
                                        background: Rectangle {
                                            color: parent.down ? "#3a2428" : (parent.hovered ? "#4a2c31" : "#2c3340")
                                            border.color: "#5a3338"
                                            radius: 4
                                        }
                                        contentItem: Text {
                                            text: parent.text
                                            color: "#e8eaed"
                                            font.pixelSize: 12
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        implicitWidth: 64
                                        implicitHeight: 24
                                    }
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: historyList.count === 0 && !(analysisController && analysisController.analyzing)
                            text: "No revision history yet"
                            color: "#9aa0a6"
                            font.pixelSize: 12
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
        color: "#333845"
    }
}
