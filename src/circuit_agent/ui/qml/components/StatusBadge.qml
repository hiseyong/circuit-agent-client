import QtQuick

Rectangle {
    id: root

    property string label: ""
    property string statusText: ""
    property bool connected: false
    property bool mock: false

    readonly property color accent: mock ? "#e6b84d" : (connected ? "#3ecf8e" : "#e05d5d")
    readonly property color fill: mock ? "#332b1a" : (connected ? "#1a3329" : "#33201f")
    readonly property color stroke: mock ? "#6b5a2f" : (connected ? "#2f6b50" : "#6b2f2f")

    implicitHeight: 24
    implicitWidth: row.implicitWidth + 16
    radius: 12
    color: root.fill
    border.color: root.stroke

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Rectangle {
            width: 7
            height: 7
            radius: 4
            color: root.accent
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.label + " " + root.statusText
            color: root.accent
            font.pixelSize: 12
            font.weight: Font.Medium
        }
    }
}
