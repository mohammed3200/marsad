import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// The status brief. A centered reading column on white paper — no cards,
// structure by hairline rules and space. Colour rationed to small status dots.
Item {
    id: page
    // the `chief` results dict (overall_health, executive_summary, kpis[], top_actions[])
    property var model: ({})
    property string reportDate: ""
    readonly property bool hasData: model && model.overall_health !== undefined
    readonly property string health: (model && model.overall_health) ? model.overall_health : "—"

    // ── first-run quick-start (no data yet) ──
    Item {
        anchors.fill: parent
        visible: !page.hasData

        ColumnLayout {
            anchors.centerIn: parent
            width: Math.max(0, Math.min(parent.width - 64, 560))
            spacing: 20

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: "مرحباً بك في مرصد"
                    Layout.alignment: Qt.AlignHCenter
                    font.family: Theme.fonts.display; font.pixelSize: Theme.fs.display; font.bold: true
                    color: Theme.colors.ink
                }
                Text {
                    text: "لا يوجد تقرير حالة بعد — ابدأ بثلاث خطوات:"
                    Layout.alignment: Qt.AlignHCenter
                    font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                    color: Theme.colors.ink2
                }
            }

            // three numbered steps
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0
                Repeater {
                    model: [
                        { n: "١", title: "اضبط محرّك الذكاء الاصطناعي", desc: "اختر المزوّد وأدخِل المفاتيح", page: 4, cta: "الإعدادات" },
                        { n: "٢", title: "أضِف تقارير ميدانية", desc: "يدوياً أو ارفع ملفات أو اجمع من المصادر", page: 0, cta: "إدخال البيانات" },
                        { n: "٣", title: "شغّل التحليل الذكي", desc: "الوكلاء يحلّلون ويولّدون ملخّص الحالة", page: 1, cta: "التحليل" }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 74
                        color: "transparent"
                        // hairline separators between steps
                        Rectangle {
                            visible: index > 0
                            anchors { top: parent.top; left: parent.left; right: parent.right }
                            height: 1; color: Theme.colors.border
                        }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 4; anchors.rightMargin: 4
                            spacing: 16
                            // number badge (leading = right in RTL)
                            Rectangle {
                                width: 34; height: 34; radius: 17
                                color: Theme.colors.accentSoft
                                Layout.alignment: Qt.AlignVCenter
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.n
                                    font.family: Theme.fonts.display; font.pixelSize: Theme.fs.section; font.bold: true
                                    color: Theme.colors.accent
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: modelData.title
                                    font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body; font.bold: true
                                    color: Theme.colors.ink
                                }
                                Text {
                                    text: modelData.desc
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                                    color: Theme.colors.ink3
                                }
                            }
                            AppButton {
                                text: modelData.cta
                                kind: index === 0 ? "accent" : "ghost"
                                implicitHeight: 34
                                Layout.alignment: Qt.AlignVCenter
                                onClicked: app.goTo(modelData.page)
                            }
                        }
                    }
                }
            }
        }
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        visible: page.hasData
        contentWidth: availableWidth
        clip: true

        // centered report column
        Item {
            width: scroll.availableWidth
            implicitHeight: column.implicitHeight + 72

            ColumnLayout {
                id: column
                width: Math.max(0, Math.min(840, parent.width - 96))
                anchors.horizontalCenter: parent.horizontalCenter
                y: 40
                spacing: 30

                // ── title + report meta ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "تقرير حالة المشروع"
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fs.display; font.bold: true
                            color: Theme.colors.ink
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: page.reportDate
                            visible: page.reportDate !== ""
                            font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.caption
                            color: Theme.colors.ink3
                            LayoutMirroring.enabled: false
                            Layout.alignment: Qt.AlignVCenter
                        }
                        AppButton {
                            text: "مسح اللوحة"; kind: "ghost"; implicitHeight: 30
                            Layout.alignment: Qt.AlignVCenter
                            onClicked: app.clearDashboard()
                        }
                    }
                    // one-line health statement
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        spacing: 9
                        Text {
                            text: "الحالة العامة"
                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
                            color: Theme.colors.ink2
                        }
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: Theme.statusColor(page.health)
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: page.health
                            font.family: Theme.fonts.display; font.pixelSize: Theme.fs.section; font.bold: true
                            color: Theme.statusColor(page.health)
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.topMargin: 6; height: 2; color: Theme.colors.accent; opacity: 0.9 }
                }

                // ── metrics table ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    ReportSection { title: "المؤشرات الرئيسية" }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: page.width < 720 ? 1 : 2
                        columnSpacing: 48; rowSpacing: 13
                        Repeater {
                            model: (page.model && page.model.kpis) ? page.model.kpis : []
                            delegate: MetricRow {
                                Layout.fillWidth: true
                                label: modelData.name ? modelData.name : ""
                                value: (modelData.value !== undefined ? modelData.value : "—") + ""
                                status: modelData.status ? modelData.status : ""
                            }
                        }
                    }
                }

                // ── executive summary ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ReportSection { title: "الملخص التنفيذي" }
                    Text {
                        Layout.fillWidth: true
                        text: (page.model && page.model.executive_summary)
                              ? page.model.executive_summary : "—"
                        wrapMode: Text.WordWrap
                        LayoutMirroring.enabled: false   // else the AlignRight below flips to AlignLeft
                        horizontalAlignment: Text.AlignRight
                        lineHeight: 1.5
                        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
                        color: Theme.colors.ink
                    }
                }

                // ── action plan ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ReportSection { title: "خطة العمل الفورية" }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Repeater {
                            model: (page.model && page.model.top_actions) ? page.model.top_actions : []
                            delegate: ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.topMargin: 13; Layout.bottomMargin: 13
                                    spacing: 13
                                    // Arabic-Indic order numeral — body font: Kufi's
                                    // digits are short by design and read weak here
                                    Text {
                                        text: page.arabicNumeral(index + 1)
                                        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.title; font.bold: true
                                        color: Theme.colors.accent
                                        Layout.alignment: Qt.AlignTop
                                        Layout.topMargin: 1
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Text {
                                            text: modelData.action ? modelData.action : ""
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                            // no explicit horizontalAlignment: Arabic content's
                                            // own implicit RTL direction already right-aligns it;
                                            // an explicit AlignRight here gets double-mirrored by
                                            // the app-wide LayoutMirroring and lands on the left
                                            // (see 88ca9e6), stranding it away from the numeral.
                                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
                                            color: Theme.colors.ink
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: {
                                                var parts = []
                                                if (modelData.owner) parts.push(modelData.owner)
                                                if (modelData.deadline) parts.push(modelData.deadline)
                                                if (modelData.impact) parts.push(modelData.impact)
                                                return parts.join("  ·  ")
                                            }
                                            visible: text !== ""
                                            wrapMode: Text.WordWrap
                                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                                            color: Theme.colors.ink2
                                        }
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true; height: 1
                                    color: Theme.colors.border
                                    visible: index < ((page.model && page.model.top_actions) ? page.model.top_actions.length - 1 : 0)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Western digits -> Arabic-Indic numerals for the native-document feel.
    function arabicNumeral(n) {
        var map = ["٠","١","٢","٣","٤","٥","٦","٧","٨","٩"]
        return ("" + n).replace(/[0-9]/g, function (d) { return map[+d] })
    }
}
