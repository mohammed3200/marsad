import QtQuick
import QtQuick.Controls.Basic

Button {
    id: btn
    property string kind: "accent"   // accent | ghost | danger
    property color _base: kind === "accent" ? Theme.colors.teal
                        : kind === "danger" ? Theme.colors.red
                        : Theme.colors.panel
    property color _fg:   kind === "ghost" ? Theme.colors.ink : Theme.colors.bg
    property color _hover: kind === "accent" ? Theme.colors.tealHi
                         : kind === "danger" ? Theme.colors.redHi
                         : Theme.colors.cardHi

    implicitHeight: 38
    font.family: Theme.fonts.body
    font.pixelSize: Theme.fs.body
    font.bold: kind !== "ghost"

    contentItem: Text {
        text: btn.text
        font: btn.font
        color: btn.enabled ? btn._fg : Theme.colors.ink3
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        leftPadding: 16; rightPadding: 16
    }
    background: Rectangle {
        radius: 10
        color: !btn.enabled ? Theme.colors.panel
             : btn.down ? Qt.darker(btn._base, 1.15)
             : btn.hovered ? btn._hover : btn._base
        border.width: btn.kind === "ghost" ? 1 : 0
        border.color: Theme.colors.border
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
