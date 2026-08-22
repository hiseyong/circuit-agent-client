import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window
import ".."

Rectangle {
    id: root
    color: "#ffffff"

    Theme { id: theme }

    property int bubbleAnchorIndex: -1
    property real bubbleAnchorY: 0
    property bool rowHovered: false

    function chosenFile(dialog) {
        if (dialog.selectedFile && dialog.selectedFile.toString().length > 0)
            return dialog.selectedFile.toString()
        if (dialog.selectedFiles && dialog.selectedFiles.length > 0)
            return dialog.selectedFiles[0].toString()
        return ""
    }

    function openProjectDialog() {
        const window = root.Window.window
        if (window)
            window.requestActivate()
        openDialog.close()
        Qt.callLater(function () { openDialog.open() })
    }

    function placeBubble(row) {
        if (!row || !Overlay.overlay)
            return
        const pos = row.mapToItem(Overlay.overlay, row.width, row.height / 2)
        detailPopup.x = pos.x - 4
        bubbleAnchorY = pos.y
        detailPopup.y = Math.max(8, Math.min(pos.y - detailPopup.height / 2, Overlay.overlay.height - detailPopup.height - 8))
        if (!detailPopup.opened)
            detailPopup.open()
    }

    function refreshBubble() {
        if (bubbleAnchorIndex < 0)
            return
        const row = componentList.itemAtIndex(bubbleAnchorIndex)
        if (row)
            placeBubble(row)
    }

    function keepDetailOpen() {
        return (projectController && projectController.detailPinned)
               || root.rowHovered
               || listHover.hovered
               || (detailPopup.opened && detailCard.hovered)
    }

    function enterRow(row) {
        hoverClearTimer.stop()
        root.rowHovered = true
        if (!row || !projectController)
            return
        const alreadyShown = root.bubbleAnchorIndex === row.index
                             && detailPopup.opened
                             && projectController.detailReference === row.reference
        root.bubbleAnchorIndex = row.index
        projectController.hoverComponent(row.reference)
        if (!alreadyShown)
            root.placeBubble(row)
    }

    function scheduleHoverClear() {
        if (root.keepDetailOpen()) {
            hoverClearTimer.stop()
            return
        }
        hoverClearTimer.restart()
    }

    function partLabel(partNumber, value) {
        if (partNumber && partNumber.length > 0)
            return partNumber
        return value || ""
    }

    Timer {
        id: hoverClearTimer
        interval: 280
        onTriggered: {
            if (root.keepDetailOpen())
                return
            if (projectController && projectController.detailReference)
                projectController.clearHover(projectController.detailReference)
        }
    }

    Connections {
        target: kicadController
        function onSelectProjectRequested() {
            root.openProjectDialog()
        }
    }

    FileDialog {
        id: openDialog
        title: "Select KiCad Project"
        fileMode: FileDialog.OpenFile
        nameFilters: ["KiCad projects (*.kicad_pro)", "All files (*)"]
        onAccepted: {
            const path = root.chosenFile(openDialog)
            console.log("Open project selected:", path)
            projectController.openProject(path)
        }
    }

    FileDialog {
        id: newDialog
        title: "New KiCad Project"
        fileMode: FileDialog.SaveFile
        nameFilters: ["KiCad projects (*.kicad_pro)"]
        defaultSuffix: "kicad_pro"
        onAccepted: projectController.newProject(root.chosenFile(newDialog))
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 74
            color: theme.surface

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 20
                anchors.rightMargin: 16
                spacing: 3

                RowLayout {
                    width: parent.width
                    spacing: 8

                    Text {
                        text: "components"
                        color: theme.text
                        font.pixelSize: 15
                        font.family: theme.mono
                        font.weight: Font.DemiBold
                    }

                    Item { Layout.fillWidth: true }

                    OutlineButton {
                        text: "New"
                        implicitWidth: 48
                        implicitHeight: 22
                        onClicked: newDialog.open()
                    }

                    OutlineButton {
                        text: "Open"
                        implicitWidth: 52
                        implicitHeight: 22
                        onClicked: root.openProjectDialog()
                    }
                }

                Text {
                    text: componentList.count + " shown"
                    color: theme.muted
                    font.pixelSize: 11
                    font.family: theme.mono
                }
            }
        }

        ListView {
            id: componentList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            cacheBuffer: 400
            model: projectController ? projectController.componentModel : null
            spacing: 0
            onContentYChanged: root.refreshBubble()

            delegate: Rectangle {
                id: row
                required property string reference
                required property string value
                required property string partNumber
                required property int index

                readonly property bool selected: projectController
                                                 && projectController.detailReference === reference

                width: componentList.width
                height: 58
                color: selected ? theme.canvas : theme.surface

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 16
                    spacing: 12

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: selected ? "●" : "○"
                        color: selected ? theme.brand : theme.muted
                        font.pixelSize: 12
                        font.family: theme.mono
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            text: row.reference
                            color: theme.brand
                            font.pixelSize: 13
                            font.family: theme.mono
                            font.weight: Font.Medium
                        }

                        Text {
                            visible: root.partLabel(row.partNumber, row.value).length > 0
                            text: root.partLabel(row.partNumber, row.value)
                            color: theme.muted
                            font.pixelSize: 11
                            font.family: theme.mono
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: root.enterRow(row)
                    onExited: {
                        root.rowHovered = false
                        root.scheduleHoverClear()
                    }
                    onClicked: {
                        if (!projectController)
                            return
                        root.bubbleAnchorIndex = row.index
                        projectController.togglePinComponent(row.reference)
                        root.placeBubble(row)
                    }
                }
            }

            Text {
                anchors.centerIn: parent
                visible: componentList.count === 0
                text: "No components"
                color: theme.muted
                font.pixelSize: 12
                font.family: theme.sans
            }

            HoverHandler {
                id: listHover
                acceptedDevices: PointerDevice.AllDevices
                onHoveredChanged: {
                    if (!hovered)
                        root.scheduleHoverClear()
                }
            }
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 1
        color: theme.border
    }

    Popup {
        id: detailPopup
        parent: Overlay.overlay
        padding: 0
        modal: false
        focus: false
        clip: false
        closePolicy: Popup.NoAutoClose
        enter: Transition {}
        exit: Transition {}
        background: Item {}

        ComponentDetailCard {
            id: detailCard
        }

        width: detailCard.width
        height: detailCard.height

        onOpened: root.refreshBubble()
        onHeightChanged: root.refreshBubble()
    }

    Connections {
        target: detailCard
        function onHoveredChanged() {
            if (detailCard.hovered)
                hoverClearTimer.stop()
            else
                root.scheduleHoverClear()
        }
    }

    Connections {
        target: projectController
        function onDetailChanged() {
            if (projectController && projectController.detailVisible)
                detailPopup.open()
            else
                detailPopup.close()
        }
    }
}
