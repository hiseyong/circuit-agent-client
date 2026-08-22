import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

Rectangle {
    id: root
    color: "#1e222a"

    property real zoom: 1.0
    property real nativeW: 1
    property real nativeH: 1
    property bool nativeReady: false
    property real pinchStartZoom: 1.0

    readonly property real dpr: Screen.devicePixelRatio || 1
    readonly property real minZoom: 0.1
    readonly property real maxZoom: 16.0
    readonly property real defaultZoomBoost: 2.2
    property int rasterCap: 4096
    readonly property real rasterScale: {
        if (!nativeReady || nativeW <= 0 || nativeH <= 0)
            return 0
        const longEdge = Math.max(nativeW, nativeH)
        return Math.min(rasterCap / longEdge, Math.max(2, dpr * 2))
    }
    readonly property int renderW: rasterScale > 0 ? Math.max(1, Math.round(nativeW * rasterScale)) : 0
    readonly property int renderH: rasterScale > 0 ? Math.max(1, Math.round(nativeH * rasterScale)) : 0

    function fitZoom() {
        if (!nativeReady || nativeW <= 0 || nativeH <= 0 || flick.width <= 0 || flick.height <= 0)
            return 1
        return Math.min(flick.width / nativeW, flick.height / nativeH)
    }

    function setZoom(nextZoom, originX, originY) {
        const clamped = Math.max(minZoom, Math.min(maxZoom, nextZoom))
        if (Math.abs(clamped - zoom) < 0.0001)
            return
        const ox = originX === undefined ? flick.width / 2 : originX
        const oy = originY === undefined ? flick.height / 2 : originY
        const scale = clamped / zoom
        const cx = flick.contentX + ox
        const cy = flick.contentY + oy
        zoom = clamped
        flick.contentX = Math.max(0, cx * scale - ox)
        flick.contentY = Math.max(0, cy * scale - oy)
    }

    function centerContent() {
        flick.contentX = Math.max(0, (flick.contentWidth - flick.width) / 2)
        flick.contentY = Math.max(0, (flick.contentHeight - flick.height) / 2)
    }

    function fitToView() {
        zoom = fitZoom()
        flick.contentX = 0
        flick.contentY = 0
    }

    function applyDefaultZoom() {
        zoom = Math.min(maxZoom, Math.max(1, fitZoom() * defaultZoomBoost))
        Qt.callLater(root.centerContent)
    }

    function resetNative() {
        nativeReady = false
        nativeW = 1
        nativeH = 1
        zoom = 1
        rasterCap = 4096
    }

    Connections {
        target: kicadController
        function onSchematicChanged() {
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
                    text: "SCHEMATIC"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.letterSpacing: 0.8
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: Math.round(root.zoom * 100) + "%"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.family: "monospace"
                }

                Repeater {
                    model: [
                        { "label": "−", "action": "out" },
                        { "label": "Fit", "action": "fit" },
                        { "label": "+", "action": "in" }
                    ]

                    Button {
                        required property var modelData
                        text: modelData.label
                        onClicked: {
                            if (modelData.action === "in")
                                root.setZoom(root.zoom * 1.25)
                            else if (modelData.action === "out")
                                root.setZoom(root.zoom / 1.25)
                            else
                                root.fitToView()
                        }
                        background: Rectangle {
                            color: parent.down ? "#2c3340" : (parent.hovered ? "#2a303b" : "#252a33")
                            border.color: "#333845"
                            radius: 4
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#e8eaed"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        implicitHeight: 22
                        implicitWidth: modelData.action === "fit" ? 36 : 24
                    }
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
            color: "#efe7d6"

            Flickable {
                id: flick
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                contentWidth: preview.width
                contentHeight: preview.height
                boundsBehavior: Flickable.StopAtBounds
                interactive: true
                visible: kicadController && kicadController.schematicUrl.length > 0

                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                Image {
                    id: preview
                    source: kicadController ? kicadController.schematicUrl : ""
                    asynchronous: true
                    cache: false
                    smooth: true
                    mipmap: true
                    fillMode: Image.Stretch
                    width: root.nativeReady ? root.nativeW * root.zoom : implicitWidth
                    height: root.nativeReady ? root.nativeH * root.zoom : implicitHeight
                    sourceSize.width: root.renderW
                    sourceSize.height: root.renderH

                    onStatusChanged: {
                        if (status === Image.Error && root.rasterCap > 2048) {
                            root.rasterCap = 2048
                            return
                        }
                        if (status === Image.Ready && !root.nativeReady && implicitWidth > 1 && implicitHeight > 1) {
                            root.nativeW = implicitWidth
                            root.nativeH = implicitHeight
                            root.nativeReady = true
                            Qt.callLater(root.applyDefaultZoom)
                        }
                    }

                    onSourceChanged: root.resetNative()
                }

                WheelHandler {
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    onWheel: function (event) {
                        const factor = event.angleDelta.y > 0 ? 1.15 : 1 / 1.15
                        root.setZoom(root.zoom * factor, event.position.x, event.position.y)
                        event.accepted = true
                    }
                }

                PinchHandler {
                    target: null
                    onActiveChanged: {
                        if (active)
                            root.pinchStartZoom = root.zoom
                    }
                    onScaleChanged: {
                        if (active)
                            root.setZoom(root.pinchStartZoom * scale, centroid.position.x, centroid.position.y)
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: !kicadController || kicadController.schematicUrl.length === 0
                text: "Open a KiCad project to preview the schematic."
                color: "#6d5c45"
                font.pixelSize: 13
            }
        }
    }
}
