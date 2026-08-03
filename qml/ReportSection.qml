import QtQuick
import QtQuick.Layouts

// A section heading in the brief: short accent tick + Arabic title + hairline.
// Flat, no card. Structure by rule, not fill. Optional `note`: a small live
// status at the trailing end (e.g. «المفتاح مضبوط»), empty by default.
ColumnLayout {
    property string title: ""
    property string note: ""
    property color  noteColor: Theme.colors.ink3
    Layout.fillWidth: true
    spacing: 8

    RowLayout {
        Layout.fillWidth: true
        spacing: 9
        Rectangle { width: 3; height: 15; radius: 1; color: Theme.colors.accent }
        Text {
            text: title
            font.family: Theme.fonts.display; font.pixelSize: Theme.fs.section; font.bold: true
            color: Theme.colors.ink
        }
        Item { Layout.fillWidth: true }
        Text {
            text: note
            visible: note !== ""
            elide: Text.ElideLeft
            maximumLineCount: 1
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
            color: noteColor
            Layout.alignment: Qt.AlignVCenter
        }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.colors.border }
}
