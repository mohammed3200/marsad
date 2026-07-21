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

    // page label + a short glyph marker, RTL order
    readonly property var navItems: [
        { label: "إدخال البيانات",   glyph: "▤" },
        { label: "التحليل والوكلاء", glyph: "◈" },
        { label: "لوحة التحكم",      glyph: "▦" },
        { label: "التقارير",         glyph: "▣" },
        { label: "الإعدادات",        glyph: "⚙" },
        { label: "جهات الاتصال",     glyph: "☷" }
    ]
    readonly property string backendLabel: {
        var b = app.settings.ai_backend
        return b === "claude" ? "Claude" : b === "openai" ? "OpenAI"
             : b === "gemini" ? "Gemini" : b === "azure"  ? "Azure" : "Ollama"
    }

    // pages can request navigation (empty-state quick actions)
    Connections {
        target: app
        function onNavRequested(i) { root.currentIndex = i }
    }

    LayoutMirroring.enabled: true
    LayoutMirroring.childrenInherit: true

    Rectangle { anchors.fill: parent; color: Theme.colors.bg }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ═══════════ sidebar (leading edge → right in RTL) ═══════════
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 256
            color: Theme.colors.panel
            // hairline on the inner (content-facing) edge
            Rectangle {
                anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                width: 1; color: Theme.colors.border
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // ── brand: mark + wordmark ──
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 26; Layout.leftMargin: 22; Layout.rightMargin: 22
                    spacing: 12
                    ColumnLayout {
                        spacing: 1
                        Layout.fillWidth: true
                        Text {
                            text: "مرصد"
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fs.hero; font.bold: true
                            color: Theme.colors.ink
                        }
                        Text {
                            text: "ذكاء المشاريع — LTT 4G/5G"
                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                            color: Theme.colors.ink3
                        }
                    }
                    Image {
                        source: "../assets/marsad.png"
                        sourceSize.width: 40; sourceSize.height: 40
                        Layout.preferredWidth: 40; Layout.preferredHeight: 40
                        fillMode: Image.PreserveAspectFit
                        smooth: true; asynchronous: true
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.topMargin: 20; Layout.leftMargin: 22; Layout.rightMargin: 22; height: 1; color: Theme.colors.border }

                // ── nav ──
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 14; Layout.leftMargin: 12; Layout.rightMargin: 12
                    spacing: 3
                    Repeater {
                        model: root.navItems
                        delegate: Item {
                            Layout.fillWidth: true
                            implicitHeight: 46
                            readonly property bool active: root.currentIndex === index

                            // rounded pill
                            Rectangle {
                                anchors.fill: parent
                                radius: 10
                                color: active ? Theme.colors.accentSoft : (hover.hovered ? Theme.colors.fill : "transparent")
                            }
                            // leading-edge marker (right in RTL)
                            Rectangle {
                                anchors { verticalCenter: parent.verticalCenter; right: parent.right; rightMargin: 6 }
                                width: 3; height: active ? 22 : 0; radius: 2
                                color: Theme.colors.accent
                                Behavior on height { NumberAnimation { duration: 140; easing.type: Easing.OutQuart } }
                            }
                            RowLayout {
                                anchors {
                                    right: parent.right; rightMargin: 20; left: parent.left; leftMargin: 14
                                    verticalCenter: parent.verticalCenter
                                }
                                spacing: 10
                                Text {
                                    text: modelData.label
                                    font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
                                    font.bold: active
                                    color: active ? Theme.colors.accent : Theme.colors.ink2
                                    Layout.fillWidth: true
                                    horizontalAlignment: Text.AlignRight
                                }
                                Text {
                                    text: modelData.glyph
                                    font.pixelSize: 15
                                    color: active ? Theme.colors.accent : Theme.colors.ink3
                                }
                            }
                            HoverHandler { id: hover }
                            TapHandler { onTapped: root.currentIndex = index }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                // ── footer: engine status + dual (Hijri · Gregorian) date ──
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.margins: 22
                    spacing: 7
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
                            text: root.backendLabel + " — " + root.ollamaStatus
                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                            color: Theme.colors.ink2
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Text {
                        text: app.todayLabel
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                        color: Theme.colors.ink3
                    }
                    Text {
                        text: "منظومة LTT-PMO"
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
