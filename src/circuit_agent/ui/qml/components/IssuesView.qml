import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    color: "#ffffff"

    Theme { id: theme }

    property int selectedIndex: 0
    signal issueActivated(int index, string title, string reference, string source, string description, string severity)

    function severityColor(level) {
        if (level === "error")
            return theme.danger
        if (level === "warning")
            return theme.warning
        return theme.brand
    }

    function severityFill(level) {
        if (level === "error")
            return theme.dangerSoft
        if (level === "warning")
            return theme.warningSoft
        return "#eef2fb"
    }

    function severityLabel(level) {
        if (level === "error")
            return "VIOLATION"
        if (level === "warning")
            return "WARNING"
        return "INFO"
    }

    function whyLabel(level) {
        if (level === "error")
            return "WHY THIS IS DANGEROUS"
        if (level === "warning")
            return "WHY THIS MATTERS"
        return "DETAILS"
    }

    function issueCode(title) {
        const compact = title.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_|_$/g, "")
        return compact.length > 0 ? compact.toUpperCase() : "ISSUE"
    }

    function evidenceLine(entries) {
        if (!entries || entries.length === 0)
            return ""
        const first = entries[0]
        const parts = []
        if (first.document)
            parts.push(first.document)
        if (first.location)
            parts.push(first.location)
        return parts.join(" · ")
    }

    function activateIssue(index, title, reference, source, description, severity) {
        root.issueActivated(index, title, reference, source, description, severity)
    }

    function firstOpenable(entries) {
        if (!entries)
            return null
        for (let i = 0; i < entries.length; i++) {
            if (entries[i].canOpen)
                return entries[i]
        }
        return entries.length > 0 ? entries[0] : null
    }

    ListView {
        id: issueList
        anchors.fill: parent
        clip: true
        spacing: 10
        topMargin: 12
        bottomMargin: 12
        model: agentController ? agentController.issueModel : null

        delegate: Item {
            id: issueDelegate
            required property int index
            required property string severity
            required property string title
            required property string description
            required property string reference
            required property string source
            required property var evidence
            required property bool highlighted
            required property var highlightTargets

            readonly property bool expanded: issueList.count > 0
                && index === Math.min(root.selectedIndex, issueList.count - 1)
            readonly property var primaryEvidence: root.firstOpenable(evidence)

            width: issueList.width
            implicitHeight: card.height
            height: implicitHeight

            Component.onCompleted: {
                if (index === 0 && root.selectedIndex === 0)
                    root.activateIssue(index, title, reference, source, description, severity)
            }

            Rectangle {
                id: card
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                height: issueDelegate.expanded ? expandedBody.implicitHeight + 12 : 70
                radius: 8
                color: {
                    if (issueDelegate.expanded)
                        return theme.surface
                    if (collapsedMouse.containsMouse)
                        return "#eef2fb"
                    return theme.canvas
                }
                border.width: 1
                border.color: issueDelegate.expanded
                              ? root.severityColor(issueDelegate.severity)
                              : "#c5d0de"
                clip: true

                Rectangle {
                    width: 4
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    color: root.severityColor(issueDelegate.severity)
                }

                Column {
                    id: expandedBody
                    visible: issueDelegate.expanded
                    width: parent.width
                    topPadding: 16
                    leftPadding: 16
                    rightPadding: 16
                    spacing: 10

                    Item {
                        width: parent.width - 32
                        height: 44

                        Column {
                            anchors.left: parent.left
                            anchors.right: badge.left
                            anchors.rightMargin: 8
                            spacing: 4

                            Text {
                                width: parent.width
                                text: root.issueCode(issueDelegate.title)
                                color: theme.text
                                font.pixelSize: 18
                                font.family: theme.mono
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                width: parent.width
                                text: {
                                    const parts = []
                                    if (issueDelegate.severity === "error")
                                        parts.push("ABSOLUTE MAXIMUM")
                                    else
                                        parts.push(root.severityLabel(issueDelegate.severity))
                                    if (issueDelegate.reference.length > 0)
                                        parts.push(issueDelegate.reference)
                                    return parts.join(" · ")
                                }
                                color: theme.muted
                                font.pixelSize: 10
                                font.family: theme.mono
                                elide: Text.ElideRight
                            }
                        }

                        Text {
                            id: badge
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.topMargin: 4
                            text: root.severityLabel(issueDelegate.severity)
                            color: root.severityColor(issueDelegate.severity)
                            font.pixelSize: 10
                            font.family: theme.mono
                            font.weight: Font.DemiBold
                        }
                    }

                    Rectangle {
                        width: parent.width - 32
                        implicitHeight: headline.implicitHeight + 24
                        color: root.severityFill(issueDelegate.severity)
                        border.color: root.severityColor(issueDelegate.severity)
                        radius: 3

                        Text {
                            id: headline
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: 12
                            text: issueDelegate.title
                            color: root.severityColor(issueDelegate.severity)
                            font.pixelSize: 11
                            font.family: theme.mono
                            font.weight: Font.DemiBold
                            wrapMode: Text.Wrap
                        }
                    }

                    Text {
                        visible: root.evidenceLine(issueDelegate.evidence).length > 0
                                 || issueDelegate.source.length > 0
                        width: parent.width - 32
                        text: root.evidenceLine(issueDelegate.evidence) || issueDelegate.source
                        color: theme.muted
                        font.pixelSize: 10
                        font.family: theme.mono
                        wrapMode: Text.Wrap
                    }

                    Column {
                        width: parent.width - 32
                        spacing: 10

                        RowLayout {
                            width: parent.width
                            spacing: 8

                            OutlineButton {
                                text: "Open datasheet"
                                implicitWidth: 118
                                enabled: issueDelegate.primaryEvidence && issueDelegate.primaryEvidence.canOpen && evidencePreview
                                onClicked: {
                                    const ev = issueDelegate.primaryEvidence
                                    if (!ev || !evidencePreview)
                                        return
                                    evidencePreview.openUrl(ev.url, ev.pageNumber, ev.document, ev.coordinates)
                                }
                            }

                            OutlineButton {
                                text: issueDelegate.highlighted ? "Highlighted" : "Highlight schematic"
                                implicitWidth: issueDelegate.highlighted ? 92 : 140
                                enabled: issueDelegate.highlightTargets.length > 0
                                fill: issueDelegate.highlighted ? "#eef2fb" : "#ffffff"
                                onClicked: {
                                    agentController.toggleIssueHighlightAt(issueDelegate.index)
                                    if (appController)
                                        appController.selectTab("schematic")
                                }
                            }

                            Item { Layout.fillWidth: true }
                        }

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: theme.border
                        }

                        RowLayout {
                            width: parent.width
                            spacing: 8

                            Item { Layout.fillWidth: true }

                            Rectangle {
                                implicitWidth: actionRow.implicitWidth + 12
                                implicitHeight: 40
                                radius: 6
                                color: theme.canvas
                                border.color: theme.border

                                Row {
                                    id: actionRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    OutlineButton {
                                        text: "Dismiss"
                                        implicitWidth: 72
                                        labelColor: theme.muted
                                        onClicked: agentController.dismissIssueAt(issueDelegate.index)
                                    }

                                    OutlineButton {
                                        text: "Solve"
                                        implicitWidth: 64
                                        labelColor: theme.surface
                                        fill: "#194df1"
                                        stroke: "#194df1"
                                        enabled: agentController
                                                 && !agentController.busy
                                                 && !agentController.awaitingDecision
                                                 && analysisController
                                                 && analysisController.projectId.length > 0
                                        onClicked: {
                                            root.activateIssue(
                                                issueDelegate.index,
                                                issueDelegate.title,
                                                issueDelegate.reference,
                                                issueDelegate.source,
                                                issueDelegate.description,
                                                issueDelegate.severity
                                            )
                                            agentController.solveIssueAt(issueDelegate.index)
                                            if (appController)
                                                appController.selectTab("chat")
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        width: parent.width - 32
                        text: root.whyLabel(issueDelegate.severity)
                        color: theme.muted
                        font.pixelSize: 10
                        font.family: theme.sans
                        font.weight: Font.Bold
                    }

                    Text {
                        width: parent.width - 32
                        text: issueDelegate.description
                        color: theme.text
                        font.pixelSize: 11
                        font.family: theme.sans
                        wrapMode: Text.Wrap
                        lineHeight: 17
                        lineHeightMode: Text.FixedHeight
                    }

                    Text {
                        visible: issueDelegate.evidence && issueDelegate.evidence.length > 0
                        width: parent.width - 32
                        topPadding: 8
                        text: "SOURCE EVIDENCE"
                        color: theme.muted
                        font.pixelSize: 10
                        font.family: theme.sans
                        font.weight: Font.Bold
                    }

                    Repeater {
                        model: issueDelegate.evidence

                        Rectangle {
                            id: evidenceCard
                            required property var modelData
                            width: expandedBody.width - 32
                            implicitHeight: evCol.implicitHeight + 20
                            color: evidenceMouse.containsMouse && modelData.canOpen ? "#eef2fb" : theme.subtle
                            border.color: {
                                if (!modelData.canOpen)
                                    return theme.border
                                return evidenceMouse.containsMouse ? theme.brand : "#9eb0c9"
                            }
                            border.width: modelData.canOpen ? 1.5 : 1
                            radius: 4

                            Column {
                                id: evCol
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 12
                                spacing: 6

                                RowLayout {
                                    width: parent.width
                                    spacing: 8

                                    Text {
                                        Layout.fillWidth: true
                                        text: {
                                            const bits = []
                                            if (modelData.document)
                                                bits.push(modelData.document)
                                            if (modelData.source)
                                                bits.push(modelData.source)
                                            return bits.join(" · ")
                                        }
                                        color: theme.muted
                                        font.pixelSize: 8
                                        font.family: theme.mono
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        visible: modelData.page.length > 0
                                        text: modelData.page
                                        color: theme.brand
                                        font.pixelSize: 8
                                        font.family: theme.mono
                                    }
                                }

                                Text {
                                    visible: modelData.section.length > 0
                                    width: parent.width
                                    text: modelData.section
                                    color: theme.text
                                    font.pixelSize: 12
                                    font.family: theme.sans
                                    font.weight: Font.Bold
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.content.length > 0 ? modelData.content : "(empty excerpt)"
                                    color: theme.muted
                                    font.pixelSize: 9
                                    font.family: theme.sans
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    visible: modelData.location.length > 0
                                    text: modelData.location
                                    color: theme.muted
                                    font.pixelSize: 8
                                    font.family: theme.mono
                                }

                                Rectangle {
                                    visible: modelData.canOpen
                                    width: parent.width
                                    implicitHeight: 28
                                    radius: 4
                                    color: evidenceMouse.containsMouse ? "#dce6fb" : "#eef2fb"
                                    border.color: theme.brand

                                    Row {
                                        anchors.centerIn: parent
                                        spacing: 6

                                        Text {
                                            text: "Open datasheet"
                                            color: theme.brand
                                            font.pixelSize: 10
                                            font.family: theme.sans
                                            font.weight: Font.DemiBold
                                        }

                                        Text {
                                            text: "↗"
                                            color: theme.brand
                                            font.pixelSize: 12
                                            font.family: theme.sans
                                            font.weight: Font.DemiBold
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                id: evidenceMouse
                                anchors.fill: parent
                                enabled: modelData.canOpen && evidencePreview
                                hoverEnabled: enabled
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: evidencePreview.openUrl(
                                    modelData.url,
                                    modelData.pageNumber,
                                    modelData.document,
                                    modelData.coordinates
                                )
                            }
                        }
                    }
                }

                Item {
                    visible: !issueDelegate.expanded
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16

                    Text {
                        id: failMark
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.topMargin: 21
                        text: issueDelegate.severity === "info" ? "i" : "×"
                        color: root.severityColor(issueDelegate.severity)
                        font.pixelSize: 15
                        font.family: theme.mono
                        font.weight: Font.DemiBold
                    }

                    Column {
                        anchors.left: failMark.right
                        anchors.leftMargin: 10
                        anchors.right: collapsedRight.left
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2

                        Text {
                            width: parent.width
                            text: root.issueCode(issueDelegate.title)
                            color: theme.text
                            font.pixelSize: 11
                            font.family: theme.mono
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: {
                                const parts = [root.severityLabel(issueDelegate.severity)]
                                if (issueDelegate.reference.length > 0)
                                    parts.push(issueDelegate.reference)
                                return parts.join(" · ")
                            }
                            color: theme.muted
                            font.pixelSize: 9
                            font.family: theme.mono
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        id: collapsedRight
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: 21
                        width: Math.min(120, implicitWidth)
                        text: issueDelegate.title
                        color: root.severityColor(issueDelegate.severity)
                        font.pixelSize: 10
                        font.family: theme.mono
                        font.weight: Font.Medium
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignRight
                    }

                    MouseArea {
                        id: collapsedMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.activateIssue(
                            issueDelegate.index,
                            issueDelegate.title,
                            issueDelegate.reference,
                            issueDelegate.source,
                            issueDelegate.description,
                            issueDelegate.severity
                        )
                    }
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: issueList.count === 0
            text: "No circuit issues"
            color: theme.muted
            font.pixelSize: 12
            font.family: theme.sans
        }
    }
}
