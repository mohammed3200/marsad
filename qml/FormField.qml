import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Labelled text input, light. Set `ltr: true` for inherently-LTR values
// (URLs, emails, phone numbers, ports). `password: true` adds an eye toggle.
ColumnLayout {
    id: field
    property string label: ""
    property alias text: input.text
    property string placeholder: ""
    property bool ltr: false
    property bool password: false
    property bool intOnly: false
    property bool _show: false
    Layout.fillWidth: true
    spacing: 5

    Text {
        text: field.label
        visible: field.label !== ""
        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
        color: Theme.colors.ink2
    }
    Item {
        id: inputWrap
        Layout.fillWidth: true
        implicitHeight: input.implicitHeight
        TextField {
            id: input
            anchors.fill: parent
            placeholderText: field.placeholder
            placeholderTextColor: Theme.colors.ink3
            echoMode: field.password && !field._show ? TextInput.Password : TextInput.Normal
            validator: field.intOnly ? intValidator : null
            color: Theme.colors.ink
            font.family: field.ltr ? Theme.fonts.mono : Theme.fonts.body
            font.pixelSize: Theme.fs.body
            horizontalAlignment: field.ltr ? Text.AlignLeft : Text.AlignRight
            LayoutMirroring.enabled: !field.ltr
            selectByMouse: true
            leftPadding: field.password && !field.ltr ? 36 : 12
            rightPadding: field.password && field.ltr ? 36 : 12
            topPadding: 9; bottomPadding: 9
            background: Rectangle {
                radius: 8
                color: Theme.colors.bg
                border.width: input.activeFocus ? 2 : 1
                border.color: input.activeFocus ? Theme.colors.accent : Theme.colors.borderHi
                Behavior on border.color { ColorAnimation { duration: 120 } }
            }
        }
        // show/hide toggle — trailing edge of the secret field (drawn, not a font glyph)
        Glyph {
            shape: field._show ? "eyeoff" : "eye"
            visible: field.password
            width: 14; height: 14
            color: eyeHover.hovered ? Theme.colors.ink2 : Theme.colors.ink3
            x: field.ltr ? parent.width - width - 10 : 10
            anchors.verticalCenter: parent.verticalCenter
            HoverHandler { id: eyeHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: field._show = !field._show }
        }
    }
    IntValidator { id: intValidator; bottom: 1 }
}
