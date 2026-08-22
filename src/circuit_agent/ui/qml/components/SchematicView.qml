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
    readonly property real baseW: nativeReady ? nativeW : Math.max(1, preview.implicitWidth)
    readonly property real baseH: nativeReady ? nativeH : Math.max(1, preview.implicitHeight)

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

    function zoomAt(deltaY, originX, originY) {
        const dy = deltaY
        if (dy === 0)
            return
        setZoom(zoom * (dy > 0 ? 1.15 : 1 / 1.15), originX, originY)
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

    function captureNativeSize() {
        if (nativeReady || preview.status !== Image.Ready)
            return
        const w = preview.implicitWidth > 1 ? preview.implicitWidth : preview.paintedWidth
        const h = preview.implicitHeight > 1 ? preview.implicitHeight : preview.paintedHeight
        if (w <= 1 || h <= 1)
            return
        nativeW = w
        nativeH = h
        nativeReady = true
        Qt.callLater(root.applyDefaultZoom)
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

            Item {
                id: viewport
                anchors.fill: parent
                anchors.margins: 8
                visible: kicadController && kicadController.schematicUrl.length > 0
                clip: true

                Flickable {
                    id: flick
                    anchors.fill: parent
                    clip: true
                    contentWidth: previewLayer.width
                    contentHeight: previewLayer.height
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: true
                    // Wheel zoom is handled on the viewport so Windows mouse
                    // wheels are not swallowed by Flickable's scroll handler.
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                    ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                    Item {
                        id: previewLayer
                        width: root.baseW * root.zoom
                        height: root.baseH * root.zoom

                        Image {
                            id: preview
                            source: kicadController ? kicadController.schematicUrl : ""
                            asynchronous: true
                            cache: false
                            smooth: true
                            mipmap: false
                            fillMode: Image.Stretch
                            width: root.baseW
                            height: root.baseH
                            transformOrigin: Item.TopLeft
                            scale: root.zoom
                            sourceSize: root.nativeReady && root.renderW > 0 && root.renderH > 0
                                        ? Qt.size(root.renderW, root.renderH)
                                        : Qt.size(-1, -1)

                            onStatusChanged: {
                                if (status === Image.Error && root.rasterCap > 2048) {
                                    root.rasterCap = 2048
                                    return
                                }
                                if (status === Image.Ready)
                                    Qt.callLater(root.captureNativeSize)
                            }

                            onImplicitWidthChanged: root.captureNativeSize()
                            onImplicitHeightChanged: root.captureNativeSize()
                            onPaintedWidthChanged: root.captureNativeSize()
                            onPaintedHeightChanged: root.captureNativeSize()
                            onSourceChanged: root.resetNative()
                        }

                        Repeater {
                            model: kicadController ? kicadController.highlightBoxes : []

                            Rectangle {
                                required property var modelData
                                readonly property bool fromDetail: projectController
                                         && projectController.detailReference === modelData.reference
                                readonly property bool fromIssue: agentController
                                         && agentController.schematicHighlightRefs.indexOf(modelData.reference) >= 0
                                visible: (fromDetail || fromIssue)
                                         && kicadController
                                         && kicadController.schematicPageWidth > 0
                                readonly property real sx: previewLayer.width / kicadController.schematicPageWidth
                                readonly property real sy: previewLayer.height / kicadController.schematicPageHeight
                                x: (modelData.x - modelData.w / 2) * sx
                                y: (modelData.y - modelData.h / 2) * sy
                                width: modelData.w * sx
                                height: modelData.h * sy
                                color: fromDetail ? "#334a8fc4" : "#33e6b84d"
                                border.color: fromDetail ? "#4a8fc4" : "#e6b84d"
                                border.width: 2
                                radius: 3
                            }
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

                WheelHandler {
                    // macOS/Linux: handle wheel here. Windows mouse wheels are
                    // PointerDevice.Mouse and get eaten by Flickable instead.
                    enabled: Qt.platform.os !== "windows"
                    blocking: true
                    grabPermissions: PointerHandler.CanTakeOverFromAnything
                    onWheel: function (event) {
                        const dy = event.angleDelta.y !== 0 ? event.angleDelta.y : event.pixelDelta.y
                        root.zoomAt(dy, event.position.x, event.position.y)
                        event.accepted = true
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.NoButton
                    enabled: Qt.platform.os === "windows"
                    onWheel: function (wheel) {
                        const dy = wheel.angleDelta.y !== 0 ? wheel.angleDelta.y : wheel.pixelDelta.y
                        root.zoomAt(dy, wheel.x, wheel.y)
                        wheel.accepted = true
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
