import QtQuick
import QtQuick.Layouts

// One line of the metrics table: Arabic label, dotted leader, mono value in ink.
// A small status dot appears only when the metric is off-track (not "good").
// Value is NOT coloured — colour is rationed to the dot alone.
RowLayout {
    id: row
    property string label: ""
    property string value: "—"
    property string status: ""
    readonly property bool offTrack: status !== "" && status !== "جيد"
                                      && status !== "آمن" && status !== "مكتمل"
    Layout.fillWidth: true
    spacing: 10

    Text {
        text: row.label
        font.family: Theme.fonts.body; font.pixelSize: 15
        color: Theme.colors.ink2
    }
    // dotted leader
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
        font.family: Theme.fonts.mono; font.pixelSize: 17
        color: Theme.colors.ink
        Layout.alignment: Qt.AlignVCenter
    }
}
