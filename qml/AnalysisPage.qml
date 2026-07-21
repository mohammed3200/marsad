import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "التحليل والوكلاء"
    subtitle: "تشغيل أسطول الوكلاء على التقارير المُجمَّعة وإنتاج تقرير الحالة"

    property int progressPct: 0
    property string logText: ""
    property bool failed: false

    function appendLog(m) {
        var lines = (pg.logText === "" ? m : pg.logText + m).split("\n")
        if (lines.length > 200)
            lines = lines.slice(lines.length - 200)
        pg.logText = lines.join("\n") + "\n"
        Qt.callLater(function() {
            logView.ScrollBar.vertical.position = 1.0 - logView.ScrollBar.vertical.size
        })
    }

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
        function onLogMessage(m) { pg.appendLog(m) }
        function onAnalysisFailed(msg) { pg.failed = true }
    }

    // ── run control ──
    RowLayout {
        Layout.fillWidth: true
        spacing: 14
        AppButton {
            text: app.busy ? "جارٍ التحليل…" : "بدء التحليل"
            kind: "accent"; enabled: !app.busy
            onClicked: { pg.logText = ""; pg.progressPct = 0; pg.failed = false; app.runAnalysis() }
        }
        // progress track
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 6; radius: 3
            color: pg.failed ? Theme.colors.red : Theme.colors.fill
            Rectangle {
                width: parent.width * pg.progressPct / 100
                height: parent.height; radius: 3
                color: Theme.colors.accent
                Behavior on width { NumberAnimation { duration: 200 } }
            }
        }
        Text {
            text: pg.progressPct + "%"
            font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2
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
                    last: model.index === app.agentCount - 1
                    hoverable: false
                    RowLayout {
                        anchors.fill: parent
                        spacing: 12
                        Text {
                            text: model.name
                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
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
                            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
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
                id: logView
                anchors.fill: parent
                anchors.margins: 10
                clip: true
                Text {
                    width: parent.width
                    text: pg.logText === "" ? "لم يبدأ التشغيل بعد." : pg.logText
                    font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
                    color: pg.logText === "" ? Theme.colors.ink3 : Theme.colors.ink2
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignRight
                    lineHeight: 1.35
                }
            }
        }
    }
}
