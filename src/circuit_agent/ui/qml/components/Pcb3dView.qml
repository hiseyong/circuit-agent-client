import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    color: "#fbfcfe"

    Theme { id: theme }

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
            Layout.preferredHeight: 48
            color: theme.surface

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 20
                spacing: 8

                Text {
                    text: "PCB 3D"
                    color: theme.muted
                    font.pixelSize: 12
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                }

                Text {
                    text: "kicad-cli still image"
                    color: theme.muted
                    font.pixelSize: 10
                    font.family: theme.mono
                }

                Item { Layout.fillWidth: true }

                Repeater {
                    model: [
                        { "id": "iso", "label": "Iso" },
                        { "id": "top", "label": "Top" },
                        { "id": "bottom", "label": "Bottom" },
                        { "id": "front", "label": "Front" }
                    ]

                    OutlineButton {
                        required property var modelData
                        text: modelData.label
                        enabled: kicadController && !kicadController.pcbBusy
                        implicitHeight: 28
                        implicitWidth: modelData.id === "bottom" ? 60 : 52
                        labelColor: kicadController && kicadController.pcbView === modelData.id
                                    ? theme.brand : theme.text
                        fill: kicadController && kicadController.pcbView === modelData.id
                              ? "#eef2fb" : "#ffffff"
                        stroke: kicadController && kicadController.pcbView === modelData.id
                                ? theme.brand : theme.border
                        onClicked: kicadController.setPcbView(modelData.id)
                    }
                }

                OutlineButton {
                    text: kicadController && kicadController.pcbBusy ? "Rendering…" : "Render"
                    enabled: kicadController && !kicadController.pcbBusy
                    implicitHeight: 28
                    implicitWidth: 66
                    labelColor: theme.text
                    onClicked: kicadController.refreshPcb()
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
            Layout.fillHeight: true
            color: theme.canvas

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
                    color: theme.muted
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
