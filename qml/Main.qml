import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

Item {
    id: root
    width: 1280; height: 800

    // bound to the Python controller (context property `app`)
    property var dashModel: app.dashModel
    property string reportDate: app.reportDate
    property string engineStatus: app.engineStatus
    property bool engineOnline: app.engineOnline
    property int currentIndex: 2

    // page label + a drawn shape marker (fonts carry no symbol glyphs), RTL order
    readonly property var navItems: [
        { label: "إدخال البيانات",   shape: "bars"    },
        { label: "التحليل والوكلاء", shape: "diamond" },
        { label: "لوحة التحكم",      shape: "grid"    },
        { label: "التقارير",         shape: "square"  },
        { label: "الإعدادات",        shape: "dial"    },
        { label: "جهات الاتصال",     shape: "trigram" }
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
        function onAnalysisDone() { root.currentIndex = 2 }   // لوحة التحكم
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
            // hairline on the inner (content-facing) edge — anchors are mirrored by
            // LayoutMirroring, so `right` here is the visual left of the sidebar
            Rectangle {
                anchors { top: parent.top; bottom: parent.bottom; right: parent.right }
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
                            // leading-edge marker (visually right in RTL — anchors are mirrored)
                            Rectangle {
                                anchors { verticalCenter: parent.verticalCenter; left: parent.left; leftMargin: 6 }
                                width: 3; height: active ? 22 : 0; radius: 2
                                color: Theme.colors.accent
                                Behavior on height { NumberAnimation { duration: 140; easing.type: Easing.OutQuart } }
                            }
                            RowLayout {
                                anchors {
                                    right: parent.right; rightMargin: 14; left: parent.left; leftMargin: 20
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
                                Glyph {
                                    shape: modelData.shape
                                    color: active ? Theme.colors.accent : Theme.colors.ink3
                                    width: 15; height: 15
                                    Layout.alignment: Qt.AlignVCenter
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
                            color: root.engineOnline ? Theme.colors.green : Theme.colors.red
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: root.backendLabel + " — " + root.engineStatus
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
                        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                        color: Theme.colors.ink3
                        LayoutMirroring.enabled: false
                    }
                }
            }
        }

        // ═══════════ content ═══════════
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true

            StackLayout {
                anchors.fill: parent
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

            // ── transient toast (controller `notify` messages) ──
            Connections {
                target: app
                function onNotify(msg) {
                    toastText.text = msg
                    toast.visible = true
                    toastTimer.restart()
                }
            }
            Timer {
                id: toastTimer
                interval: 3500
                onTriggered: toast.visible = false
            }
            Rectangle {
                id: toast
                visible: false
                anchors { bottom: parent.bottom; bottomMargin: 78; horizontalCenter: parent.horizontalCenter }
                width: Math.min(toastText.implicitWidth + 32, parent.width - 48)
                height: toastText.implicitHeight + 18
                radius: 10
                color: Theme.colors.ink
                Text {
                    id: toastText
                    anchors.centerIn: parent
                    width: Math.min(implicitWidth, toast.width - 32)
                    elide: Text.ElideLeft
                    font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                    color: Theme.colors.bg
                }
            }

        }
    }

    // ── modal layer — last child of root so it covers the sidebar too ──
    // ── نافذة ربط واتساب برمز QR ──
    Rectangle {
        id: waScrim
        visible: app.waDialogOpen
        anchors.fill: parent
        color: Theme.colors.ink
        opacity: 0.30
        z: 100
        TapHandler { onTapped: app.waDialogOpen = false }
    }
    Rectangle {
        id: waDialog
        visible: app.waDialogOpen
        anchors.centerIn: parent
        z: 101
        width: 360
        implicitHeight: waCol.implicitHeight + 40
        radius: 12
        color: Theme.colors.bg
        border.width: 1; border.color: Theme.colors.borderHi

        ColumnLayout {
            id: waCol
            anchors { left: parent.left; right: parent.right; top: parent.top
                      leftMargin: 24; rightMargin: 24; topMargin: 20 }
            spacing: 12

            Text {
                text: "ربط واتساب"
                Layout.alignment: Qt.AlignHCenter
                font.family: Theme.fonts.display; font.pixelSize: Theme.fs.section; font.bold: true
                color: Theme.colors.ink
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.colors.border }

            // success state
            RowLayout {
                visible: app.waLinked
                Layout.alignment: Qt.AlignHCenter
                spacing: 9
                Rectangle {
                    width: 9; height: 9; radius: 5
                    color: Theme.colors.green
                    Layout.alignment: Qt.AlignVCenter
                }
                Text {
                    text: "تم الربط بنجاح"
                    font.family: Theme.fonts.display; font.pixelSize: Theme.fs.title; font.bold: true
                    color: Theme.colors.green
                }
            }
            Text {
                visible: app.waLinked && app.waPhone !== ""
                text: app.waPhone
                Layout.alignment: Qt.AlignHCenter
                font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small
                color: Theme.colors.ink3
                LayoutMirroring.enabled: false
            }

            // waiting state
            Text {
                visible: !app.waLinked && app.waQrMatrix.length === 0
                text: app.waStarting ? "جارٍ تجهيز الجسر وتوليد الرمز…\n(أول مرة قد تستغرق دقائق)"
                                     : "بانتظار رمز الربط من الجسر…"
                Layout.alignment: Qt.AlignHCenter
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                color: Theme.colors.ink3
            }

            // the QR itself — drawn from the matrix, no image files
            Item {
                visible: !app.waLinked && app.waQrMatrix.length > 0
                Layout.fillWidth: true
                implicitHeight: qrBox.height
                Rectangle {
                    id: qrBox
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: waGrid.width + 32; height: waGrid.height + 32
                    color: "white"
                    border.width: 1; border.color: Theme.colors.border
                    radius: 8
                    Column {
                        id: waGrid
                        anchors.centerIn: parent
                        spacing: 0
                        Repeater {
                            model: app.waQrMatrix
                            delegate: Row {
                                spacing: 0
                                property string rowData: modelData
                                Repeater {
                                    model: rowData.length
                                    delegate: Rectangle {
                                        width: 6; height: 6
                                        color: rowData.charAt(index) === "1" ? Theme.colors.ink : "white"
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                visible: !app.waLinked
                // بلا أسهم: الخطوط المرفقة لا تحوي U+2190، فتظهر مربعاً فارغاً
                text: "من واتساب: الأجهزة المرتبطة، ثم ربط جهاز، ثم امسح الرمز"
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                color: Theme.colors.ink3
            }

            AppButton {
                text: "إغلاق"; kind: "ghost"
                Layout.alignment: Qt.AlignHCenter
                onClicked: app.waDialogOpen = false
            }
        }
    }
}
