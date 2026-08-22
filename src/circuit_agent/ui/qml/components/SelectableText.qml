import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic

TextEdit {
    id: root

    property bool markdown: false

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
    height: contentHeight

    onLinkActivated: function (link) {
        Qt.openUrlExternally(link)
    }

    HoverHandler {
        enabled: root.hoveredLink.length > 0
        cursorShape: Qt.PointingHandCursor
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
