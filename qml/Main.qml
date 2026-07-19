import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

Item {
    id: root
    width: 1280; height: 800

    // bound to the Python controller (context property `app`)
    property var dashModel: app.dashModel
    property string reportDate: app.reportDate
    property string ollamaStatus: app.ollamaStatus
    property bool ollamaOnline: app.ollamaOnline
    property int currentIndex: 2
    readonly property string health: (dashModel && dashModel.overall_health) ? dashModel.overall_health : ""

    readonly property var navItems: [
        "إدخال البيانات",
        "التحليل والوكلاء",
        "لوحة التحكم",
        "التقارير",
        "الإعدادات",
        "جهات الاتصال"
    ]

    LayoutMirroring.enabled: true
    LayoutMirroring.childrenInherit: true

    Rectangle { anchors.fill: parent; color: Theme.colors.bg }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ═══════════ sidebar (leading edge → right in RTL) ═══════════
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 232
            color: Theme.colors.panel
            // hairline on the inner (content-facing) edge
            Rectangle {
                anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                width: 1; color: Theme.colors.border
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // brand
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.margins: 24
                    spacing: 2
                    Text {
                        text: "مرصد"
                        font.family: Theme.fonts.display; font.pixelSize: 24; font.bold: true
                        color: Theme.colors.ink
                    }
                    Text {
                        text: "ذكاء المشاريع — LTT 4G/5G"
                        font.family: Theme.fonts.body; font.pixelSize: 11
                        color: Theme.colors.ink3
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; height: 1; color: Theme.colors.border }

                // nav
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 12
                    spacing: 2
                    Repeater {
                        model: root.navItems
                        delegate: Item {
                            Layout.fillWidth: true
                            implicitHeight: 44
                            readonly property bool active: root.currentIndex === index

                            Rectangle {
                                anchors.fill: parent
                                color: active ? Theme.colors.accentBg : (hover.hovered ? Theme.colors.fill : "transparent")
                            }
                            // leading-edge marker (right in RTL)
                            Rectangle {
                                anchors { top: parent.top; bottom: parent.bottom; right: parent.right }
                                width: 3
                                color: active ? Theme.colors.accent : "transparent"
                            }
                            Text {
                                anchors {
                                    right: parent.right; rightMargin: 24
                                    verticalCenter: parent.verticalCenter
                                }
                                text: modelData
                                font.family: Theme.fonts.body; font.pixelSize: 14
                                font.bold: active
                                color: active ? Theme.colors.accent : Theme.colors.ink2
                            }
                            HoverHandler { id: hover }
                            TapHandler { onTapped: root.currentIndex = index }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // footer meta — reads as an official reference line
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.margins: 24
                    spacing: 6
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.colors.border }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        spacing: 7
                        Rectangle {
                            width: 7; height: 7; radius: 4
                            color: root.ollamaOnline ? Theme.colors.green : Theme.colors.red
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: "Ollama " + root.ollamaStatus
                            font.family: Theme.fonts.body; font.pixelSize: 11
                            color: Theme.colors.ink2
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Text {
                        text: "LTT-PMO" + (root.reportDate !== "" ? " · " + root.reportDate : "")
                        font.family: Theme.fonts.mono; font.pixelSize: 10
                        color: Theme.colors.ink3
                        LayoutMirroring.enabled: false
                    }
                }
            }
        }

        // ═══════════ content ═══════════
        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: root.currentIndex

            InputPage {}
            AnalysisPage {}
            DashboardPage {
                model: root.dashModel
                reportDate: root.reportDate
            }
            ReportsPage {}
            SettingsPage {}
            ContactsPage {}
        }
    }
}
