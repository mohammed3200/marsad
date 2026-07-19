import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "التحليل والوكلاء"
    subtitle: "تشغيل أسطول الوكلاء على التقارير المُجمَّعة وإنتاج تقرير الحالة"

    property int progressPct: 0
    property string logText: ""

    function stateWord(s) {
        return s === "running" ? "قيد التشغيل"
             : s === "done"    ? "تم"
             : s === "error"   ? "خطأ" : "بالانتظار"
    }
    function stateColor(s) {
        return s === "running" ? Theme.colors.amber
             : s === "done"    ? Theme.colors.green
             : s === "error"   ? Theme.colors.red : Theme.colors.ink3
    }

    Connections {
        target: app
        function onProgress(p) { pg.progressPct = p }
        function onLogMessage(m) { pg.logText += m + "\n" }
    }

    // ── run control ──
    RowLayout {
        Layout.fillWidth: true
        spacing: 14
        AppButton {
            text: app.busy ? "جارٍ التحليل…" : "بدء التحليل"
            kind: "accent"; enabled: !app.busy
            onClicked: { pg.logText = ""; pg.progressPct = 0; app.runAnalysis() }
        }
        // progress track
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 6; radius: 3
            color: Theme.colors.border
            Rectangle {
                width: parent.width * pg.progressPct / 100
                height: parent.height; radius: 3
                color: Theme.colors.accent
                Behavior on width { NumberAnimation { duration: 200 } }
            }
        }
        Text {
            text: pg.progressPct + "%"
            font.family: Theme.fonts.mono; font.pixelSize: 13; color: Theme.colors.ink2
            LayoutMirroring.enabled: false
        }
    }

    // ── agents ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 8
        ReportSection { title: "حالة الوكلاء" }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: app.agentsModel
                delegate: ListRow {
                    last: index === app.agentsModel.rowCount() - 1
                    hoverable: false
                    RowLayout {
                        anchors.fill: parent
                        spacing: 12
                        Text {
                            text: model.name
                            font.family: Theme.fonts.body; font.pixelSize: 14
                            color: Theme.colors.ink
                        }
                        Item { Layout.fillWidth: true }
                        Rectangle {
                            width: 7; height: 7; radius: 4
                            visible: model.state !== "idle"
                            color: pg.stateColor(model.state)
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Text {
                            text: pg.stateWord(model.state)
                            font.family: Theme.fonts.body; font.pixelSize: 13
                            font.bold: model.state === "running"
                            color: pg.stateColor(model.state)
                        }
                    }
                }
            }
        }
    }

    // ── log ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 10
        ReportSection { title: "سجل التشغيل" }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 160
            radius: 8; color: Theme.colors.fill
            border.width: 1; border.color: Theme.colors.border
            ScrollView {
                anchors.fill: parent
                anchors.margins: 10
                clip: true
                Text {
                    width: parent.width
                    text: pg.logText === "" ? "لم يبدأ التشغيل بعد." : pg.logText
                    font.family: Theme.fonts.mono; font.pixelSize: 12
                    color: pg.logText === "" ? Theme.colors.ink3 : Theme.colors.ink2
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignRight
                    lineHeight: 1.35
                }
            }
        }
    }
}
