import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Item {
    id: root
    width: pointerSize + cardWidth
    implicitHeight: Math.max(card.implicitHeight, 28)
    height: implicitHeight

    Theme { id: theme }

    readonly property int pointerSize: 12
    readonly property int cardWidth: 300
    readonly property color fill: theme.surface
    readonly property color stroke: theme.brand
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
                    color: theme.muted
                    font.pixelSize: 10
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                }

                Item { Layout.fillWidth: true }

                Text {
                    visible: projectController && projectController.detailPinned
                    text: "PINNED"
                    color: theme.brand
                    font.pixelSize: 10
                    font.family: theme.mono
                    font.weight: Font.DemiBold
                }

                Button {
                    text: "×"
                    onClicked: {
                        if (projectController)
                            projectController.closeDetail()
                    }
                    background: Rectangle {
                        color: parent.down ? theme.dangerSoft : (parent.hovered ? theme.canvas : "transparent")
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: parent.hovered ? theme.text : theme.muted
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
                color: theme.text
                font.pixelSize: 16
                font.weight: Font.Bold
                font.family: theme.mono
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailDescription.length > 0
                text: projectController ? projectController.detailDescription : ""
                color: theme.muted
                font.pixelSize: 13
                font.family: theme.sans
                wrapMode: Text.Wrap
                width: parent.width
            }

            Rectangle {
                width: parent.width
                height: 1
                color: theme.border
            }

            Text {
                visible: projectController && projectController.detailLibId.length > 0
                text: "Symbol: " + (projectController ? projectController.detailLibId : "")
                color: theme.muted
                font.pixelSize: 12
                font.family: theme.mono
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailFootprint.length > 0
                text: "Footprint: " + (projectController ? projectController.detailFootprint : "")
                color: theme.muted
                font.pixelSize: 12
                font.family: theme.mono
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailPartNumber.length > 0
                text: "MPN: " + (projectController ? projectController.detailPartNumber : "")
                color: theme.muted
                font.pixelSize: 12
                font.family: theme.mono
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailManufacturer.length > 0
                text: "Manufacturer: " + (projectController ? projectController.detailManufacturer : "")
                color: theme.muted
                font.pixelSize: 12
                font.family: theme.sans
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailNets.length > 0
                text: "Nets: " + (projectController ? projectController.detailNets : "")
                color: theme.text
                font.pixelSize: 12
                font.family: theme.mono
                wrapMode: Text.Wrap
                width: parent.width
            }

            Text {
                visible: projectController && projectController.detailDatasheet.length > 0
                text: projectController ? projectController.detailDatasheet : ""
                color: theme.brand
                font.pixelSize: 12
                font.family: theme.mono
                wrapMode: Text.Wrap
                width: parent.width
            }
        }
    }
}
