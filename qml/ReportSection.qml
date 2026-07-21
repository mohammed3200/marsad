import QtQuick
import QtQuick.Layouts

// A section heading in the brief: short accent tick + Arabic title + hairline.
// Flat, no card. Structure by rule, not fill.
ColumnLayout {
    property string title: ""
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
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.colors.border }
}
