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
                required property bool highlighted
                required property var highlightTargets

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

                    Row {
                        spacing: 8
                        width: parent.width

                        Switch {
                            id: highlightSwitch
                            checked: highlighted
                            enabled: highlightTargets.length > 0
                            onClicked: agentController.toggleIssueHighlightAt(index)
                            indicator: Rectangle {
                                implicitWidth: 32
                                implicitHeight: 18
                                x: highlightSwitch.leftPadding
                                y: parent.height / 2 - height / 2
                                radius: 9
                                color: highlightSwitch.checked ? "#2d6b4f" : "#2a303b"
                                border.color: highlightSwitch.checked ? "#3ecf8e" : "#333845"

                                Rectangle {
                                    x: highlightSwitch.checked ? parent.width - width - 2 : 2
                                    y: 2
                                    width: 14
                                    height: 14
                                    radius: 7
                                    color: highlightSwitch.enabled ? "#e8eaed" : "#6d737c"
                                }
                            }
                            implicitWidth: 36
                            implicitHeight: 22
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: highlightTargets.length > 0
                                  ? "Highlight in schematic  ·  " + highlightTargets.join(", ")
                                  : "Highlight in schematic"
                            color: highlightSwitch.enabled ? "#c5cad3" : "#6d737c"
                            font.pixelSize: 12
                        }
                    }

                    Text {
                        visible: source.length > 0
                        text: "Issue source: " + source
                        color: "#9aa0a6"
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        width: parent.width
                    }

                    Repeater {
                        model: evidence

                        Rectangle {
                            required property var modelData
                            width: issueBody.width
                            implicitHeight: evCol.implicitHeight + 16
                            color: "#16181d"
                            border.color: modelData.canOpen ? "#3d5a80" : "#333845"
                            radius: 4

                            Column {
                                id: evCol
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 8
                                spacing: 8

                                Row {
                                    width: parent.width
                                    spacing: 8

                                    Text {
                                        text: "EVIDENCE"
                                        color: "#5b9fd4"
                                        font.pixelSize: 10
                                        font.letterSpacing: 0.6
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        visible: modelData.canOpen
                                        text: modelData.pageNumber > 0
                                              ? "Tap to open PDF  ·  p." + modelData.pageNumber
                                              : "Tap to open PDF"
                                        color: "#5b9fd4"
                                        font.pixelSize: 10
                                    }
                                }

                                Column {
                                    width: parent.width
                                    spacing: 4

                                    Text {
                                        text: "Excerpt"
                                        color: "#e8eaed"
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        text: "Quoted passage used to support this issue."
                                        color: "#6d737c"
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    SelectableText {
                                        width: parent.width
                                        text: modelData.content.length > 0
                                              ? modelData.content
                                              : "(empty excerpt)"
                                        color: "#c5cad3"
                                        font.pixelSize: 12
                                    }
                                }

                                Column {
                                    width: parent.width
                                    spacing: 4

                                    Text {
                                        text: "Source"
                                        color: "#e8eaed"
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        text: "Where this excerpt came from."
                                        color: "#6d737c"
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Text {
                                        visible: modelData.source.length > 0
                                        text: "Kind: " + modelData.source
                                        color: "#c5cad3"
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Text {
                                        visible: modelData.document.length > 0
                                        text: "Document: " + modelData.document
                                        color: "#c5cad3"
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Text {
                                        visible: modelData.location.length > 0
                                        text: "Location: " + modelData.location
                                        color: "#c5cad3"
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Text {
                                        visible: modelData.confidence.length > 0
                                        text: "Confidence: " + modelData.confidence
                                        color: "#c5cad3"
                                        font.pixelSize: 12
                                    }

                                    Text {
                                        visible: modelData.url.length > 0
                                        text: "PDF: " + modelData.url
                                        color: "#5b9fd4"
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Repeater {
                                        model: modelData.extras
                                        Text {
                                            required property string modelData
                                            width: evCol.width
                                            text: modelData
                                            color: "#9aa0a6"
                                            font.pixelSize: 12
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }

                                Column {
                                    width: parent.width
                                    spacing: 4

                                    Text {
                                        text: "Original JSON"
                                        color: "#e8eaed"
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        text: "Payload as received from the analysis API."
                                        color: "#6d737c"
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                        width: parent.width
                                    }

                                    Rectangle {
                                        width: parent.width
                                        implicitHeight: jsonText.height + 12
                                        color: "#12141a"
                                        border.color: "#333845"
                                        radius: 4

                                        SelectableText {
                                            id: jsonText
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: 6
                                            text: modelData.json
                                            color: "#c5cad3"
                                            font.pixelSize: 11
                                            font.family: "monospace"
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                z: 1
                                enabled: modelData.canOpen && evidencePreview
                                hoverEnabled: enabled
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: evidencePreview.openUrl(
                                    modelData.url,
                                    modelData.pageNumber,
                                    modelData.document,
                                    modelData.content
                                )
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
