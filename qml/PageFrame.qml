import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// The report-page shell: a centered ≤840px column on white with a title block.
// Page content goes in the default slot (appended below the title).
Item {
    id: page
    property string title: ""
    property string subtitle: ""
    default property alias body: bodyHolder.data

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Item {
            width: page.width
            implicitHeight: col.implicitHeight + 72

            ColumnLayout {
                id: col
                width: Math.min(840, parent.width - 96)
                anchors.horizontalCenter: parent.horizontalCenter
                y: 40
                spacing: 26

                // title block
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text {
                        text: page.title
                        font.family: Theme.fonts.display; font.pixelSize: 24; font.bold: true
                        color: Theme.colors.ink
                    }
                    Text {
                        text: page.subtitle
                        visible: page.subtitle !== ""
                        font.family: Theme.fonts.body; font.pixelSize: 13
                        color: Theme.colors.ink2
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.topMargin: 8
                        height: 2; color: Theme.colors.accent; opacity: 0.9
                    }
                }

                ColumnLayout {
                    id: bodyHolder
                    Layout.fillWidth: true
                    spacing: 22
                }
            }
        }
    }
}
