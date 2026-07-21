import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Labelled text input, light. Set `ltr: true` for inherently-LTR values
// (URLs, emails, phone numbers, ports).
ColumnLayout {
    id: field
    property string label: ""
    property alias text: input.text
    property string placeholder: ""
    property bool ltr: false
    property bool password: false
    property bool intOnly: false
    Layout.fillWidth: true
    spacing: 5

    Text {
        text: field.label
        visible: field.label !== ""
        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
        color: Theme.colors.ink2
    }
    TextField {
        id: input
        Layout.fillWidth: true
        placeholderText: field.placeholder
        placeholderTextColor: Theme.colors.ink3
        echoMode: field.password ? TextInput.Password : TextInput.Normal
        validator: field.intOnly ? intValidator : null
        color: Theme.colors.ink
        font.family: field.ltr ? Theme.fonts.mono : Theme.fonts.body
        font.pixelSize: Theme.fs.body
        horizontalAlignment: field.ltr ? Text.AlignLeft : Text.AlignRight
        LayoutMirroring.enabled: !field.ltr
        selectByMouse: true
        leftPadding: 12; rightPadding: 12; topPadding: 9; bottomPadding: 9
        background: Rectangle {
            radius: 8
            color: Theme.colors.bg
            border.width: input.activeFocus ? 2 : 1
            border.color: input.activeFocus ? Theme.colors.accent : Theme.colors.borderHi
            Behavior on border.color { ColorAnimation { duration: 120 } }
        }
    }
    IntValidator { id: intValidator; bottom: 1 }
}
