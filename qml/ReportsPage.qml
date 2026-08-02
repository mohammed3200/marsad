import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "التقارير"
    subtitle: "عاين التقرير الحالي، صدّره بصيغة PDF أو Excel، أرسله بالبريد، أو ارجع لملفات سابقة"

    readonly property bool hasResults: app.dashModel && app.dashModel.overall_health !== undefined
    readonly property string health: hasResults ? app.dashModel.overall_health : "—"
    readonly property int kpiCount:    hasResults && app.dashModel.kpis        ? app.dashModel.kpis.length        : 0
    readonly property int actionCount: hasResults && app.dashModel.top_actions ? app.dashModel.top_actions.length : 0
    readonly property var  recipients: app.recipientsModel || []
    readonly property int  recipCount: recipients.length
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
        Layout.preferredHeight: implicitHeight
        Layout.minimumHeight: implicitHeight
        visible: !pg.hasResults
        message: "لا يوجد تقرير للتصدير"
        hint: "شغّل التحليل من «التحليل والوكلاء» أولاً"
        actions: [
            AppButton { text: "الانتقال إلى «التحليل والوكلاء»"; kind: "accent"; onClicked: app.goTo(1) }
        ]
    }

    // ═══════════ التقرير الحالي ═══════════
    ColumnLayout {
        Layout.fillWidth: true
        visible: pg.hasResults
        spacing: 14

        ReportSection { title: "التقرير الحالي" }

        // meta line: health + date
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
            Text {
                text: pg.kpiCount + " مؤشرات أداء · " + pg.actionCount + " إجراءات عاجلة"
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption; color: Theme.colors.ink3
                Layout.alignment: Qt.AlignVCenter
            }
            Item { Layout.fillWidth: true }
            Text {
                text: app.reportDate
                font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.caption; color: Theme.colors.ink3
                LayoutMirroring.enabled: false
            }
        }

        // preview excerpt — ما سيُصدَّر فعلاً
        Text {
            visible: text !== ""
            text: pg.hasResults ? (app.dashModel.executive_summary || "") : ""
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            maximumLineCount: 3; elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink2
        }

        // export actions
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            AppButton { text: "تصدير PDF"; kind: "accent"; onClicked: { pg.notice = ""; pg.noticeError = false; app.exportPdf("") } }
            AppButton { text: "تصدير Excel"; kind: "ghost"; onClicked: { pg.notice = ""; pg.noticeError = false; app.exportExcel("") } }
            AppButton { text: "فتح مجلد التقارير"; kind: "ghost"; onClicked: app.openReportsFolder() }
            Item { Layout.fillWidth: true }
        }

        Text {
            text: pg.notice
            visible: pg.notice !== ""
            Layout.fillWidth: true
            wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignRight
            maximumLineCount: 2; elide: Text.ElideRight
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: pg.noticeError ? Theme.colors.red : Theme.colors.ink2
        }
    }

    // ═══════════ التقارير السابقة ═══════════
    ColumnLayout {
        Layout.fillWidth: true
        visible: pg.hasResults
        spacing: 10

        ReportSection { title: "التقارير السابقة" }

        Text {
            visible: app.exportsModel.length === 0
            text: "لا توجد ملفات مُصدَّرة بعد — أول تصدير يظهر هنا."
            Layout.fillWidth: true
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3
        }

        Repeater {
            model: app.exportsModel
            delegate: ListRow {
                last: index === app.exportsModel.length - 1
                RowLayout {
                    anchors.fill: parent
                    spacing: 12
                    Text {
                        Layout.fillWidth: true
                        text: modelData.name
                        elide: Text.ElideMiddle
                        font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small
                        color: Theme.colors.ink
                        LayoutMirroring.enabled: false
                        horizontalAlignment: Text.AlignLeft
                    }
                    Text {
                        text: modelData.sizeKb + " KB"
                        font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.caption
                        color: Theme.colors.ink3
                        LayoutMirroring.enabled: false
                    }
                    Text {
                        text: modelData.date
                        font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.caption
                        color: Theme.colors.ink3
                        LayoutMirroring.enabled: false
                    }
                }
                TapHandler { onTapped: app.openFile(modelData.path) }
            }
        }
    }

    // ═══════════ الإرسال بالبريد ═══════════
    ColumnLayout {
        Layout.fillWidth: true
        visible: pg.hasResults
        spacing: 12

        ReportSection { title: "الإرسال بالبريد" }

        // recipients known → show exactly who; unknown → warn before the click
        RowLayout {
            Layout.fillWidth: true
            visible: pg.recipCount > 0
            spacing: 8
            Text {
                text: "سيُرسَل إلى:"
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2
            }
            Text {
                Layout.fillWidth: true
                text: pg.recipients.join("، ")
                elide: Text.ElideRight
                maximumLineCount: 2; wrapMode: Text.WrapAnywhere
                font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small
                color: Theme.colors.ink2
                LayoutMirroring.enabled: false
                horizontalAlignment: Text.AlignLeft
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: pg.recipCount === 0
            spacing: 8
            Rectangle {
                width: 8; height: 8; radius: 4
                color: Theme.colors.amber
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                Layout.fillWidth: true
                text: "لا يوجد مستلمون مضبوطون — اضبط «مستلمو التقرير» في الإعدادات أولاً"
                wrapMode: Text.WordWrap
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                color: Theme.colors.ink2
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            AppButton {
                text: app.sendingEmail ? "جارٍ الإرسال…" : "إرسال تقرير بالبريد"; kind: "ghost"
                enabled: pg.recipCount > 0 && !app.sendingEmail
                onClicked: app.sendEmailReport()
            }
            AppButton {
                text: "فتح الإعدادات"; kind: "ghost"
                visible: pg.recipCount === 0
                onClicked: app.goTo(4)
            }
            Item { Layout.fillWidth: true }
        }
    }
}
