import QtQuick
import QtQuick.Layouts

// One line of the metrics table: Arabic label, solid hairline leader, mono value in ink.
// A small status dot appears only when the metric is off-track (amber/red).
// Value is NOT coloured — colour is rationed to the dot alone.
RowLayout {
    id: row
    property string label: ""
    property string value: "—"
    property string status: ""
    readonly property bool offTrack: {
        if (status === "") return false
        var c = Theme.statusColor(status)
        return c === Theme.colors.amber || c === Theme.colors.red
    }
    Layout.fillWidth: true
    spacing: 10

    Text {
        text: row.label
        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
        color: Theme.colors.ink2
    }
    // solid hairline leader
    Item {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
        implicitHeight: 1
        Rectangle {
            width: parent.width; height: 1
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.colors.border
        }
    }
    // status dot (only when off-track)
    Rectangle {
        visible: row.offTrack
        width: 7; height: 7; radius: 4
        color: Theme.statusColor(row.status)
        Layout.alignment: Qt.AlignVCenter
    }
    Text {
        text: row.value
        font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.section
        color: Theme.colors.ink
        Layout.alignment: Qt.AlignVCenter
    }
}
