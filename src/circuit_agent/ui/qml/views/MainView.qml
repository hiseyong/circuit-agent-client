import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."
import "../components"

Item {
    id: root

    Theme { id: theme }

    property int selectedIssueIndex: 0
    property string attachedTitle: ""
    property string attachedReference: ""
    property string attachedSource: ""
    property string attachedDescription: ""
    property string attachedSeverity: ""

    readonly property var centerTabs: [
        { "id": "schematic", "title": "Schematic" },
        { "id": "analysis", "title": "Analysis" },
        { "id": "pcb3d", "title": "PCB 3D" },
        { "id": "spice", "title": "SPICE" }
    ]

    function rememberIssue(index, title, reference, source, description, severity) {
        selectedIssueIndex = index
        attachedTitle = title
        attachedReference = reference
        attachedSource = source
        attachedDescription = description
        attachedSeverity = severity
    }

    function connectionColor(connected, mock) {
        if (mock)
            return theme.warning
        return connected ? theme.success : theme.danger
    }

    function connectionLabel(name, connected, mock, statusText) {
        if (mock)
            return "●  " + name + " mock"
        if (connected)
            return "●  " + name + " connected"
        return "●  " + name + " " + (statusText || "disconnected").toLowerCase()
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
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12

                Text {
                    text: "TraceCircuit"
                    color: theme.text
                    font.pixelSize: 16
                    font.family: theme.sans
                    font.weight: Font.Bold
                }

                Text {
                    text: "/"
                    color: theme.muted
                    font.pixelSize: 11
                    font.family: theme.mono
                }

                Text {
                    text: projectController ? projectController.projectFileName : ""
                    color: theme.text
                    font.pixelSize: 11
                    font.family: theme.mono
                    font.weight: Font.Medium
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 280
                }

                Text {
                    visible: analysisController && analysisController.historyCount > 0
                    text: analysisController
                          ? ("·  change set #" + analysisController.historyCount)
                          : ""
                    color: theme.muted
                    font.pixelSize: 10
                    font.family: theme.mono
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: root.connectionLabel(
                        "KiCad",
                        kicadController && kicadController.connected,
                        kicadController && kicadController.status === "MOCK",
                        kicadController ? kicadController.status : ""
                    )
                    color: root.connectionColor(
                        kicadController && kicadController.connected,
                        kicadController && kicadController.status === "MOCK"
                    )
                    font.pixelSize: 10
                    font.family: theme.mono
                    font.weight: Font.Medium
                }

                Text {
                    text: root.connectionLabel(
                        "Server",
                        appController && appController.serverConnected,
                        appController && appController.serverStatus === "MOCK",
                        appController ? appController.serverStatus : ""
                    )
                    color: root.connectionColor(
                        appController && appController.serverConnected,
                        appController && appController.serverStatus === "MOCK"
                    )
                    font.pixelSize: 10
                    font.family: theme.mono
                    font.weight: Font.Medium
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

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: theme.surface

            Row {
                id: tabRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.leftMargin: 18
                spacing: 34

                Repeater {
                    model: root.centerTabs

                    Item {
                        required property var modelData
                        width: tabLabel.implicitWidth
                        height: parent.height

                        Text {
                            id: tabLabel
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.title
                            color: (appController && appController.activeTab === modelData.id)
                                   ? theme.text : theme.muted
                            font.pixelSize: 10
                            font.family: theme.mono
                            font.weight: (appController && appController.activeTab === modelData.id)
                                         ? Font.Medium : Font.Normal
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 2
                            color: theme.brand
                            visible: appController && appController.activeTab === modelData.id
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
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
                color: theme.border
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Sidebar {
                SplitView.preferredWidth: 300
                SplitView.minimumWidth: 220
                SplitView.maximumWidth: 420
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

                Pcb3dView {
                    anchors.fill: parent
                    visible: appController && appController.activeTab === "pcb3d"
                }

                SpiceView {
                    anchors.fill: parent
                    visible: appController && appController.activeTab === "spice"
                }

                Rectangle {
                    id: analysisLoading
                    anchors.fill: parent
                    visible: analysisController && analysisController.analyzing
                    color: "#ccffffff"
                    z: 100

                    Column {
                        anchors.centerIn: parent
                        spacing: 14

                        BusyIndicator {
                            anchors.horizontalCenter: parent.horizontalCenter
                            running: analysisLoading.visible
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Analyzing circuit"
                            color: theme.text
                            font.pixelSize: 16
                            font.family: theme.sans
                            font.weight: Font.Bold
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 360
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.Wrap
                            text: "Sending components and connections to the server. You can still open another project from the sidebar."
                            color: theme.muted
                            font.pixelSize: 12
                            font.family: theme.sans
                        }
                    }
                }
            }

            Rectangle {
                SplitView.preferredWidth: 420
                SplitView.minimumWidth: 320
                SplitView.maximumWidth: 560
                color: theme.surface

                Rectangle {
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    width: 1
                    color: theme.border
                }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        color: theme.surface

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            spacing: 24

                            Item {
                                width: reviewLabel.implicitWidth
                                height: parent.height

                                Text {
                                    id: reviewLabel
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "REVIEW"
                                    color: (appController && appController.rightPanelTab === "issues")
                                           ? theme.text : theme.muted
                                    font.pixelSize: 10
                                    font.family: theme.sans
                                    font.weight: (appController && appController.rightPanelTab === "issues")
                                                 ? Font.Bold : Font.Medium
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    width: 48
                                    anchors.bottom: parent.bottom
                                    height: 3
                                    color: theme.brand
                                    visible: appController && appController.rightPanelTab === "issues"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appController.selectTab("issues")
                                }
                            }

                            Item {
                                width: aiLabel.implicitWidth
                                height: parent.height

                                Text {
                                    id: aiLabel
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "AI"
                                    color: (appController && appController.rightPanelTab === "chat")
                                           ? theme.text : theme.muted
                                    font.pixelSize: 10
                                    font.family: theme.mono
                                    font.weight: (appController && appController.rightPanelTab === "chat")
                                                 ? Font.DemiBold : Font.Medium
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    width: 24
                                    anchors.bottom: parent.bottom
                                    height: 3
                                    color: theme.brand
                                    visible: appController && appController.rightPanelTab === "chat"
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appController.selectTab("chat")
                                }
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

                    IssuesView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: appController && appController.rightPanelTab === "issues"
                        selectedIndex: root.selectedIssueIndex
                        onIssueActivated: function (index, title, reference, source, description, severity) {
                            root.rememberIssue(index, title, reference, source, description, severity)
                        }
                    }

                    ChatView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        visible: appController && appController.rightPanelTab === "chat"
                        attachedTitle: root.attachedTitle
                        attachedReference: root.attachedReference
                        attachedSource: root.attachedSource
                        attachedDescription: root.attachedDescription
                    }
                }
            }
        }

        LogView {
            Layout.fillWidth: true
            Layout.preferredHeight: 160
            Layout.minimumHeight: 80
            visible: appController && appController.logsOpen
        }

        AgentStatus {
            Layout.fillWidth: true
            Layout.preferredHeight: 28
        }
    }
}
