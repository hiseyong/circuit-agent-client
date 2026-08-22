import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic

Button {
    id: root

    property color labelColor: "#194df1"
    property color fill: "#ffffff"
    property color stroke: "#dae2ed"

    implicitHeight: 30
    font.pixelSize: 10
    font.family: "Noto Sans KR"

    background: Rectangle {
        color: {
            if (!root.enabled)
                return root.fill === "#ffffff" ? "#ffffff" : Qt.tint(root.fill, "#80ffffff")
            if (root.down)
                return root.fill === "#ffffff" ? "#eef2fb" : Qt.darker(root.fill, 1.08)
            if (root.hovered)
                return root.fill === "#ffffff" ? "#f8fafd" : Qt.lighter(root.fill, 1.06)
            return root.fill
        }
        border.color: root.enabled ? root.stroke : "#dae2ed"
        radius: 3
    }

    contentItem: Text {
        text: root.text
        color: root.enabled ? root.labelColor : "#8a93a6"
        font.pixelSize: root.font.pixelSize
        font.family: root.font.family
        font.weight: Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
