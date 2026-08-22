import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic

TextEdit {
    id: root

    property bool markdown: false
    property var flickable: null

    readOnly: true
    selectByMouse: true
    persistentSelection: true
    wrapMode: TextEdit.Wrap
    textFormat: markdown ? TextEdit.MarkdownText : TextEdit.PlainText
    color: "#e8eaed"
    selectedTextColor: "#ffffff"
    selectionColor: "#3d5a80"
    font.pixelSize: 13
    activeFocusOnPress: true
    implicitHeight: contentHeight

    onLinkActivated: function (link) {
        Qt.openUrlExternally(link)
    }

    HoverHandler {
        enabled: root.hoveredLink.length > 0
        cursorShape: Qt.PointingHandCursor
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        propagateComposedEvents: true
        cursorShape: root.hoveredLink.length > 0 ? Qt.PointingHandCursor : Qt.IBeamCursor
        onPressed: function (mouse) {
            if (root.flickable)
                root.flickable.interactive = false
            root.forceActiveFocus()
            mouse.accepted = false
        }
        onReleased: if (root.flickable)
            root.flickable.interactive = true
        onCanceled: if (root.flickable)
            root.flickable.interactive = true
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: copyMenu.popup()
    }

    Menu {
        id: copyMenu

        MenuItem {
            text: "Copy"
            enabled: root.selectedText.length > 0
            onTriggered: root.copy()
        }
        MenuItem {
            text: "Copy all"
            onTriggered: {
                root.selectAll()
                root.copy()
                root.deselect()
            }
        }
    }
}
