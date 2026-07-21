import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "الإعدادات"
    subtitle: "اضبط محرّك الذكاء الاصطناعي ومصادر البيانات — كل شيء من هنا، بدون تعديل ملفات"

    property string testMsg: ""
    property int testState: 0
    property string emailMsg: ""
    property int emailState: 0

    // backend index ↔ id
    readonly property var backendIds: ["ollama", "claude", "openai", "gemini", "azure"]
    function backendIndex(id) { var i = backendIds.indexOf(id); return i < 0 ? 0 : i }
    function resetEngineTest() { pg.testState = 0; pg.testMsg = "" }
    function resetEmailTest()  { pg.emailState = 0; pg.emailMsg = "" }

    // OpenAI-compatible provider presets (base_url, model)
    readonly property var oaPresets: [
        { name: "OpenAI",            url: "https://api.openai.com/v1",        model: "gpt-4o-mini" },
        { name: "OpenRouter",        url: "https://openrouter.ai/api/v1",     model: "openai/gpt-4o-mini" },
        { name: "Groq",              url: "https://api.groq.com/openai/v1",   model: "llama-3.3-70b-versatile" },
        { name: "Together",          url: "https://api.together.xyz/v1",      model: "meta-llama/Llama-3.3-70B-Instruct-Turbo" },
        { name: "DeepSeek",          url: "https://api.deepseek.com/v1",      model: "deepseek-chat" },
        { name: "LM Studio (محلي)",  url: "http://localhost:1234/v1",         model: "local-model" },
        { name: "مخصّص",             url: "",                                 model: "" }
    ]

    Connections {
        target: app
        function onConnectionTested(ok, msg) { pg.testState = ok ? 1 : -1; pg.testMsg = msg }
        function onEmailTested(ok, msg)      { pg.emailState = ok ? 1 : -1; pg.emailMsg = msg }
    }

    // ═══════════ AI engine ═══════════
    ReportSection { title: "محرّك الذكاء الاصطناعي" }
    FormCombo {
        id: backendC
        label: "المزوّد"
        options: ["Ollama — محلي", "Claude API", "OpenAI / متوافق", "Google Gemini", "Azure OpenAI"]
        currentIndex: pg.backendIndex(app.settings.ai_backend)
    }
    FormField { id: aiTimeout; label: "مهلة الاستجابة (ثانية)"; ltr: true; intOnly: true; Component.onCompleted: text = (app.settings.ai_timeout || 180).toString() }

    // ── Ollama ──
    ColumnLayout {
        Layout.fillWidth: true; spacing: 14
        visible: backendC.currentIndex === 0
        FormField { id: ollamaUrl;   label: "عنوان الخادم"; ltr: true; Component.onCompleted: text = app.settings.ollama_url || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: ollamaModel; label: "اسم النموذج"; ltr: true; Component.onCompleted: text = app.settings.ollama_model || "" }
    }

    // ── Claude ──
    ColumnLayout {
        Layout.fillWidth: true; spacing: 14
        visible: backendC.currentIndex === 1
        FormField { id: claudeKey;   label: "مفتاح API"; ltr: true; password: true; Component.onCompleted: text = app.settings.claude_api_key || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: claudeModel; label: "اسم النموذج"; ltr: true; Component.onCompleted: text = app.settings.claude_model || "" }
    }

    // ── OpenAI / compatible ──
    ColumnLayout {
        Layout.fillWidth: true; spacing: 14
        visible: backendC.currentIndex === 2
        FormCombo {
            id: oaPreset
            label: "الخدمة"
            options: pg.oaPresets.map(function(p){ return p.name })
            Component.onCompleted: {
                var u = app.settings.openai_base_url || ""
                var i = pg.oaPresets.findIndex(function(p){ return p.url === u })
                currentIndex = i >= 0 ? i : pg.oaPresets.length - 1
            }
            onActivated: function(i) {
                var p = pg.oaPresets[i]
                if (p.url)   openaiBase.text = p.url
                if (p.model) openaiModel.text = p.model
            }
        }
        FormField { id: openaiBase;  label: "عنوان الخدمة (Base URL)"; ltr: true; Component.onCompleted: text = app.settings.openai_base_url || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: openaiKey;   label: "مفتاح API"; ltr: true; password: true; Component.onCompleted: text = app.settings.openai_api_key || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: openaiModel; label: "اسم النموذج"; ltr: true; Component.onCompleted: text = app.settings.openai_model || "" }
    }

    // ── Gemini ──
    ColumnLayout {
        Layout.fillWidth: true; spacing: 14
        visible: backendC.currentIndex === 3
        FormField { id: geminiKey;   label: "مفتاح API"; ltr: true; password: true; Component.onCompleted: text = app.settings.gemini_api_key || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: geminiModel; label: "اسم النموذج"; ltr: true; Component.onCompleted: text = app.settings.gemini_model || "" }
    }

    // ── Azure ──
    ColumnLayout {
        Layout.fillWidth: true; spacing: 14
        visible: backendC.currentIndex === 4
        FormField { id: azureEndpoint; label: "Endpoint"; ltr: true; Component.onCompleted: text = app.settings.azure_endpoint || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: azureDeploy;   label: "اسم النشر (Deployment)"; ltr: true; Component.onCompleted: text = app.settings.azure_deployment || "" }
        FormField { id: azureKey;      label: "مفتاح API"; ltr: true; password: true; Component.onCompleted: text = app.settings.azure_api_key || ""; onTextChanged: pg.resetEngineTest() }
        FormField { id: azureVersion;  label: "إصدار الواجهة (api-version)"; ltr: true; Component.onCompleted: text = app.settings.azure_api_version || "" }
    }

    // engine test
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        AppButton { text: "اختبار المحرّك"; kind: "ghost"; enabled: !app.testingEngine
            onClicked: { pg.testState = 2; pg.testMsg = "جارٍ الفحص…"; app.testConnection() } }
        Rectangle {
            width: 8; height: 8; radius: 4
            visible: pg.testState !== 0
            color: pg.testState === 1 ? Theme.colors.green : pg.testState === 2 ? Theme.colors.amber : Theme.colors.red
            Layout.alignment: Qt.AlignVCenter
        }
        Text {
            text: pg.testMsg
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink2
        }
    }

    // ═══════════ Email ═══════════
    ReportSection { title: "البريد الإلكتروني" }
    FormField { id: emailUser; label: "البريد"; ltr: true; Component.onCompleted: text = app.settings.email_user || ""; onTextChanged: pg.resetEmailTest() }
    FormField { id: emailPass; label: "كلمة المرور / App Password"; ltr: true; password: true; Component.onCompleted: text = app.settings.email_password || ""; onTextChanged: pg.resetEmailTest() }
    RowLayout {
        Layout.fillWidth: true
        spacing: 14
        FormField { id: imapHost; label: "خادم IMAP"; ltr: true; Component.onCompleted: text = app.settings.imap_host || ""; onTextChanged: pg.resetEmailTest() }
        FormField { id: smtpHost; label: "خادم SMTP"; ltr: true; Component.onCompleted: text = app.settings.smtp_host || ""; onTextChanged: pg.resetEmailTest() }
        FormField { id: smtpPort; label: "منفذ SMTP"; ltr: true; intOnly: true; Layout.preferredWidth: 120; Component.onCompleted: text = (app.settings.smtp_port || 587).toString(); onTextChanged: pg.resetEmailTest() }
    }
    FormField {
        id: recipients
        label: "مستلمو التقرير (افصل بينهم بفاصلة)"
        ltr: true
        Component.onCompleted: text = (app.settings.report_recipients || []).join(", ")
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        AppButton { text: "اختبار البريد"; kind: "ghost"; enabled: !app.testingEmail
            onClicked: { pg.emailState = 2; pg.emailMsg = "جارٍ الفحص…"; app.testEmail() } }
        Rectangle {
            width: 8; height: 8; radius: 4
            visible: pg.emailState !== 0
            color: pg.emailState === 1 ? Theme.colors.green : pg.emailState === 2 ? Theme.colors.amber : Theme.colors.red
            Layout.alignment: Qt.AlignVCenter
        }
        Text {
            text: pg.emailMsg
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink2
        }
    }

    // ═══════════ ERP folder ═══════════
    ReportSection { title: "مجلد ERP" }
    Text {
        text: "أي ملف (Excel / PDF / CSV / Word…) يوضع في هذا المجلد يُقرأ عند «جمع من المصادر»."
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption; color: Theme.colors.ink3
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        FormField { id: erpFolder; label: "المسار"; ltr: true; Component.onCompleted: text = app.settings.erp_folder || "" }
        AppButton {
            text: "استعراض"; kind: "ghost"; Layout.alignment: Qt.AlignBottom
            onClicked: { var d = app.pickErpFolder(); if (d.length) erpFolder.text = d }
        }
    }

    // ═══════════ WhatsApp ═══════════
    ReportSection { title: "واتساب" }
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        CheckBox {
            id: waEnabled
            checked: app.settings.whatsapp_enabled === true
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body
            contentItem: Text {
                text: "تفعيل استقبال واتساب"; rightPadding: waEnabled.indicator.width + 8
                font: waEnabled.font; color: Theme.colors.ink; verticalAlignment: Text.AlignVCenter
            }
        }
        Item { Layout.fillWidth: true }
        FormField { id: waPort; label: "منفذ المستقبِل"; ltr: true; intOnly: true; Layout.preferredWidth: 140; Component.onCompleted: text = (app.settings.whatsapp_port || 5051).toString() }
    }
    Text {
        text: "واتساب يحتاج جسر Node.js يعمل مرة واحدة: «توليد ملف الجسر»، ثم في مجلد البيانات "
            + "شغّل npm install ثم node whatsapp_bridge.js وامسح رمز QR بهاتفك."
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption; color: Theme.colors.ink3
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        AppButton { text: "توليد ملف الجسر"; kind: "ghost"; onClicked: app.generateWhatsAppBridge() }
        AppButton { text: "فحص Node.js"; kind: "ghost"; onClicked: app.checkNode() }
        Item { Layout.fillWidth: true }
    }

    // ═══════════ save ═══════════
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.colors.border }
    RowLayout {
        Layout.fillWidth: true
        Item { Layout.fillWidth: true }
        AppButton {
            text: "حفظ الإعدادات"; kind: "accent"
            onClicked: {
                app.saveSettings({
                "ai_backend":        pg.backendIds[backendC.currentIndex],
                "ai_timeout":        parseInt(aiTimeout.text) || 180,
                "ollama_url":        ollamaUrl.text,
                "ollama_model":      ollamaModel.text,
                "claude_api_key":    claudeKey.text,
                "claude_model":      claudeModel.text,
                "openai_base_url":   openaiBase.text,
                "openai_api_key":    openaiKey.text,
                "openai_model":      openaiModel.text,
                "gemini_api_key":    geminiKey.text,
                "gemini_model":      geminiModel.text,
                "azure_endpoint":    azureEndpoint.text,
                "azure_deployment":  azureDeploy.text,
                "azure_api_key":     azureKey.text,
                "azure_api_version": azureVersion.text,
                "email_user":        emailUser.text,
                "email_password":    emailPass.text,
                "imap_host":         imapHost.text,
                "smtp_host":         smtpHost.text,
                "smtp_port":         parseInt(smtpPort.text) || 587,
                "report_recipients": recipients.text.split(",").map(function(s){ return s.trim() }).filter(function(s){ return s.length > 0 }),
                "erp_folder":        erpFolder.text,
                "whatsapp_enabled":  waEnabled.checked,
                "whatsapp_port":     parseInt(waPort.text) || 5051
                })
                pg.resetEngineTest(); pg.resetEmailTest()
            }
        }
    }
}
