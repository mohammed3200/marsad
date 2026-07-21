import QtQuick
import QtQuick.Layouts

// A flat list row separated by a hairline — the card-less list unit used across
// pages. Put content in the default slot; a bottom rule draws unless `last`.
Item {
    id: row
    property bool last: false
    property bool hoverable: true
    default property alias content: holder.data
    Layout.fillWidth: true
    // size from the slotted child's implicit height — childrenRect includes
    // y-offsets and feedback-loops with wrapped text, producing overlapping rows
    implicitHeight: Math.max(52, (holder.children[0] ? holder.children[0].implicitHeight : 32) + 20)

    Rectangle {
        anchors.fill: parent
        color: (row.hoverable && hh.hovered) ? Theme.colors.fill : "transparent"
    }
    Item {
        id: holder
        anchors {
            fill: parent
            leftMargin: 4; rightMargin: 4
            topMargin: 10; bottomMargin: 10
        }
    }
    Rectangle {
        visible: !row.last
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 1; color: Theme.colors.border
    }
    HoverHandler { id: hh; enabled: row.hoverable }
}
