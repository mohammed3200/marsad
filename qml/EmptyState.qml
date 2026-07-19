import QtQuick
import QtQuick.Layouts

Item {
    id: es
    property string icon: "◔"
    property string message: ""
    property string hint: ""

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 420)
        spacing: 8
        Text {
            text: es.icon
            Layout.alignment: Qt.AlignHCenter
            font.pixelSize: 40; color: Theme.colors.ink3
        }
        Text {
            text: es.message
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            font.family: Theme.fonts.body; font.pixelSize: 15
            color: Theme.colors.ink2
        }
        Text {
            text: es.hint; visible: es.hint !== ""
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            font.family: Theme.fonts.body; font.pixelSize: 12
            color: Theme.colors.ink3
        }
    }
}
