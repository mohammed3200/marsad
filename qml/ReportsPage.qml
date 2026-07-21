import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "التقارير"
    subtitle: "تصدير تقرير الحالة الحالي بصيغة PDF أو Excel، أو إرساله بالبريد"

    readonly property bool hasResults: app.dashModel && app.dashModel.overall_health !== undefined
    readonly property string health: hasResults ? app.dashModel.overall_health : "—"
    property string notice: ""
    property bool noticeError: false

    onHasResultsChanged: if (!pg.hasResults) { pg.notice = ""; pg.noticeError = false }

    Connections {
        target: app
        function onExportDone(path) { pg.notice = "حُفظ الملف: " + path; pg.noticeError = false }
        function onExportFailed(msg) { pg.notice = "تعذّر التصدير: " + msg; pg.noticeError = true }
    }

    EmptyState {
        Layout.fillWidth: true
        Layout.preferredHeight: 160
        visible: !pg.hasResults
        message: "لا يوجد تقرير للتصدير"
        hint: "شغّل التحليل من «التحليل والوكلاء» أولاً"
        actions: [
            AppButton { text: "الانتقال إلى «التحليل والوكلاء»"; kind: "accent"; onClicked: app.goTo(1) }
        ]
    }

    ColumnLayout {
        Layout.fillWidth: true
        visible: pg.hasResults
        spacing: 16

        ReportSection { title: "تصدير التقرير الحالي" }

        // meta line
        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            Text {
                text: "الحالة العامة"
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body; color: Theme.colors.ink2
            }
            Rectangle {
                width: 8; height: 8; radius: 4
                color: Theme.statusColor(pg.health)
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                text: pg.health
                font.family: Theme.fonts.display; font.pixelSize: Theme.fs.section; font.bold: true
                color: Theme.statusColor(pg.health)
            }
            Item { Layout.fillWidth: true }
            Text {
                text: app.reportDate
                font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.caption; color: Theme.colors.ink3
                LayoutMirroring.enabled: false
            }
        }

        // export actions
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            AppButton { text: "تصدير PDF"; kind: "accent"; onClicked: { pg.notice = ""; pg.noticeError = false; app.exportPdf("") } }
            AppButton { text: "تصدير Excel"; kind: "accent"; onClicked: { pg.notice = ""; pg.noticeError = false; app.exportExcel("") } }
            AppButton { text: "فتح مجلد التقارير"; kind: "ghost"; onClicked: app.openReportsFolder() }
            Item { Layout.fillWidth: true }
        }

        Text {
            text: pg.notice
            visible: pg.notice !== ""
            Layout.fillWidth: true
            wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignRight
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: pg.noticeError ? Theme.colors.red : Theme.colors.ink2
        }
    }

    // email
    ColumnLayout {
        Layout.fillWidth: true
        visible: pg.hasResults
        spacing: 12
        ReportSection { title: "الإرسال بالبريد" }
        Text {
            Layout.fillWidth: true
            text: "يُرسَل التقرير إلى المستلمين المضبوطين في الإعدادات (خريطة البريد ← الإدارة)."
            wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignRight
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2
        }
        RowLayout {
            Layout.fillWidth: true
            AppButton { text: "إرسال تقرير بالبريد"; kind: "ghost"; onClicked: app.sendEmailReport() }
            Item { Layout.fillWidth: true }
        }
    }
}
