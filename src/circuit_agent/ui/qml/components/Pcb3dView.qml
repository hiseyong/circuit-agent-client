import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#1e222a"

    property real zoom: 1.0
    property real nativeW: 1
    property real nativeH: 1
    property bool nativeReady: false

    function fitZoom() {
        if (!nativeReady || nativeW <= 0 || nativeH <= 0 || flick.width <= 0 || flick.height <= 0)
            return 1
        return Math.min(flick.width / nativeW, flick.height / nativeH)
    }

    function setZoom(nextZoom) {
        zoom = Math.max(0.2, Math.min(8, nextZoom))
    }

    function fitToView() {
        zoom = fitZoom()
        flick.contentX = 0
        flick.contentY = 0
    }

    function resetNative() {
        nativeReady = false
        nativeW = 1
        nativeH = 1
        zoom = 1
    }

    Connections {
        target: kicadController
        function onPcbChanged() {
            root.resetNative()
        }
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
                    text: "PCB 3D"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.letterSpacing: 0.8
                    font.weight: Font.DemiBold
                }

                Text {
                    text: "kicad-cli still image"
                    color: "#6d737c"
                    font.pixelSize: 11
                }

                Item { Layout.fillWidth: true }

                Repeater {
                    model: [
                        { "id": "iso", "label": "Iso" },
                        { "id": "top", "label": "Top" },
                        { "id": "bottom", "label": "Bottom" },
                        { "id": "front", "label": "Front" }
                    ]

                    Button {
                        required property var modelData
                        text: modelData.label
                        enabled: kicadController && !kicadController.pcbBusy
                        onClicked: kicadController.setPcbView(modelData.id)
                        background: Rectangle {
                            color: kicadController && kicadController.pcbView === modelData.id
                                   ? "#2a3f5f"
                                   : (parent.down ? "#2c3340" : "#252a33")
                            border.color: kicadController && kicadController.pcbView === modelData.id
                                          ? "#3d5f86"
                                          : "#333845"
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
                        implicitWidth: 56
                    }
                }

                Button {
                    text: kicadController && kicadController.pcbBusy ? "Rendering…" : "Render"
                    enabled: kicadController && !kicadController.pcbBusy
                    onClicked: kicadController.refreshPcb()
                    background: Rectangle {
                        color: parent.down ? "#2c3340" : "#252a33"
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
                    implicitWidth: 76
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
            Layout.fillHeight: true
            color: "#2a2d33"

            Flickable {
                id: flick
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                contentWidth: preview.width
                contentHeight: preview.height
                boundsBehavior: Flickable.StopAtBounds
                visible: kicadController && kicadController.pcbUrl.length > 0 && !kicadController.pcbBusy

                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                Image {
                    id: preview
                    source: kicadController ? kicadController.pcbUrl : ""
                    asynchronous: true
                    cache: false
                    smooth: true
                    width: root.nativeReady ? root.nativeW * root.zoom : implicitWidth
                    height: root.nativeReady ? root.nativeH * root.zoom : implicitHeight

                    onStatusChanged: {
                        if (status === Image.Ready && implicitWidth > 1 && implicitHeight > 1) {
                            root.nativeW = implicitWidth
                            root.nativeH = implicitHeight
                            root.nativeReady = true
                            Qt.callLater(root.fitToView)
                        }
                    }

                    onSourceChanged: root.resetNative()
                }

                WheelHandler {
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    onWheel: function (event) {
                        root.setZoom(root.zoom * (event.angleDelta.y > 0 ? 1.15 : 1 / 1.15))
                        event.accepted = true
                    }
                }
            }

            Column {
                anchors.centerIn: parent
                spacing: 10
                width: Math.min(420, parent.width - 40)
                visible: !kicadController || kicadController.pcbUrl.length === 0 || kicadController.pcbBusy

                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    running: kicadController && kicadController.pcbBusy
                    visible: running
                }

                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                    color: "#9aa0a6"
                    font.pixelSize: 13
                    text: {
                        if (kicadController && kicadController.pcbBusy)
                            return "Rendering the board in KiCad’s 3D camera…"
                        if (kicadController && kicadController.pcbError.length > 0)
                            return kicadController.pcbError
                        return "Open a project that has a .kicad_pcb file, then press Render."
                    }
                }
            }
        }
    }
}
