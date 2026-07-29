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
    // optional sticky bottom bar (e.g. the Settings save bar) — zero height,
    // no visual change, on pages that don't set it
    property alias footer: footerHolder.data

    ScrollView {
        anchors { top: parent.top; left: parent.left; right: parent.right
                  bottom: footerBar.top }
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
                    spacing: 5
                    Text {
                        text: page.title
                        font.family: Theme.fonts.display; font.pixelSize: Theme.fs.display; font.bold: true
                        color: Theme.colors.ink
                    }
                    Text {
                        text: page.subtitle
                        visible: page.subtitle !== ""
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                        color: Theme.colors.ink2
                    }
                    // short accent rule (leading edge in RTL) — a kashida-like tick
                    Rectangle {
                        Layout.topMargin: 9
                        Layout.preferredWidth: 56; height: 3; radius: 2
                        color: Theme.colors.accent
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

    // sticky footer bar — height 0 unless a page slots `footer` content
    Item {
        id: footerBar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: footerHolder.children.length > 0 ? 60 : 0
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 1; color: Theme.colors.border
            visible: footerBar.height > 0
        }
        Item { id: footerHolder; anchors.fill: parent }
    }
}
