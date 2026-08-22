import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#16181d"

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
                    text: "SPICE"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.letterSpacing: 0.8
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: spiceController && spiceController.hasResult
                    text: spiceController && spiceController.ok ? "OK" : "Failed"
                    color: spiceController && spiceController.ok ? "#3ecf8e" : "#e05d5d"
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
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

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: controls.implicitHeight + 20
            color: "#1e222a"

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
                        color: "#9aa0a6"
                        font.pixelSize: 12
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

                    Button {
                        text: spiceController && spiceController.running ? "Running…" : "Run"
                        enabled: spiceController && !spiceController.running
                        onClicked: {
                            if (!spiceController)
                                return
                            spiceController.setInstructions(instructionField.text)
                            spiceController.run()
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
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        implicitWidth: 88
                        implicitHeight: 28
                    }
                }

                TextField {
                    id: instructionField
                    Layout.fillWidth: true
                    placeholderText: "Optional ngspice card, e.g. tran 1u 10m"
                    color: "#e8eaed"
                    placeholderTextColor: "#6d737c"
                    background: Rectangle {
                        color: "#16181d"
                        border.color: instructionField.activeFocus ? "#5b9fd4" : "#333845"
                        radius: 4
                    }
                    leftPadding: 10
                    rightPadding: 10
                    implicitHeight: 30
                }

                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    color: "#6d737c"
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
                color: "#16181d"

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        text: spiceController && spiceController.hasResult
                              ? spiceController.summary
                              : "No run yet."
                        color: "#e8eaed"
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
                        color: "#9aa0a6"
                        font.pixelSize: 11
                    }
                }
            }

            Rectangle {
                SplitView.fillHeight: true
                SplitView.minimumHeight: 80
                color: "#16181d"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Text {
                        Layout.leftMargin: 14
                        Layout.topMargin: 8
                        text: "LOG"
                        color: "#9aa0a6"
                        font.pixelSize: 10
                        font.letterSpacing: 0.6
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
                            color: "#c5cad3"
                            font.pixelSize: 12
                            font.family: "monospace"
                        }
                    }
                }
            }

            Rectangle {
                SplitView.preferredHeight: 140
                SplitView.minimumHeight: 72
                color: "#16181d"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Text {
                        Layout.leftMargin: 14
                        Layout.topMargin: 8
                        text: "NETLIST"
                        color: "#9aa0a6"
                        font.pixelSize: 10
                        font.letterSpacing: 0.6
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
                            color: "#9aa0a6"
                            font.pixelSize: 12
                            font.family: "monospace"
                        }
                    }
                }
            }
        }
    }
}
