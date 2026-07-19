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

    EmptyState {
        anchors.fill: parent
        visible: !page.hasData
        icon: "▢"
        message: "لا يوجد تقرير حالة بعد"
        hint: "شغّل التحليل من تبويب «التحليل والوكلاء» ليظهر ملخّص الحالة وخطة العمل"
    }

    ScrollView {
        anchors.fill: parent
        visible: page.hasData
        contentWidth: availableWidth
        clip: true

        // centered report column
        Item {
            width: page.width
            implicitHeight: column.implicitHeight + 72

            ColumnLayout {
                id: column
                width: Math.min(840, parent.width - 96)
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
                            font.family: Theme.fonts.display; font.pixelSize: 24; font.bold: true
                            color: Theme.colors.ink
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: page.reportDate
                            visible: page.reportDate !== ""
                            font.family: Theme.fonts.mono; font.pixelSize: 12
                            color: Theme.colors.ink3
                            LayoutMirroring.enabled: false
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }
                    // one-line health statement
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        spacing: 9
                        Text {
                            text: "الحالة العامة"
                            font.family: Theme.fonts.body; font.pixelSize: 15
                            color: Theme.colors.ink2
                        }
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: Theme.statusColor(page.health)
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: page.health
                            font.family: Theme.fonts.display; font.pixelSize: 16; font.bold: true
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
                        horizontalAlignment: Text.AlignRight
                        lineHeight: 1.5
                        font.family: Theme.fonts.body; font.pixelSize: 15
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
                                    // Arabic-Indic order numeral
                                    Text {
                                        text: page.arabicNumeral(index + 1)
                                        font.family: Theme.fonts.display; font.pixelSize: 18; font.bold: true
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
                                            horizontalAlignment: Text.AlignRight
                                            font.family: Theme.fonts.body; font.pixelSize: 15
                                            color: Theme.colors.ink
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            horizontalAlignment: Text.AlignRight
                                            text: {
                                                var parts = []
                                                if (modelData.owner) parts.push(modelData.owner)
                                                if (modelData.deadline) parts.push(modelData.deadline)
                                                if (modelData.impact) parts.push(modelData.impact)
                                                return parts.join("  ·  ")
                                            }
                                            visible: text !== ""
                                            wrapMode: Text.WordWrap
                                            font.family: Theme.fonts.body; font.pixelSize: 13
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
