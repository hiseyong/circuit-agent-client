import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    color: "#ffffff"

    Theme { id: theme }

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
                    text: "SPICE"
                    color: theme.muted
                    font.pixelSize: 12
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: spiceController && spiceController.hasResult
                    text: spiceController && spiceController.ok ? "OK" : "Failed"
                    color: spiceController && spiceController.ok ? theme.success : theme.danger
                    font.pixelSize: 11
                    font.family: theme.mono
                    font.weight: Font.DemiBold
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
            implicitHeight: controls.implicitHeight + 20
            color: theme.subtle

            ColumnLayout {
                id: controls
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 8

                RowLayout {
                    spacing: 8

                    Text {
                        text: "Analysis"
                        color: theme.muted
                        font.pixelSize: 12
                        font.family: theme.sans
                    }

                    ComboBox {
                        id: analysisBox
                        model: ["Operating point", "Transient", "AC", "DC"]
                        implicitWidth: 160
                        implicitHeight: 28
                        onActivated: if (spiceController)
                            spiceController.setAnalysisType(["op", "tran", "ac", "dc"][currentIndex])
                    }

                    Item { Layout.fillWidth: true }

                    OutlineButton {
                        text: spiceController && spiceController.running ? "Running…" : "Run"
                        enabled: spiceController && !spiceController.running
                        implicitWidth: 88
                        implicitHeight: 28
                        labelColor: "#ffffff"
                        fill: theme.success
                        stroke: theme.success
                        onClicked: {
                            if (!spiceController)
                                return
                            spiceController.setInstructions(instructionField.text)
                            spiceController.run()
                        }
                    }
                }

                TextField {
                    id: instructionField
                    Layout.fillWidth: true
                    placeholderText: "Optional ngspice card, e.g. tran 1u 10m"
                    color: theme.text
                    placeholderTextColor: theme.muted
                    background: Rectangle {
                        color: theme.surface
                        border.color: instructionField.activeFocus ? theme.brand : theme.border
                        radius: 4
                    }
                    leftPadding: 10
                    rightPadding: 10
                    implicitHeight: 30
                }

                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: theme.muted
                    font.pixelSize: 11
                    text: "Exports the open schematic with kicad-cli and runs KiCad’s libngspice. Schematics without models or sources will fail."
                }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical

            Rectangle {
                SplitView.preferredHeight: 88
                SplitView.minimumHeight: 56
                color: theme.surface

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        text: spiceController && spiceController.hasResult
                              ? spiceController.summary
                              : "No run yet."
                        color: theme.text
                        wrapMode: Text.Wrap
                        width: parent.width
                        font.pixelSize: 13
                    }

                    Text {
                        visible: spiceController && spiceController.hasResult
                        text: {
                            if (!spiceController)
                                return ""
                            const parts = []
                            if (spiceController.engine)
                                parts.push(spiceController.engine)
                            if (spiceController.command)
                                parts.push(spiceController.command)
                            return parts.join("  ·  ")
                        }
                        color: theme.muted
                    }
                }
            }

            Rectangle {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 80
                color: theme.surface

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Text {
                        Layout.leftMargin: 14
                        Layout.topMargin: 8
                        text: "LOG"
                        color: theme.muted
                        font.pixelSize: 10
                        font.family: theme.mono
                        font.weight: Font.DemiBold
                    }

                    Flickable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: width
                        contentHeight: logText.height + 16
                        boundsBehavior: Flickable.StopAtBounds

                        SelectableText {
                            id: logText
                            x: 14
                            y: 6
                            width: parent.width - 28
                            height: contentHeight
                            text: spiceController ? spiceController.log : ""
                            color: theme.text
                            font.pixelSize: 12
                            font.family: theme.mono
                        }
                    }
                }
            }

            Rectangle {
                SplitView.preferredHeight: 140
                SplitView.minimumHeight: 72
                color: theme.surface

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Text {
                        Layout.leftMargin: 14
                        Layout.topMargin: 8
                        text: "NETLIST"
                        color: theme.muted
                        font.pixelSize: 10
                        font.family: theme.mono
                        font.weight: Font.DemiBold
                    }

                    Flickable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: width
                        contentHeight: netlistText.height + 16
                        boundsBehavior: Flickable.StopAtBounds

                        SelectableText {
                            id: netlistText
                            x: 14
                            y: 6
                            width: parent.width - 28
                            height: contentHeight
                            text: spiceController ? spiceController.netlist : ""
                            color: theme.muted
                            font.pixelSize: 12
                            font.family: theme.mono
                        }
                    }
                }
            }
        }
    }
}
