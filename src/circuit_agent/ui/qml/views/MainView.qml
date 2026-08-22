import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../components"

Item {
    id: root

    readonly property color bg: "#16181d"
    readonly property color panel: "#1e222a"
    readonly property color border: "#333845"
    readonly property color text: "#e8eaed"
    readonly property color muted: "#9aa0a6"

    function tabVisible(tabId) {
        if (!appController)
            return false
        if (tabId === "schematic")
            return appController.showSchematic
        if (tabId === "analysis")
            return appController.showAnalysis
        if (tabId === "issues")
            return appController.showIssues
        if (tabId === "chat")
            return appController.showChat
        return false
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: root.panel

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                Text {
                    text: appController ? appController.title : "Circuit Agent"
                    color: root.text
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }

                Button {
                    id: tabsButton
                    text: "Tabs"
                    onClicked: tabMenu.open()
                    background: Rectangle {
                        color: tabsButton.down ? "#2c3340" : (tabsButton.hovered ? "#2a303b" : "#252a33")
                        border.color: root.border
                        radius: 4
                    }
                    contentItem: Text {
                        text: tabsButton.text
                        color: root.text
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitHeight: 26
                    implicitWidth: 56

                    Menu {
                        id: tabMenu
                        modal: true

                        MenuItem {
                            text: "Schematic"
                            checkable: true
                            checked: appController ? appController.showSchematic : false
                            onToggled: appController.setTabVisible("schematic", checked)
                        }
                        MenuItem {
                            text: "Analysis"
                            checkable: true
                            checked: appController ? appController.showAnalysis : false
                            onToggled: appController.setTabVisible("analysis", checked)
                        }
                        MenuItem {
                            text: "Issues"
                            checkable: true
                            checked: appController ? appController.showIssues : false
                            onToggled: appController.setTabVisible("issues", checked)
                        }
                        MenuItem {
                            text: "Chat"
                            checkable: true
                            checked: appController ? appController.showChat : false
                            onToggled: appController.setTabVisible("chat", checked)
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                StatusBadge {
                    label: "KiCad"
                    statusText: kicadController ? kicadController.status : "DISCONNECTED"
                    connected: kicadController ? kicadController.connected : false
                    mock: kicadController && kicadController.status === "MOCK"
                }

                StatusBadge {
                    label: "Server"
                    statusText: appController ? appController.serverStatus : "DISCONNECTED"
                    connected: appController ? appController.serverConnected : false
                    mock: appController && appController.serverStatus === "MOCK"
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: root.border
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            color: root.panel
            visible: appController !== null

            Row {
                id: tabRow
                anchors.fill: parent
                anchors.leftMargin: 8
                spacing: 4

                Repeater {
                    model: [
                        { "id": "schematic", "title": "Schematic" },
                        { "id": "analysis", "title": "Analysis" },
                        { "id": "issues", "title": "Issues" },
                        { "id": "chat", "title": "Chat" }
                    ]

                    Rectangle {
                        required property var modelData
                        visible: root.tabVisible(modelData.id)
                        height: 24
                        width: tabLabel.implicitWidth + 20
                        anchors.verticalCenter: parent.verticalCenter
                        radius: 4
                        color: (appController && appController.activeTab === modelData.id) ? "#2a3f5f" : "transparent"
                        border.color: (appController && appController.activeTab === modelData.id) ? "#3d5f86" : "transparent"

                        Text {
                            id: tabLabel
                            anchors.centerIn: parent
                            text: modelData.title
                            color: (appController && appController.activeTab === modelData.id) ? "#e8eaed" : "#9aa0a6"
                            font.pixelSize: 12
                            font.weight: (appController && appController.activeTab === modelData.id) ? Font.DemiBold : Font.Normal
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: appController.selectTab(modelData.id)
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: root.border
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical

            SplitView {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 280
                orientation: Qt.Horizontal

                Sidebar {
                    SplitView.preferredWidth: 240
                    SplitView.minimumWidth: 180
                }

                Item {
                    SplitView.fillWidth: true
                    SplitView.minimumWidth: 360

                    SchematicView {
                        anchors.fill: parent
                        visible: appController && appController.activeTab === "schematic"
                    }

                    AnalysisView {
                        anchors.fill: parent
                        visible: appController && appController.activeTab === "analysis"
                    }

                    IssuesView {
                        anchors.fill: parent
                        visible: appController && appController.activeTab === "issues"
                    }

                    ChatView {
                        anchors.fill: parent
                        visible: appController && appController.activeTab === "chat"
                    }
                }
            }

            LogView {
                SplitView.preferredHeight: 140
                SplitView.minimumHeight: 80
            }
        }

        AgentStatus {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
        }
    }
}
