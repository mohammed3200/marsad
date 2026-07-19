import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "إدخال البيانات"
    subtitle: "أضف تقارير ميدانية أو حمّل النماذج، ثم انتقل إلى «التحليل والوكلاء»"

    readonly property var deptOptions: [
        "شبكة الراديو RAN", "شبكة النواة Core", "العمليات", "الجودة", "السلامة",
        "الأعمال الإنشائية", "التكاليف", "العقود", "المشتريات", "المخازن والتوريد"
    ]
    readonly property var sourceOptions: ["يدوي", "بريد إلكتروني", "واتساب", "ERP"]

    // ── actions ──
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        AppButton { text: "تحميل نماذج"; kind: "accent"; onClicked: app.loadSamples() }
        AppButton { text: "جمع من المصادر"; kind: "ghost"; onClicked: app.collectReports() }
        Item { Layout.fillWidth: true }
        AppButton {
            text: "مسح الكل"; kind: "ghost"
            enabled: app.reportCount > 0
            onClicked: app.clearReports()
        }
    }

    // ── queued reports ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 10
        ReportSection {
            title: "التقارير الجاهزة للتحليل"
        }
        Text {
            text: app.reportCount + " تقرير في القائمة"
            font.family: Theme.fonts.body; font.pixelSize: 12; color: Theme.colors.ink3
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.preferredHeight: 140
            visible: app.reportCount === 0
            icon: "▢"
            message: "لا توجد تقارير بعد"
            hint: "حمّل النماذج أو أضف تقريراً من النموذج بالأسفل"
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: app.reportsModel
                delegate: ListRow {
                    last: index === app.reportCount - 1
                    RowLayout {
                        anchors.fill: parent
                        spacing: 12
                        // source + dept tag
                        ColumnLayout {
                            Layout.preferredWidth: 120
                            spacing: 2
                            Text {
                                text: source
                                font.family: Theme.fonts.body; font.pixelSize: 13; font.bold: true
                                color: Theme.colors.accent
                            }
                            Text {
                                text: dept
                                font.family: Theme.fonts.body; font.pixelSize: 11
                                color: Theme.colors.ink3
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: (from_ || "—") + "  ·  " + (date || "")
                                font.family: Theme.fonts.body; font.pixelSize: 12
                                color: Theme.colors.ink2
                            }
                            Text {
                                Layout.fillWidth: true
                                text: model.content
                                maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignRight
                                font.family: Theme.fonts.body; font.pixelSize: 13
                                color: Theme.colors.ink
                            }
                        }
                        AppButton {
                            text: "حذف"; kind: "ghost"; implicitHeight: 30
                            onClicked: app.removeReport(index)
                        }
                    }
                }
            }
        }
    }

    // ── add report ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 12
        ReportSection { title: "إضافة تقرير يدوي" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            FormCombo { id: srcC; label: "المصدر"; options: pg.sourceOptions }
            FormCombo { id: deptC; label: "الإدارة"; options: pg.deptOptions }
        }
        FormField { id: fromF; label: "المُرسِل"; placeholder: "اسم المرسل أو الجهة" }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            Text {
                text: "نص التقرير"
                font.family: Theme.fonts.body; font.pixelSize: 13; color: Theme.colors.ink2
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                TextArea {
                    id: contentF
                    placeholderText: "الصق أو اكتب محتوى التقرير الميداني هنا…"
                    placeholderTextColor: Theme.colors.ink3
                    color: Theme.colors.ink
                    font.family: Theme.fonts.body; font.pixelSize: 14
                    wrapMode: TextArea.Wrap
                    horizontalAlignment: Text.AlignRight
                    leftPadding: 12; rightPadding: 12; topPadding: 10; bottomPadding: 10
                    background: Rectangle {
                        radius: 8; color: Theme.colors.bg
                        border.width: contentF.activeFocus ? 2 : 1
                        border.color: contentF.activeFocus ? Theme.colors.accent : Theme.colors.borderHi
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            AppButton {
                text: "إضافة إلى القائمة"; kind: "accent"
                onClicked: {
                    app.addReport({
                        "source": srcC.value, "dept": deptC.value,
                        "from": fromF.text, "content": contentF.text
                    })
                    contentF.text = ""; fromF.text = ""
                }
            }
        }
    }
}
