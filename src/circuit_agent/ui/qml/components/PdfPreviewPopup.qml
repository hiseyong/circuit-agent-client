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
        color: "#1e222a"
        border.color: "#333845"
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
            color: "#16181d"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 10
                spacing: 8

                Text {
                    text: evidencePreview ? evidencePreview.title : "Datasheet"
                    color: "#e8eaed"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }

                Text {
                    visible: evidencePreview && evidencePreview.pageLabel.length > 0
                    text: evidencePreview ? evidencePreview.pageLabel : ""
                    color: evidencePreview && evidencePreview.highlighted ? "#e6b84d" : "#9aa0a6"
                    font.pixelSize: 11
                }

                Button {
                    text: "−"
                    onClicked: root.setZoom(root.zoom / 1.25)
                    background: Rectangle {
                        color: parent.down ? "#2c3340" : "#252a33"
                        border.color: "#333845"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#e8eaed"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitWidth: 28
                    implicitHeight: 24
                }

                Text {
                    text: Math.round(root.zoom * 100) + "%"
                    color: "#9aa0a6"
                    font.pixelSize: 11
                    font.family: "monospace"
                }

                Button {
                    text: "+"
                    onClicked: root.setZoom(root.zoom * 1.25)
                    background: Rectangle {
                        color: parent.down ? "#2c3340" : "#252a33"
                        border.color: "#333845"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#e8eaed"
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
                        color: parent.down ? "#2c3340" : "#252a33"
                        border.color: "#333845"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#e8eaed"
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
                color: "#9aa0a6"
                font.pixelSize: 13
            }

            Text {
                anchors.centerIn: parent
                width: parent.width - 32
                visible: evidencePreview && !evidencePreview.loading && evidencePreview.error.length > 0
                text: evidencePreview ? evidencePreview.error : ""
                color: "#e05d5d"
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
                        model: evidencePreview ? evidencePreview.highlights : []

                        Rectangle {
                            required property var modelData
                            x: modelData.x * pageBox.width
                            y: modelData.y * pageBox.height
                            width: modelData.w * pageBox.width
                            height: modelData.h * pageBox.height
                            color: "#66e6b84d"
                            border.color: "#e6b84d"
                            border.width: 1
                            radius: 2
                        }
                    }
                }
            }
        }
    }
}
