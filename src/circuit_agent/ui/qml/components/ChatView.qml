import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    color: "#ffffff"

    Theme { id: theme }

    property string attachedTitle: ""
    property string attachedReference: ""
    property string attachedSource: ""
    property string attachedDescription: ""

    readonly property bool hasAttached: attachedTitle.length > 0

    function sendCurrent() {
        if (!agentController)
            return
        const text = inputField.text
        agentController.sendMessage(text)
        inputField.text = ""
    }

    function roleLabel(role, isError) {
        if (role === "user")
            return "YOU"
        if (role === "system")
            return isError ? "ERROR" : "SYSTEM"
        return "TRACECIRCUIT"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            visible: root.hasAttached
            Layout.fillWidth: true
            implicitHeight: attachedCol.implicitHeight + 20
            color: theme.subtle

            Column {
                id: attachedCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                anchors.topMargin: 10
                spacing: 6

                Text {
                    text: "ATTACHED CONTEXT"
                    color: theme.muted
                    font.pixelSize: 9
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                }

                Text {
                    width: parent.width
                    text: {
                        const bits = [root.attachedTitle]
                        if (root.attachedReference.length > 0)
                            bits.push(root.attachedReference)
                        return bits.join(" · ")
                    }
                    color: theme.text
                    font.pixelSize: 10
                    font.family: theme.mono
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }

                Text {
                    visible: root.attachedSource.length > 0 || root.attachedDescription.length > 0
                    width: parent.width
                    text: root.attachedSource.length > 0 ? root.attachedSource : root.attachedDescription
                    color: theme.danger
                    font.pixelSize: 9
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
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

        ListView {
            id: chatList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 12
            model: agentController ? agentController.chatModel : null
            leftMargin: 16
            rightMargin: 16
            topMargin: 20
            bottomMargin: 12
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick
            interactive: true
            readonly property bool agentWorking: agentController
                && agentController.busy
                && !agentController.awaitingDecision

            cacheBuffer: 2000

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            function minContentY() {
                return chatList.originY
            }

            function maxContentY() {
                return Math.max(
                    chatList.originY,
                    chatList.originY + chatList.contentHeight - chatList.height
                )
            }

            function scrollBy(delta) {
                chatList.contentY = Math.max(
                    chatList.minContentY(),
                    Math.min(chatList.contentY - delta, chatList.maxContentY())
                )
            }

            function scrollToEnd() {
                Qt.callLater(function () {
                    chatList.forceLayout()
                    chatList.positionViewAtEnd()
                })
            }

            WheelHandler {
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onWheel: function (event) {
                    const dy = event.pixelDelta.y !== 0
                               ? event.pixelDelta.y
                               : event.angleDelta.y
                    chatList.scrollBy(dy)
                    event.accepted = true
                }
            }

            onCountChanged: chatList.scrollToEnd()
            onContentHeightChanged: {
                if (chatList.atYEnd)
                    chatList.scrollToEnd()
            }
            onAgentWorkingChanged: if (agentWorking)
                chatList.scrollToEnd()

            delegate: Item {
                id: chatDelegate
                required property string role
                required property string content
                required property string timestamp
                required property string level
                readonly property bool isError: role === "system" && level === "error"
                readonly property bool isUser: role === "user"
                readonly property bool isSystem: role === "system"
                width: chatList.width - chatList.leftMargin - chatList.rightMargin
                height: bubbleCol.implicitHeight

                Column {
                    id: bubbleCol
                    width: Math.min(parent.width * (chatDelegate.isSystem ? 0.94 : 0.82), parent.width)
                    x: chatDelegate.isUser
                       ? parent.width - width
                       : (chatDelegate.isSystem ? (parent.width - width) / 2 : 0)
                    spacing: 6

                    Row {
                        spacing: 6
                        layoutDirection: chatDelegate.isUser ? Qt.RightToLeft : Qt.LeftToRight
                        width: parent.width

                        Rectangle {
                            width: 18
                            height: 18
                            radius: 9
                            color: chatDelegate.isError
                                   ? theme.dangerSoft
                                   : (chatDelegate.isUser
                                      ? theme.brand
                                      : (chatDelegate.isSystem ? theme.warningSoft : "#eef2fb"))
                            border.color: chatDelegate.isError
                                          ? theme.danger
                                          : (chatDelegate.isUser
                                             ? theme.brand
                                             : (chatDelegate.isSystem ? theme.warning : theme.border))

                            Text {
                                anchors.centerIn: parent
                                text: chatDelegate.isUser ? "Y" : (chatDelegate.isSystem ? "S" : "T")
                                color: chatDelegate.isError
                                       ? theme.danger
                                       : (chatDelegate.isUser
                                          ? "#ffffff"
                                          : (chatDelegate.isSystem ? theme.warning : theme.brand))
                                font.pixelSize: 8
                                font.family: theme.mono
                                font.weight: Font.DemiBold
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.roleLabel(role, chatDelegate.isError)
                            color: chatDelegate.isError ? theme.danger : theme.muted
                            font.pixelSize: 9
                            font.family: theme.mono
                            font.weight: Font.DemiBold
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: timestamp
                            color: theme.muted
                            font.pixelSize: 9
                            font.family: theme.mono
                            opacity: 0.7
                        }
                    }

                    Rectangle {
                        width: parent.width
                        implicitHeight: messageText.height + 20
                        radius: 10
                        color: chatDelegate.isError
                               ? theme.dangerSoft
                               : (chatDelegate.isUser
                                  ? theme.brand
                                  : (chatDelegate.isSystem ? theme.warningSoft : theme.canvas))
                        border.color: chatDelegate.isError
                                      ? "#f0b8b8"
                                      : (chatDelegate.isUser
                                         ? theme.brand
                                         : (chatDelegate.isSystem ? "#ead9a8" : theme.border))

                        Rectangle {
                            visible: !chatDelegate.isSystem
                            width: 10
                            height: 10
                            rotation: 45
                            color: parent.color
                            border.color: parent.border.color
                            x: chatDelegate.isUser ? parent.width - 16 : 6
                            y: -4
                        }

                        Rectangle {
                            visible: !chatDelegate.isSystem
                            width: 14
                            height: 10
                            color: parent.color
                            x: chatDelegate.isUser ? parent.width - 18 : 4
                            y: 0
                        }

                        SelectableText {
                            id: messageText
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 10
                            text: content
                            markdown: role !== "user"
                            color: chatDelegate.isUser ? "#ffffff" : theme.text
                            font.pixelSize: 12
                            font.family: theme.sans
                            selectionColor: chatDelegate.isUser ? "#9db4f8" : "#c9d7f8"
                            selectedTextColor: chatDelegate.isUser ? "#ffffff" : theme.text
                            onContentHeightChanged: Qt.callLater(chatList.forceLayout)
                        }
                    }
                }
            }

            footer: Column {
                visible: chatList.agentWorking
                width: Math.min((chatList.width - chatList.leftMargin - chatList.rightMargin) * 0.82,
                                chatList.width - chatList.leftMargin - chatList.rightMargin)
                height: visible ? implicitHeight : 0
                spacing: 6
                topPadding: 4
                bottomPadding: 8

                Row {
                    spacing: 6

                    Rectangle {
                        width: 18
                        height: 18
                        radius: 9
                        color: "#eef2fb"
                        border.color: theme.border

                        Text {
                            anchors.centerIn: parent
                            text: "T"
                            color: theme.brand
                            font.pixelSize: 8
                            font.family: theme.mono
                            font.weight: Font.DemiBold
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "TRACECIRCUIT"
                        color: theme.muted
                        font.pixelSize: 9
                        font.family: theme.mono
                        font.weight: Font.DemiBold
                    }
                }

                Rectangle {
                    width: parent.width
                    implicitHeight: 40
                    radius: 10
                    color: theme.canvas
                    border.color: theme.border

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        spacing: 6

                        Repeater {
                            model: 3
                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: theme.brand
                                opacity: 0.25

                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    running: chatList.agentWorking
                                    PauseAnimation { duration: index * 160 }
                                    NumberAnimation { to: 1; duration: 240; easing.type: Easing.InOutQuad }
                                    NumberAnimation { to: 0.25; duration: 240; easing.type: Easing.InOutQuad }
                                    PauseAnimation { duration: (2 - index) * 160 }
                                }
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: agentController && agentController.agentStatus === "PROCESSING"
                                  ? "working" : "thinking"
                            color: theme.muted
                            font.pixelSize: 10
                            font.family: theme.mono
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: agentController && agentController.awaitingDecision
            Layout.fillWidth: true
            implicitHeight: 56
            color: theme.warningSoft

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: "Commit or reject the last schematic edit before the next request."
                    color: theme.warning
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                    font.family: theme.sans
                }

                OutlineButton {
                    text: "Commit"
                    implicitWidth: 72
                    implicitHeight: 28
                    labelColor: "#ffffff"
                    fill: theme.success
                    stroke: theme.success
                    onClicked: agentController.acceptPending()
                }

                OutlineButton {
                    text: "Reject"
                    implicitWidth: 72
                    implicitHeight: 28
                    labelColor: theme.danger
                    onClicked: agentController.rejectPending()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 78
            color: theme.surface

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: theme.border
            }

            Rectangle {
                id: composer
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 16
                height: 42
                radius: 4
                color: theme.surface
                border.color: inputField.activeFocus ? theme.brand : theme.border

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
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
                            return "Ask about this check…"
                        }
                        color: theme.text
                        placeholderTextColor: theme.muted
                        font.pixelSize: 11
                        font.family: theme.sans
                        enabled: agentController && !agentController.busy && !agentController.awaitingDecision
                        background: Item {}
                        leftPadding: 0
                        rightPadding: 0
                        Keys.onReturnPressed: function (event) {
                            if (event.modifiers & Qt.ShiftModifier) {
                                event.accepted = false
                                return
                            }
                            root.sendCurrent()
                            event.accepted = true
                        }
                    }

                    Text {
                        text: "Send  ↵"
                        color: sendEnabled() ? theme.brand : theme.muted
                        font.pixelSize: 10
                        font.family: theme.mono
                        font.weight: Font.Medium

                        MouseArea {
                            anchors.fill: parent
                            enabled: sendEnabled()
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: root.sendCurrent()
                        }
                    }
                }
            }
        }
    }

    function sendEnabled() {
        return agentController && !agentController.busy && !agentController.awaitingDecision
               && inputField.text.trim().length > 0
    }
}
