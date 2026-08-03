import QtQuick
import QtQuick.Layouts

Item {
    id: es
    property string message: ""
    property string hint: ""
    property alias actions: actionHolder.data   // optional buttons row
    // self-size from content — without this the Item has zero implicit height
    // and the centred column overflows into neighbouring sections
    implicitHeight: col.implicitHeight + 24

    ColumnLayout {
        id: col
        anchors.centerIn: parent
        width: Math.max(0, Math.min(parent.width - 48, 440))
        spacing: 9
        Glyph {
            shape: "square"
            Layout.alignment: Qt.AlignHCenter
            width: 40; height: 40
            color: Theme.colors.ink3
        }
        Text {
            text: es.message
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            font.family: Theme.fonts.display; font.pixelSize: Theme.fs.title
            color: Theme.colors.ink
        }
        Text {
            text: es.hint; visible: es.hint !== ""
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink3
        }
        RowLayout {
            id: actionHolder
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 6
            spacing: 10
        }
    }
}
