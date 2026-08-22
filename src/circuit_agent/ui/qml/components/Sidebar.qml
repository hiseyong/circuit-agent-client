import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#1e222a"

    property int bubbleAnchorIndex: -1
    property real bubbleAnchorY: 0

    function openProjectDialog() {
        openDialog.open()
    }

    function placeBubble(row) {
        if (!row || !Overlay.overlay)
            return
        const pos = row.mapToItem(Overlay.overlay, row.width, row.height / 2)
        detailPopup.x = pos.x - 4
        bubbleAnchorY = pos.y
        detailPopup.y = Math.max(8, Math.min(pos.y - detailPopup.height / 2, Overlay.overlay.height - detailPopup.height - 8))
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
               || listHover.hovered
               || (detailPopup.opened && detailCard.hovered)
    }

    function hoverAt(x, y) {
        hoverClearTimer.stop()
        if (!projectController)
            return
        const idx = componentList.indexAt(x, y + componentList.contentY)
        if (idx < 0) {
            root.scheduleHoverClear()
            return
        }
        const row = componentList.itemAtIndex(idx)
        if (!row)
            return
        root.bubbleAnchorIndex = idx
        projectController.hoverComponent(row.reference)
        root.placeBubble(row)
    }

    function scheduleHoverClear() {
        if (root.keepDetailOpen()) {
            hoverClearTimer.stop()
            return
        }
        hoverClearTimer.restart()
    }

    Timer {
        id: hoverClearTimer
        interval: 200
        onTriggered: {
            if (root.keepDetailOpen())
                return
            if (listHover.hovered) {
                const x = listHover.point.position.x
                const y = listHover.point.position.y
                if (componentList.indexAt(x, y + componentList.contentY) >= 0) {
                    root.hoverAt(x, y)
                    return
                }
            }
            if (projectController && projectController.detailReference)
                projectController.clearHover(projectController.detailReference)
        }
    }

    Connections {
        target: kicadController
        function onSelectProjectRequested() {
            openDialog.open()
        }
    }

    FileDialog {
        id: openDialog
        title: "Select KiCad Project"
        nameFilters: ["KiCad projects (*.kicad_pro)", "All files (*)"]
        onAccepted: projectController.openProject(selectedFile.toString())
    }

    FileDialog {
        id: newDialog
        title: "New KiCad Project"
        fileMode: FileDialog.SaveFile
        nameFilters: ["KiCad projects (*.kicad_pro)"]
        defaultSuffix: "kicad_pro"
        onAccepted: projectController.newProject(selectedFile.toString())
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Text {
            text: "PROJECT"
            color: "#9aa0a6"
            font.pixelSize: 11
            font.letterSpacing: 0.8
            font.weight: Font.DemiBold
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Button {
                text: "New Project"
                onClicked: newDialog.open()
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
            }

            Button {
                text: "Open Project"
                onClicked: root.openProjectDialog()
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
            }
        }

        Text {
            text: projectController ? projectController.projectName : ""
            color: "#e8eaed"
            font.pixelSize: 14
            font.weight: Font.DemiBold
            elide: Text.ElideMiddle
            Layout.fillWidth: true
        }

        Text {
            text: "└ " + (projectController ? projectController.projectFileName : "")
            color: "#c5cad3"
            font.pixelSize: 13
            font.family: "monospace"
            elide: Text.ElideMiddle
            Layout.fillWidth: true
        }

        Text {
            text: "Status: " + (projectController ? projectController.projectStatus : "")
            color: "#9aa0a6"
            font.pixelSize: 12
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#333845"
        }

        Text {
            text: "COMPONENTS"
            color: "#9aa0a6"
            font.pixelSize: 11
            font.letterSpacing: 0.8
            font.weight: Font.DemiBold
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: componentList
                anchors.fill: parent
                clip: true
                model: projectController ? projectController.componentModel : null
                spacing: 2
                onContentYChanged: root.refreshBubble()

                delegate: Rectangle {
                    id: row
                    required property string reference
                    required property string value
                    required property int index

                    width: componentList.width
                    height: 28
                    radius: 4
                    color: projectController && projectController.detailReference === reference
                           ? "#2a3f5f"
                           : "transparent"

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                        text: (index === componentList.count - 1 ? "└ " : "├ ") + reference
                              + (value.length > 0 ? "  " + value : "")
                        color: "#e8eaed"
                        font.pixelSize: 13
                        font.family: "monospace"
                        elide: Text.ElideRight
                        width: parent.width - 8
                    }

                    MouseArea {
                        anchors.fill: parent
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
                    color: "#9aa0a6"
                    font.pixelSize: 12
                }
            }

            HoverHandler {
                id: listHover
                acceptedDevices: PointerDevice.AllDevices
                onHoveredChanged: {
                    if (hovered)
                        root.hoverAt(point.position.x, point.position.y)
                    else
                        root.scheduleHoverClear()
                }
                onPointChanged: {
                    if (hovered)
                        root.hoverAt(point.position.x, point.position.y)
                }
            }
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 1
        color: "#333845"
    }

    Popup {
        id: detailPopup
        parent: Overlay.overlay
        padding: 0
        modal: false
        focus: false
        clip: false
        closePolicy: Popup.NoAutoClose
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
