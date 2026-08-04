import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

PageFrame {
    id: pg
    title: "جهات الاتصال"
    subtitle: "الهيكل التنظيمي والموظفون — يزامَن مع خرائط التوجيه في الإعدادات"

    property var structure: app.contactsStructure()
    property var employees: []
    readonly property var deptOptions: structure ? Object.keys(structure) : []
    property var subOptions: []

    function currentDept() { return deptC.value }
    function currentSub()  { return subC.value }

    function refreshSubs() {
        var d = deptC.value
        subOptions = (structure && structure[d] && structure[d].subs)
                     ? Object.keys(structure[d].subs) : []
    }
    function refreshEmployees() {
        employees = app.employeesFor(deptC.value, subC.value) || []
    }

    Component.onCompleted: { refreshSubs(); refreshEmployees() }

    // ── org selector ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 14
        ReportSection { title: "الهيكل التنظيمي" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            FormCombo {
                id: deptC; label: "الإدارة"; options: pg.deptOptions
                onValueChanged: { pg.refreshSubs(); subC.currentIndex = 0; pg.refreshEmployees() }
            }
            FormCombo {
                id: subC; label: "القسم"; options: pg.subOptions
                onValueChanged: pg.refreshEmployees()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            AppButton { text: "مزامنة مع الإعدادات"; kind: "ghost"; onClicked: app.syncContacts() }
            Text {
                // بلا أسهم: الخطوط المرفقة لا تحوي U+2190، فتظهر مربعاً فارغاً
                text: "ينسخ توجيه البريد وواتساب إلى الأقسام، ويحفظه في الإعدادات"
                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.caption
                color: Theme.colors.ink3
            }
            Item { Layout.fillWidth: true }
        }
    }

    // ── employees ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 8
        ReportSection { title: "الموظفون" }
        EmptyState {
            Layout.fillWidth: true
            Layout.preferredHeight: 170
            visible: pg.employees.length === 0
            message: "لا يوجد موظفون في هذا القسم"
            hint: "أضف موظفاً من النموذج بالأسفل"
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: pg.employees
                delegate: ListRow {
                    last: index === pg.employees.length - 1
                    RowLayout {
                        anchors.fill: parent
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.name || "—"
                                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.body; font.bold: true
                                color: Theme.colors.ink
                                Layout.fillWidth: true; elide: Text.ElideLeft
                            }
                            Text {
                                text: modelData.position || ""
                                visible: !!modelData.position
                                font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3
                                Layout.fillWidth: true; elide: Text.ElideLeft
                            }
                        }
                        ColumnLayout {
                            spacing: 2
                            Layout.maximumWidth: 260
                            Text {
                                text: modelData.email || ""
                                font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink2
                                LayoutMirroring.enabled: false
                                horizontalAlignment: Text.AlignLeft
                                Layout.fillWidth: true; elide: Text.ElideLeft
                            }
                            Text {
                                text: modelData.whatsapp || ""
                                visible: !!modelData.whatsapp
                                font.family: Theme.fonts.mono; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3
                                LayoutMirroring.enabled: false
                                horizontalAlignment: Text.AlignLeft
                                Layout.fillWidth: true; elide: Text.ElideLeft
                            }
                        }
                        AppButton {
                            text: "حذف"; kind: "danger"; implicitHeight: 30
                            onClicked: { app.deleteEmployee(modelData.id); pg.refreshEmployees() }
                        }
                    }
                }
            }
        }
    }

    // ── add employee ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 12
        ReportSection { title: "إضافة موظف" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            FormField { id: nameF; label: "الاسم"; placeholder: "الاسم الكامل" }
            FormField { id: posF;  label: "المنصب"; placeholder: "المسمّى الوظيفي" }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            FormField { id: emailF; label: "البريد الإلكتروني"; ltr: true; placeholder: "name@example.com" }
            FormField { id: waF;    label: "واتساب"; ltr: true; placeholder: "+1000000000" }
        }
        RowLayout {
            Layout.fillWidth: true
            AppButton {
                text: "إضافة الموظف"; kind: "accent"
                enabled: nameF.text !== "" && pg.deptOptions.length > 0
                onClicked: {
                    app.addEmployee({
                        "name": nameF.text, "position": posF.text,
                        "dept": pg.currentDept(), "sub_dept": pg.currentSub(),
                        "email": emailF.text, "whatsapp": waF.text, "active": true
                    })
                    nameF.text = ""; posF.text = ""; emailF.text = ""; waF.text = ""
                    pg.refreshEmployees()
                }
            }
            Item { Layout.fillWidth: true }
        }
        Text {
            text: "لا توجد إدارات في الهيكل التنظيمي بعد — أضِف إدارة أولاً لتتمكن من إضافة موظف"
            visible: pg.deptOptions.length === 0
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            font.family: Theme.fonts.body; font.pixelSize: Theme.fs.small; color: Theme.colors.ink3
        }
    }
}
