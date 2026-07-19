import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "الإعدادات"
    subtitle: "اختر محرّك الذكاء الاصطناعي واضبط الاتصال"

    property string testMsg: ""
    property int testState: 0   // 0 none, 1 ok, -1 fail

    Connections {
        target: app
        function onConnectionTested(ok, msg) {
            pg.testState = ok ? 1 : -1
            pg.testMsg = msg
        }
    }

    // ── engine ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 14
        ReportSection { title: "محرّك الذكاء الاصطناعي" }
        FormCombo {
            id: backendC
            label: "المحرّك"
            options: ["Ollama — محلي", "Claude API"]
            currentIndex: app.settings.ai_backend === "claude" ? 1 : 0
        }
        readonly property bool isClaude: backendC.currentIndex === 1
    }

    // ── ollama ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 14
        ReportSection { title: "إعداد Ollama" }
        FormField { id: ollamaUrl;   label: "عنوان الخادم"; ltr: true; text: app.settings.ollama_url || "" }
        FormField { id: ollamaModel; label: "اسم النموذج"; ltr: true; text: app.settings.ollama_model || "" }
    }

    // ── claude ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 14
        ReportSection { title: "إعداد Claude API" }
        FormField { id: claudeKey;   label: "مفتاح API"; ltr: true; password: true; text: app.settings.claude_api_key || "" }
        FormField { id: claudeModel; label: "اسم النموذج"; ltr: true; text: app.settings.claude_model || "" }
    }

    // ── connection test ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            AppButton { text: "اختبار الاتصال"; kind: "ghost"; onClicked: app.testConnection() }
            Rectangle {
                width: 8; height: 8; radius: 4
                visible: pg.testState !== 0
                color: pg.testState === 1 ? Theme.colors.green : Theme.colors.red
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                text: pg.testMsg
                font.family: Theme.fonts.body; font.pixelSize: 13
                color: pg.testState === 1 ? Theme.colors.green
                     : pg.testState === -1 ? Theme.colors.red : Theme.colors.ink2
            }
            Item { Layout.fillWidth: true }
        }
    }

    // ── save ──
    RowLayout {
        Layout.fillWidth: true
        Item { Layout.fillWidth: true }
        AppButton {
            text: "حفظ الإعدادات"; kind: "accent"
            onClicked: app.saveSettings({
                "ai_backend":   backendC.currentIndex === 1 ? "claude" : "ollama",
                "ollama_url":   ollamaUrl.text,
                "ollama_model": ollamaModel.text,
                "claude_api_key": claudeKey.text,
                "claude_model": claudeModel.text
            })
        }
    }
}
