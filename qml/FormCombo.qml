import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Labelled dropdown, light. `model` is a list of strings; `value` is the current text.
ColumnLayout {
    id: field
    property string label: ""
    property var options: []
    property alias currentIndex: box.currentIndex
    readonly property string value: box.currentText
    Layout.fillWidth: true
    spacing: 5

    Text {
        text: field.label
        visible: field.label !== ""
        font.family: Theme.fonts.body; font.pixelSize: 13
        color: Theme.colors.ink2
    }
    ComboBox {
        id: box
        Layout.fillWidth: true
        model: field.options
        implicitHeight: 40

        contentItem: Text {
            text: box.displayText
            font.family: Theme.fonts.body; font.pixelSize: 14
            color: Theme.colors.ink
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignRight
            leftPadding: 12; rightPadding: 12
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: Theme.colors.bg
            border.width: box.activeFocus ? 2 : 1
            border.color: box.activeFocus ? Theme.colors.accent : Theme.colors.borderHi
        }
        indicator: Text {
            x: 12; y: (box.height - height) / 2
            text: "▾"; font.pixelSize: 12; color: Theme.colors.ink3
        }
        popup: Popup {
            y: box.height + 4
            width: box.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 260)
            padding: 4
            background: Rectangle {
                radius: 8; color: Theme.colors.bg
                border.width: 1; border.color: Theme.colors.borderHi
            }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: box.popup.visible ? box.delegateModel : null
                ScrollIndicator.vertical: ScrollIndicator {}
            }
        }
        delegate: ItemDelegate {
            width: box.width - 8
            implicitHeight: 36
            contentItem: Text {
                text: modelData
                font.family: Theme.fonts.body; font.pixelSize: 14
                color: Theme.colors.ink
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
                rightPadding: 8
            }
            background: Rectangle {
                radius: 6
                color: highlighted ? Theme.colors.fill : "transparent"
            }
            highlighted: box.highlightedIndex === index
        }
    }
}
