import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "الإعدادات"
    subtitle: "اضبط محرّك الذكاء الاصطناعي ومصادر البيانات ثم احفظ — زرّا الاختبار يحفظان تلقائياً قبل الفحص"

    property string testMsg: ""
    property int testState: 0
    property string emailMsg: ""
    property int emailState: 0

    // backend index ↔ id
    readonly property var backendIds: ["ollama", "claude", "openai", "gemini", "azure"]
    function backendIndex(id) { var i = backendIds.indexOf(id); return i < 0 ? 0 : i }
    function resetEngineTest() { pg.testState = 0; pg.testMsg = "" }
    function resetEmailTest()  { pg.emailState = 0; pg.emailMsg = "" }

    // يجمع قيم النموذج الظاهرة — يستخدمها «حفظ الإعدادات» وزرّا الاختبار حتى
    // يُختبَر ما يراه المستخدم فعلاً، لا الإعدادات المحفوظة القديمة.
    function collectSettings() {
        return {
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
        }
    }

    function doSave() {
        app.saveSettings(pg.collectSettings())
        pg.resetEngineTest(); pg.resetEmailTest()
    }

    // اكتب النموذج المختار في حقل المزوّد الظاهر حالياً
    function setCurrentModel(m) {
        var b = backendC.currentIndex
        if (b === 0)      ollamaModel.text = m
        else if (b === 1) claudeModel.text = m
        else if (b === 2) openaiModel.text = m
        else if (b === 3) geminiModel.text = m
        else              azureDeploy.text = m
    }

    // أعد تعبئة الحقول من الإعدادات — يُستدعى بعد تبديل ملف المحرّك فقط
    // (لا يُربط بـ settingsChanged حتى لا تُمسح تعديلات غير محفوظة عند المزامنة)
    function reloadFields() {
        var s = app.settings
        backendC.currentIndex = pg.backendIndex(s.ai_backend)
        aiTimeout.text   = (s.ai_timeout || 180).toString()
        ollamaUrl.text   = s.ollama_url || ""
        ollamaModel.text = s.ollama_model || ""
        claudeKey.text   = s.claude_api_key || ""
        claudeModel.text = s.claude_model || ""
        openaiBase.text  = s.openai_base_url || ""
        openaiKey.text   = s.openai_api_key || ""
        openaiModel.text = s.openai_model || ""
        geminiKey.text   = s.gemini_api_key || ""
        geminiModel.text = s.gemini_model || ""
        azureEndpoint.text = s.azure_endpoint || ""
        azureDeploy.text = s.azure_deployment || ""
        azureKey.text    = s.azure_api_key || ""
        azureVersion.text = s.azure_api_version || ""
        emailUser.text   = s.email_user || ""
        emailPass.text   = s.email_password || ""
        imapHost.text    = s.imap_host || ""
        smtpHost.text    = s.smtp_host || ""
        smtpPort.text    = (s.smtp_port || 587).toString()
        recipients.text  = (s.report_recipients || []).join(", ")
        erpFolder.text   = s.erp_folder || ""
        waEnabled.checked = s.whatsapp_enabled === true
        waPort.text      = (s.whatsapp_port || 5051).toString()
    }

    // حالة الحفظ الحيّة — تقارن كل حقل ظاهر بالإعدادات المحفوظة
    readonly property bool dirty: computeDirty()
    function computeDirty() {
        var s = app.settings, c = pg.collectSettings()
        for (var k in c) {
            var a = s[k], b = c[k]
            if (typeof b === "boolean") { if ((a === true) !== b) return true }
            else if (typeof b === "number") { if ((parseFloat(a) || 0) !== b) return true }
            else if (Array.isArray(b))   { if ((a || []).join(",") !== b.join(",")) return true }
            else { if ((a === undefined || a === null ? "" : String(a)) !== String(b)) return true }
        }
        return false
    }

    // جاهزية كل قسم من الإعدادات المحفوظة (وليست قيم الحقول المؤقتة)
    function engineNote() {
        var b = pg.backendIds[backendC.currentIndex]
        if (b === "ollama") return "محلي — بلا مفتاح"
        var key = { "claude": "claude_api_key", "openai": "openai_api_key",
                    "gemini": "gemini_api_key", "azure": "azure_api_key" }[b]
        return (app.settings[key] || "") !== "" ? "المفتاح مضبوط" : "المفتاح غير مضبوط"
    }
    function engineWarn() {
        var b = pg.backendIds[backendC.currentIndex]
        if (b === "ollama") return false
        var key = { "claude": "claude_api_key", "openai": "openai_api_key",
                    "gemini": "gemini_api_key", "azure": "azure_api_key" }[b]
        return (app.settings[key] || "") === ""
    }
    function emailNote() {
        var u = app.settings.email_user || "", p = app.settings.email_password || ""
        if (u && p) return "مكتمل"
        var missing = []
        if (!u) missing.push("البريد")
        if (!p) missing.push("كلمة المرور")
        return "ينقصه: " + missing.join("، ")
    }
    function emailWarn() {
        return !((app.settings.email_user || "") && (app.settings.email_password || ""))
    }

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
    ReportSection { title: "محرّك الذكاء الاصطناعي"; note: pg.engineNote(); noteColor: pg.engineWarn() ? Theme.colors.amber : Theme.colors.ink3 }

    // ملفات المحرّك — احفظ الإعداد الحالي كملف وبدّل بين الملفات لاحقاً
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        FormCombo {
            id: profileC
            label: "ملف المحرّك"
            Layout.fillWidth: true
            options: ["الافتراضي (Ollama)"].concat(app.engineProfilesModel.map(function(p){ return p.name }))
            onActivated: function(i) {
                if (i > 0) { app.switchEngineProfile(options[i]); pg.reloadFields() }
            }
        }
        AppButton {
            text: "حذف الملف"; kind: "ghost"; Layout.alignment: Qt.AlignBottom
            visible: profileC.currentIndex > 0
            enabled: !app.busy
            onClicked: { app.deleteEngineProfile(profileC.options[profileC.currentIndex]); profileC.currentIndex = 0 }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        FormField { id: profileName; label: "احفظ الإعداد الحالي كملف"; placeholder: "مثال: Gemini العمل" }
        AppButton {
            text: "حفظ كملف"; kind: "ghost"; Layout.alignment: Qt.AlignBottom
            enabled: !app.busy
            onClicked: { app.saveSettings(pg.collectSettings()); app.saveEngineProfile(profileName.text); profileName.text = "" }
        }
    }

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

    // جلب قائمة النماذج من المزوّد الحالي بدل كتابة الاسم يدوياً
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        AppButton {
            text: app.modelsBusy ? "جارٍ الجلب…" : "جلب قائمة النماذج"; kind: "ghost"
            enabled: !app.modelsBusy && !app.busy
            onClicked: { app.saveSettings(pg.collectSettings()); app.fetchModels() }
        }
        FormCombo {
            id: modelsC
            Layout.fillWidth: true
            visible: app.modelsModel.length > 0
            options: app.modelsModel
            onActivated: function(i) { pg.setCurrentModel(app.modelsModel[i]) }
        }
    }

    // engine test
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        AppButton { text: "اختبار المحرّك"; kind: "ghost"; enabled: !app.testingEngine && !app.busy
            onClicked: { app.saveSettings(pg.collectSettings()); pg.testState = 2; pg.testMsg = "جارٍ الفحص…"; app.testConnection() } }
        Rectangle {
            width: 8; height: 8; radius: 4
            visible: pg.testState !== 0
            color: pg.testState === 1 ? Theme.colors.green : pg.testState === 2 ? Theme.colors.amber : Theme.colors.red
            Layout.alignment: Qt.AlignVCenter
        }
        Text {
            text: pg.testMsg
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            maximumLineCount: 2; elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink2
        }
    }

    // ═══════════ Email ═══════════
    ReportSection { title: "البريد الإلكتروني"; note: pg.emailNote(); noteColor: pg.emailWarn() ? Theme.colors.amber : Theme.colors.ink3 }
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
        AppButton { text: "اختبار البريد"; kind: "ghost"; enabled: !app.testingEmail && !app.busy
            onClicked: { app.saveSettings(pg.collectSettings()); pg.emailState = 2; pg.emailMsg = "جارٍ الفحص…"; app.testEmail() } }
        Rectangle {
            width: 8; height: 8; radius: 4
            visible: pg.emailState !== 0
            color: pg.emailState === 1 ? Theme.colors.green : pg.emailState === 2 ? Theme.colors.amber : Theme.colors.red
            Layout.alignment: Qt.AlignVCenter
        }
        Text {
            text: pg.emailMsg
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            maximumLineCount: 2; elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink2
        }
    }

    // ═══════════ ERP folder ═══════════
    ReportSection { title: "مجلد ERP"; note: (app.settings.erp_folder || "") !== "" ? "مضبوط" : "غير مضبوط" }
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
    ReportSection { title: "واتساب"; note: app.settings.whatsapp_enabled === true ? "مفعّل" : "معطّل" }
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

    // إعداد الجسر تسلسل حقيقي — الترقيم هنا يحمل معلومة (الخطوات مرتّبة)
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 12

        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Text { text: "1"; font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3; Layout.preferredWidth: 16 }
            Text { text: "تحقق من Node.js على هذا الجهاز"; Layout.fillWidth: true; wrapMode: Text.WordWrap
                   font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2 }
            AppButton { text: "فحص Node.js"; kind: "ghost"; onClicked: app.checkNode() }
            Rectangle {
                width: 8; height: 8; radius: 4
                visible: app.nodeStatus !== ""
                color: app.nodeStatus === "missing" ? Theme.colors.red : Theme.colors.green
                Layout.alignment: Qt.AlignVCenter
            }
            Text {
                visible: app.nodeStatus !== ""
                text: app.nodeStatus === "missing" ? "غير مثبّت" : "مثبّت: " + app.nodeStatus
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                color: Theme.colors.ink2
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Text { text: "2"; font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3; Layout.preferredWidth: 16 }
            Text { text: "إن لم يكن مثبّتاً، ثبّته من الموقع الرسمي"; Layout.fillWidth: true; wrapMode: Text.WordWrap
                   font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2 }
            AppButton {
                text: "تثبيت Node.js"; kind: "ghost"
                visible: app.nodeStatus === "missing"
                onClicked: app.installNode()
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Text { text: "3"; font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3; Layout.preferredWidth: 16 }
            Text { text: "ولّد ملف الجسر في مجلد البيانات"; Layout.fillWidth: true; wrapMode: Text.WordWrap
                   font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2 }
            AppButton { text: "توليد ملف الجسر"; kind: "ghost"; onClicked: app.generateWhatsAppBridge() }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Text { text: "4"; font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3; Layout.preferredWidth: 16 }
            Text { text: "اعرض رمز الربط داخل التطبيق وامسحه بواتساب — يصلك تأكيد فور الربط"
                   Layout.fillWidth: true; wrapMode: Text.WordWrap
                   font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2 }
            AppButton {
                text: "عرض رمز الربط"; kind: "accent"
                enabled: !app.waStarting
                onClicked: app.showWhatsAppQr()
            }
        }
        Text { text: "أو يدوياً من مجلد البيانات:  npm install && node whatsapp_bridge.js"
               Layout.fillWidth: true; Layout.leftMargin: 26
               font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.caption; color: Theme.colors.ink3
               LayoutMirroring.enabled: false; horizontalAlignment: Text.AlignLeft }
    }

    // clears the sticky save bar (60px + hairline + air) so the last field never sits flush against it
    Item { Layout.fillWidth: true; Layout.preferredHeight: 72 }

    // ═══════════ sticky save bar (PageFrame footer) ═══════════
    footer: RowLayout {
        width: Math.min(840, parent.width - 96)
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        AppButton {
            text: "حفظ الإعدادات"; kind: "accent"
            enabled: !app.busy
            onClicked: pg.doSave()
        }
        Rectangle {
            width: 8; height: 8; radius: 4
            color: pg.dirty ? Theme.colors.amber : Theme.colors.green
            Layout.alignment: Qt.AlignVCenter
        }
        Text {
            text: app.busy ? "التحليل قيد التشغيل — تعذّر الحفظ الآن"
                           : (pg.dirty ? "تغييرات غير محفوظة" : "كل الإعدادات محفوظة")
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small
            color: Theme.colors.ink2
        }
        Item { Layout.fillWidth: true }
    }
}
