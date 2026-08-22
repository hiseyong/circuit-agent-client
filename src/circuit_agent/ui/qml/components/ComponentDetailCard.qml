import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    width: pointerSize + cardWidth
    implicitHeight: Math.max(card.implicitHeight, 28)
    height: implicitHeight

    readonly property int pointerSize: 12
    readonly property int cardWidth: 300
    readonly property color fill: "#1e222a"
    readonly property color stroke: "#3d5f86"
    readonly property alias hovered: cardHover.hovered

    HoverHandler {
        id: cardHover
    }

    Rectangle {
        id: pointer
        width: root.pointerSize
        height: root.pointerSize
        rotation: 45
        color: root.fill
        border.color: root.stroke
        border.width: 1
        x: 2
        anchors.verticalCenter: parent.verticalCenter
        z: 0
    }

    Rectangle {
        id: card
        x: root.pointerSize - 2
        width: root.cardWidth
        implicitHeight: body.implicitHeight + 28
        height: implicitHeight
        radius: 8
        color: root.fill
        border.color: root.stroke
        border.width: 1
        z: 1

        Column {
            id: body
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 14
            spacing: 6

            RowLayout {
                width: parent.width

                Text {
                    text: "COMPONENT"
                    color: "#9aa0a6"
                    font.pixelSize: 10
                    font.letterSpacing: 0.7
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: projectController && projectController.detailPinned
                    text: "PINNED"
                    color: "#5b9fd4"
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                }

                Button {
                    text: "×"
                    onClicked: {
                        if (projectController)
                            projectController.closeDetail()
                    }
                    background: Rectangle {
                        color: parent.down ? "#3a2428" : (parent.hovered ? "#2c3340" : "transparent")
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: parent.hovered ? "#e8eaed" : "#9aa0a6"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    implicitWidth: 22
                    implicitHeight: 22
                }
            }

            Text {
                text: (projectController ? projectController.detailReference : "")
                      + (projectController && projectController.detailValue.length > 0
                         ? "  " + projectController.detailValue : "")
                color: "#e8eaed"
                font.pixelSize: 16
                font.weight: Font.DemiBold
                font.family: "monospace"
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailDescription.length > 0
                text: projectController ? projectController.detailDescription : ""
                color: "#c5cad3"
                font.pixelSize: 13
                wrapMode: Text.Wrap
                width: parent.width
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#333845"
            }

            Text {
                visible: projectController && projectController.detailLibId.length > 0
                text: "Symbol: " + (projectController ? projectController.detailLibId : "")
                color: "#9aa0a6"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailFootprint.length > 0
                text: "Footprint: " + (projectController ? projectController.detailFootprint : "")
                color: "#9aa0a6"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailPartNumber.length > 0
                text: "MPN: " + (projectController ? projectController.detailPartNumber : "")
                color: "#9aa0a6"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailManufacturer.length > 0
                text: "Manufacturer: " + (projectController ? projectController.detailManufacturer : "")
                color: "#9aa0a6"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailNets.length > 0
                text: "Nets: " + (projectController ? projectController.detailNets : "")
                color: "#c5cad3"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailDatasheet.length > 0
                text: projectController ? projectController.detailDatasheet : ""
                color: "#5b9fd4"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: parent.width
            }
        }
    }
}
