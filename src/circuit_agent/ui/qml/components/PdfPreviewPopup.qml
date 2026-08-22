import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Popup {
    id: root
    parent: Overlay.overlay
    modal: true
    focus: true
    visible: evidencePreview && evidencePreview.isOpen
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    anchors.centerIn: parent
    width: Math.min(720, Overlay.overlay.width - 48)
    height: Math.min(820, Overlay.overlay.height - 48)
    padding: 0
    property real zoom: 1.0
    onClosed: if (evidencePreview) evidencePreview.close()

    function clampZoom(value) {
        return Math.min(4, Math.max(0.5, value))
    }

    function setZoom(value) {
        root.zoom = root.clampZoom(value)
    }

    background: Rectangle {
        color: "#ffffff"
        border.color: "#dae2ed"
        radius: 8
    }

    Connections {
        target: evidencePreview
        function onPreviewChanged() {
            if (evidencePreview && evidencePreview.loading)
                root.zoom = 1
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: "#ffffff"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 10
                spacing: 8

                Text {
                    text: evidencePreview ? evidencePreview.title : "Datasheet"
                    color: "#0e1b36"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }

                Text {
                    visible: evidencePreview && evidencePreview.pageLabel.length > 0
                    text: evidencePreview ? evidencePreview.pageLabel : ""
                    color: evidencePreview && evidencePreview.highlighted ? "#194df1" : "#445674"
                    font.pixelSize: 11
                }

                Button {
                    text: "−"
                    onClicked: root.setZoom(root.zoom / 1.25)
                    background: Rectangle {
                        color: parent.down ? "#eef2fb" : "#ffffff"
                        border.color: "#dae2ed"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#0e1b36"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitWidth: 28
                    implicitHeight: 24
                }

                Text {
                    text: Math.round(root.zoom * 100) + "%"
                    color: "#445674"
                    font.pixelSize: 11
                    font.family: "monospace"
                }

                Button {
                    text: "+"
                    onClicked: root.setZoom(root.zoom * 1.25)
                    background: Rectangle {
                        color: parent.down ? "#eef2fb" : "#ffffff"
                        border.color: "#dae2ed"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#0e1b36"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitWidth: 28
                    implicitHeight: 24
                }

                Button {
                    text: "Close"
                    onClicked: root.close()
                    background: Rectangle {
                        color: parent.down ? "#eef2fb" : "#ffffff"
                        border.color: "#dae2ed"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#0e1b36"
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitWidth: 64
                    implicitHeight: 24
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Text {
                anchors.centerIn: parent
                visible: evidencePreview && evidencePreview.loading
                text: "Loading datasheet…"
                color: "#445674"
                font.pixelSize: 13
            }

            Text {
                anchors.centerIn: parent
                width: parent.width - 32
                visible: evidencePreview && !evidencePreview.loading && evidencePreview.error.length > 0
                text: evidencePreview ? evidencePreview.error : ""
                color: "#dc141e"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
            }

            Flickable {
                id: pdfFlick
                anchors.fill: parent
                anchors.margins: 8
                visible: evidencePreview && evidencePreview.imageUrl.length > 0
                clip: true
                contentWidth: Math.max(width, pageBox.width)
                contentHeight: Math.max(height, pageBox.height)
                boundsBehavior: Flickable.StopAtBounds
                interactive: true

                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                WheelHandler {
                    acceptedModifiers: Qt.ControlModifier
                    onWheel: function (event) {
                        const factor = event.angleDelta.y > 0 ? 1.15 : 1 / 1.15
                        root.setZoom(root.zoom * factor)
                        event.accepted = true
                    }
                }

                Item {
                    id: pageBox
                    width: pdfFlick.width * root.zoom
                    height: pdfImage.implicitHeight > 0 && pdfImage.implicitWidth > 0
                            ? pdfImage.implicitHeight * (width / pdfImage.implicitWidth)
                            : pdfFlick.height

                    Image {
                        id: pdfImage
                        anchors.fill: parent
                        source: evidencePreview ? evidencePreview.imageUrl : ""
                        fillMode: Image.PreserveAspectFit
                        cache: false
                    }

                    Repeater {
                        // Do not bind model roles named `x`/`y` onto Rectangle —
                        // API boxes are page-normalized (0–1), so those roles
                        // would place the overlay at ~0.1px. Index lookup only.
                        model: evidencePreview ? evidencePreview.highlights : []

                        Item {
                            required property int index
                            anchors.fill: parent
                            z: 10
                            readonly property var box: evidencePreview.highlights[index]

                            Rectangle {
                                visible: parent.box && parent.box.w > 0 && parent.box.h > 0
                                x: parent.box.x * parent.width
                                y: parent.box.y * parent.height
                                width: parent.box.w * parent.width
                                height: parent.box.h * parent.height
                                color: "#40194df1"
                                border.color: "#194df1"
                                border.width: 2
                                radius: 2
                            }
                        }
                    }
                }
            }
        }
    }
}
