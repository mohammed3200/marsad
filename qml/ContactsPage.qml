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
    }

    // ── employees ──
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 8
        ReportSection { title: "الموظفون" }
        EmptyState {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            visible: pg.employees.length === 0
            icon: "☷"
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
                                font.family: Theme.fonts.body; font.pixelSize: 14; font.bold: true
                                color: Theme.colors.ink
                            }
                            Text {
                                text: modelData.position || ""
                                visible: !!modelData.position
                                font.family: Theme.fonts.body; font.pixelSize: 12; color: Theme.colors.ink3
                            }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: modelData.email || ""
                                font.family: Theme.fonts.mono; font.pixelSize: 12; color: Theme.colors.ink2
                                LayoutMirroring.enabled: false
                                horizontalAlignment: Text.AlignLeft
                            }
                            Text {
                                text: modelData.whatsapp || ""
                                visible: !!modelData.whatsapp
                                font.family: Theme.fonts.mono; font.pixelSize: 12; color: Theme.colors.ink3
                                LayoutMirroring.enabled: false
                                horizontalAlignment: Text.AlignLeft
                            }
                        }
                        AppButton {
                            text: "حذف"; kind: "ghost"; implicitHeight: 30
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
            Item { Layout.fillWidth: true }
            AppButton {
                text: "إضافة الموظف"; kind: "accent"
                enabled: nameF.text !== ""
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
        }
    }

    // ── sync ──
    RowLayout {
        Layout.fillWidth: true
        AppButton { text: "مزامنة مع الإعدادات"; kind: "ghost"; onClicked: app.syncContacts() }
        Item { Layout.fillWidth: true }
    }
}
