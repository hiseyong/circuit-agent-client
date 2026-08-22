import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#16181d"

    function sendCurrent() {
        if (!agentController)
            return
        const text = inputField.text
        agentController.sendMessage(text)
        inputField.text = ""
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

                Text {
                    text: "CHAT"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.letterSpacing: 0.8
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: analysisController && analysisController.projectId.length > 0
                    text: "Linked"
                    color: "#3ecf8e"
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
            id: chatList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 10
            model: agentController ? agentController.chatModel : null
            leftMargin: 14
            rightMargin: 14
            topMargin: 12
            bottomMargin: 12
            readonly property bool agentWorking: agentController
                && agentController.busy
                && !agentController.awaitingDecision

            onCountChanged: Qt.callLater(function () {
                chatList.positionViewAtEnd()
            })
            onAgentWorkingChanged: if (agentWorking)
                Qt.callLater(function () { chatList.positionViewAtEnd() })

            delegate: Column {
                required property string role
                required property string content
                required property string timestamp
                width: chatList.width - chatList.leftMargin - chatList.rightMargin
                spacing: 4

                Row {
                    spacing: 8
                    Text {
                        text: role === "user" ? "User" : (role === "system" ? "System" : "Agent")
                        color: role === "user" ? "#5b9fd4" : (role === "system" ? "#e05d5d" : "#3ecf8e")
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: timestamp
                        color: "#6d737c"
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    width: role === "user"
                           ? Math.min(parent.width, messageText.implicitWidth + 20)
                           : parent.width
                    height: messageText.contentHeight + 16
                    radius: 6
                    color: role === "user" ? "#223247" : (role === "system" ? "#3a2428" : "#252a33")
                    border.color: role === "user" ? "#2f4a6a" : "#333845"

                    SelectableText {
                        id: messageText
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 10
                        text: content
                        markdown: role !== "user"
                        color: "#e8eaed"
                        flickable: chatList
                    }
                }
            }

            footer: Column {
                visible: chatList.agentWorking
                width: chatList.width - chatList.leftMargin - chatList.rightMargin
                height: visible ? implicitHeight : 0
                spacing: 4
                topPadding: 0
                bottomPadding: 2

                Row {
                    spacing: 8
                    Text {
                        text: "Agent"
                        color: "#3ecf8e"
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: agentController && agentController.agentStatus === "PROCESSING"
                              ? "working"
                              : "thinking"
                        color: "#6d737c"
                        font.pixelSize: 11
                    }
                }

                Rectangle {
                    width: typingRow.implicitWidth + 20
                    height: 36
                    radius: 6
                    color: "#252a33"
                    border.color: "#333845"

                    Row {
                        id: typingRow
                        anchors.centerIn: parent
                        spacing: 6

                        Repeater {
                            model: 3
                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: "#3ecf8e"
                                opacity: 0.25

                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    running: chatList.agentWorking
                                    PauseAnimation { duration: index * 160 }
                                    NumberAnimation { to: 1; duration: 240; easing.type: Easing.InOutQuad }
                                    NumberAnimation { to: 0.25; duration: 240; easing.type: Easing.InOutQuad }
                                    PauseAnimation { duration: (2 - index) * 160 }
                                }

                                SequentialAnimation on y {
                                    loops: Animation.Infinite
                                    running: chatList.agentWorking
                                    PauseAnimation { duration: index * 160 }
                                    NumberAnimation { to: -3; duration: 240; easing.type: Easing.InOutQuad }
                                    NumberAnimation { to: 0; duration: 240; easing.type: Easing.InOutQuad }
                                    PauseAnimation { duration: (2 - index) * 160 }
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: agentController && agentController.awaitingDecision
            Layout.fillWidth: true
            implicitHeight: 56
            color: "#2a2416"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: "Commit or reject the last schematic edit before the next request."
                    color: "#e6b84d"
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                }

                Button {
                    text: "Commit"
                    onClicked: agentController.acceptPending()
                    background: Rectangle {
                        color: parent.down ? "#2f7a52" : "#2d6b4f"
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
                    implicitWidth: 72
                    implicitHeight: 28
                }

                Button {
                    text: "Reject"
                    onClicked: agentController.rejectPending()
                    background: Rectangle {
                        color: parent.down ? "#3a2428" : "#2c3340"
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
                    implicitWidth: 72
                    implicitHeight: 28
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: "#1e222a"

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: "#333845"
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                TextField {
                    id: inputField
                    Layout.fillWidth: true
                    placeholderText: {
                        if (agentController && agentController.awaitingDecision)
                            return "Commit or reject the last edit first"
                        if (agentController && agentController.busy)
                            return agentController.agentStatus === "PROCESSING"
                                   ? "Agent is working…"
                                   : "Agent is thinking…"
                        if (!analysisController || analysisController.projectId.length === 0)
                            return "Open a project and wait for analysis first"
                        return "Ask a question or request a schematic change..."
                    }
                    color: "#e8eaed"
                    placeholderTextColor: "#6d737c"
                    enabled: agentController && !agentController.busy && !agentController.awaitingDecision
                    background: Rectangle {
                        color: "#16181d"
                        border.color: inputField.activeFocus ? "#5b9fd4" : "#333845"
                        radius: 4
                    }
                    leftPadding: 10
                    rightPadding: 10
                    Keys.onReturnPressed: function (event) {
                        if (event.modifiers & Qt.ShiftModifier) {
                            event.accepted = false
                            return
                        }
                        root.sendCurrent()
                        event.accepted = true
                    }
                }

                Button {
                    id: sendButton
                    text: "Send"
                    enabled: agentController && !agentController.busy && !agentController.awaitingDecision && inputField.text.trim().length > 0
                    onClicked: root.sendCurrent()
                    background: Rectangle {
                        color: sendButton.enabled ? (sendButton.down ? "#3d7eb0" : "#4a8fc4") : "#2a303b"
                        radius: 4
                    }
                    contentItem: Text {
                        text: sendButton.text
                        color: sendButton.enabled ? "#ffffff" : "#6d737c"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitWidth: 72
                    implicitHeight: 32
                }
            }
        }
    }
}
