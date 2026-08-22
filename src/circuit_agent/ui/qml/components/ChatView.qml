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

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 14
                text: "CHAT"
                color: "#9aa0a6"
                font.pixelSize: 11
                font.letterSpacing: 0.8
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

            onCountChanged: Qt.callLater(function () {
                chatList.positionViewAtEnd()
            })

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
                    width: Math.min(parent.width, messageText.implicitWidth + 20)
                    height: messageText.implicitHeight + 16
                    radius: 6
                    color: role === "user" ? "#223247" : (role === "system" ? "#3a2428" : "#252a33")
                    border.color: role === "user" ? "#2f4a6a" : "#333845"

                    Text {
                        id: messageText
                        anchors.fill: parent
                        anchors.margins: 10
                        text: content
                        color: "#e8eaed"
                        wrapMode: Text.Wrap
                        width: chatList.width - chatList.leftMargin - chatList.rightMargin - 40
                        font.pixelSize: 13
                    }
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
                    placeholderText: "Type a message..."
                    color: "#e8eaed"
                    placeholderTextColor: "#6d737c"
                    enabled: agentController && !agentController.busy
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
                    enabled: agentController && !agentController.busy && inputField.text.trim().length > 0
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
