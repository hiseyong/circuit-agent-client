import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#16181d"

    function severityColor(level) {
        if (level === "error")
            return "#e05d5d"
        if (level === "warning")
            return "#e6b84d"
        return "#5b9fd4"
    }

    function severityLabel(level) {
        if (level === "error")
            return "ERROR"
        if (level === "warning")
            return "WARNING"
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
                anchors.rightMargin: 14

                Text {
                    text: "ISSUES"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.letterSpacing: 0.8
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: agentController && agentController.issueCount > 0
                    text: agentController ? (agentController.issueCount + " found") : ""
                    color: "#9aa0a6"
                    font.pixelSize: 11
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

        ListView {
            id: issueList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 10
            leftMargin: 14
            rightMargin: 14
            topMargin: 12
            bottomMargin: 12
            model: agentController ? agentController.issueModel : null

            delegate: Rectangle {
                required property int index
                required property string severity
                required property string title
                required property string description
                required property string reference
                required property string source
                required property var evidence

                width: issueList.width - issueList.leftMargin - issueList.rightMargin
                implicitHeight: issueBody.implicitHeight + 20
                color: "#1e222a"
                border.color: "#333845"
                radius: 6

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 4
                    radius: 2
                    color: root.severityColor(severity)
                }

                Column {
                    id: issueBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    anchors.leftMargin: 16
                    spacing: 6

                    RowLayout {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: root.severityLabel(severity)
                            color: root.severityColor(severity)
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                        }

                        Text {
                            visible: reference.length > 0
                            text: reference
                            color: "#c5cad3"
                            font.pixelSize: 12
                            font.family: "monospace"
                        }

                        Item { Layout.fillWidth: true }

                        Button {
                            text: "Dismiss"
                            onClicked: agentController.dismissIssueAt(index)
                            background: Rectangle {
                                color: parent.down ? "#3a2428" : "#2c3340"
                                border.color: "#5a3338"
                                radius: 4
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#e8eaed"
                                font.pixelSize: 11
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            implicitWidth: 72
                            implicitHeight: 22
                        }

                        Button {
                            text: "Solve"
                            enabled: agentController
                                     && !agentController.busy
                                     && !agentController.awaitingDecision
                                     && analysisController
                                     && analysisController.projectId.length > 0
                            onClicked: {
                                agentController.solveIssueAt(index)
                                if (appController)
                                    appController.selectTab("chat")
                            }
                            background: Rectangle {
                                color: parent.enabled
                                       ? (parent.down ? "#2f7a52" : "#2d6b4f")
                                       : "#2a303b"
                                radius: 4
                            }
                            contentItem: Text {
                                text: parent.text
                                color: parent.enabled ? "#ffffff" : "#6d737c"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            implicitWidth: 64
                            implicitHeight: 22
                        }
                    }

                    Text {
                        text: title
                        color: "#e8eaed"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        wrapMode: Text.Wrap
                        width: parent.width
                    }

                    Text {
                        text: description
                        color: "#c5cad3"
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        width: parent.width
                    }

                    Text {
                        visible: source.length > 0
                        text: source
                        color: "#6d737c"
                        font.pixelSize: 11
                    }

                    Repeater {
                        model: evidence

                        Rectangle {
                            required property var modelData
                            width: issueBody.width
                            implicitHeight: evCol.implicitHeight + 16
                            color: "#16181d"
                            border.color: "#333845"
                            radius: 4

                            Column {
                                id: evCol
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 8
                                spacing: 3

                                Text {
                                    text: "EVIDENCE"
                                    color: "#5b9fd4"
                                    font.pixelSize: 10
                                    font.letterSpacing: 0.6
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    text: modelData.document
                                          + (modelData.page.length > 0 ? "  ·  p." + modelData.page : "")
                                          + (modelData.section.length > 0 ? "  ·  " + modelData.section : "")
                                    color: "#e8eaed"
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                }

                                Text {
                                    text: modelData.content
                                    color: "#c5cad3"
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                }

                                Text {
                                    text: modelData.source
                                          + (modelData.confidence.length > 0 ? "  ·  " + modelData.confidence : "")
                                    color: "#6d737c"
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                    width: parent.width
                                }
                            }
                        }
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: issueList.count === 0
                text: "No circuit issues"
                color: "#9aa0a6"
                font.pixelSize: 12
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
