#!/usr/bin/env python3
"""Screenshot harness — render each page of the QML app to PNG (offscreen).

Uses the real AppController, then overrides the dashboard with the demo
result below. Run:  QT_QPA_PLATFORM=offscreen python tools/capture_qt.py [out_dir]

Two things this harness has to get right, both learned from the shots it
produced before:

1. `loadSamples()` raises a toast, and Main.qml's toastTimer runs for 3500 ms.
   Grabbing sooner left «حُمّلت 8 تقارير نموذجية» sitting across the bottom of
   the first pages. We wait it out rather than reaching into the QML.
2. The dashboard renders from `reports/latest.json`, which is gitignored and
   on a dev machine is usually thin placeholder data — leaving the lower half
   of the shot empty. DEMO_CHIEF below is assigned in memory only. Nothing
   here writes to the user's reports/, and the real latest.json is left alone.
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import Qt, QUrl, QTimer, QEventLoop

from core.paths import BUNDLE_DIR
from backend.theme import Theme
from backend.controller import AppController

PAGES = ["input", "analysis", "dashboard", "reports", "settings", "contacts"]

# A realistic chief result for the documentation shots. Same shape as
# _ensure_chief_schema guarantees; the field names match what
# qml/DashboardPage.qml reads (kpis: name/value/status, top_actions:
# action/owner/deadline/impact) and what core/exporters.py consumes.
# The chief output of a REAL analysis — 11/11 agents against a live model
# on 2026-08-05, over the eight field reports in sample_reports.json.
# Captured verbatim so the README shows what the app actually produces
# rather than figures a human invented. Regenerate by re-running an
# analysis and pasting the new chief dict here.
DEMO_CHIEF = {
    "overall_health": "جيد",
    "executive_summary": "تم إنجاز 14 برجاً من أصل 23 (83٪) وتثبيت خوادم MEC في مصراتة 100٪. استهلك المشروع 60٪ من الميزانية مع تجاوز 8٪ بسبب تكاليف الشحن. هناك تأخير حاسم في شحنة Massive MIMO (18 يوماً) وضعف ترددات الباك هول بين سرت والجفرة يتطلب حلًا خلال 3 أيام. المرحلة الثانية متأخرة 18 يوماً والمرحلة الثالثة لم تبدأ، مما يدفع تاريخ الانتهاء إلى سبتمبر 2026. السلامة عامة جيدة (87٪) مع حادثتين بسيطتين. جودة الفحص 80٪ مع محطتين تحتاجان إعادة معايرة. تم تحديد مجموعة من الإجراءات العاجلة لاستعادة الجدول الزمني وتقليل المخاطر.",
    "kpis": [
        {
            "name": "نسبة إكمال المشروع",
            "value": "81٪",
            "trend": "→",
            "status": "جيد"
        },
        {
            "name": "نسبة الإنفاق من الميزانية",
            "value": "60٪",
            "trend": "→",
            "status": "جيد"
        },
        {
            "name": "درجة السلامة",
            "value": "87٪",
            "trend": "→",
            "status": "جيد"
        },
        {
            "name": "معدل نجاح الفحص الجودة",
            "value": "80٪",
            "trend": "→",
            "status": "جيد"
        },
        {
            "name": "مستوى ملء المخازن",
            "value": "72٪",
            "trend": "↓",
            "status": "متوسط"
        }
    ],
    "top_actions": [
        {
            "priority": 1,
            "action": "تسريع التخليص الجمركي لشحنة Massive MIMO أو إيجاد مورد بديل",
            "owner": "م. أحمد الورفلي",
            "deadline": "2026-06-05",
            "impact": "استعادة المسار الحرج وتجنب تأخير إضافي"
        },
        {
            "priority": 2,
            "action": "إجراء مراجعة فورية لترددات الباك هول بين سرت والجفرة وتطبيق تحسينات أو إضافة محطات تعزيز",
            "owner": "م. سالم المشري",
            "deadline": "2026-05-19",
            "impact": "حماية جودة URLLC وتجنب انقطاع الخدمة"
        },
        {
            "priority": 3,
            "action": "تركيب سياج أمان حول برج 17 في سرت وتكثيف تدريب السلامة للمقاولين الفرعيين",
            "owner": "م. يوسف العريبي",
            "deadline": "2026-05-25",
            "impact": "رفع درجة السلامة العامة فوق 90٪"
        },
        {
            "priority": 4,
            "action": "إجراء دراسة جيوتقنية شاملة لموقع الجفرة وتعديل تصميم الأساسات بناءً على النتائج",
            "owner": "م. نور المهدي",
            "deadline": "2026-06-30",
            "impact": "تجنب مشاكل الأساسات المستقبلية"
        },
        {
            "priority": 5,
            "action": "تنفيذ مشروع ألواح طاقة شمسية في الجفرة لتقليل استهلاك الوقود الإضافي",
            "owner": "م. خالد بوزيد",
            "deadline": "2026-08-15",
            "impact": "خفض تكلفة الوقود بنسبة تقديرية 30٪"
        }
    ],
    "dept_scores": [
        {
            "dept": "العمليات",
            "score": 78,
            "status": "جيد",
            "key_issue": "تأخير شحنة Massive MIMO وتأثيرها على المسار الحرج"
        },
        {
            "dept": "الجودة",
            "score": 80,
            "status": "جيد",
            "key_issue": "محطتان في الجفرة بحاجة لإعادة معايرة الهوائيات"
        },
        {
            "dept": "السلامة",
            "score": 87,
            "status": "جيد",
            "key_issue": "حوادث بسيطة وحاجة إلى سياج أمان حول برج 17 في سرت"
        },
        {
            "dept": "الإنشائية",
            "score": 83,
            "status": "جيد",
            "key_issue": "أربعة قواعد معلقة بسبب تصاريح بلدية ومشكلة تربة في الجفرة"
        },
        {
            "dept": "المالية",
            "score": 70,
            "status": "جيد",
            "key_issue": "تجاوز ميزانية المرحلة 2 بنسبة 8٪ بسبب تكاليف الشحن"
        },
        {
            "dept": "المشتريات",
            "score": 62,
            "status": "متوسط",
            "key_issue": "طلب واحد معلق لشحنة MIMO وتأخير الجمارك"
        },
        {
            "dept": "الإمداد",
            "score": 72,
            "status": "متوسط",
            "key_issue": "مخزون مصراتة 72٪ وشحنة MIMO عالقة"
        },
        {
            "dept": "المخاطر",
            "score": 68,
            "status": "متوسط",
            "key_issue": "عدد كبير من المخاطر عالية المستوى (MIMO، الباك هول، الميزانية)"
        },
        {
            "dept": "الجدول الزمني",
            "score": 55,
            "status": "ضعيف",
            "key_issue": "تأخير 27 يوماً وإعادة جدولة المرحلة 3 إلى سبتمبر 2026"
        }
    ],
    "achievements": [
        "تركيب 14 برجاً من أصل 23 في منطقة سرت",
        "إكمال تثبيت خوادم MEC في مصراتة 100٪",
        "فحص 10 محطات وفق 3GPP Release 16، 8 محطات اجتازت",
        "إكمال الحفر والصب لـ 19 قاعدة من أصل 23",
        "عدم تسجيل أي حوادث سلامة كبيرة خلال شهر مايو"
    ]
}


def load_fonts():
    for ttf in sorted((BASE / "assets" / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QGuiApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    load_fonts()

    theme, controller = Theme(), AppController()

    # Swap in the SHIPPED defaults BEFORE Main.qml loads. SettingsPage fills
    # its fields with `Component.onCompleted: text = ...`, which runs once at
    # construction — overriding after setSource() leaves the old values on
    # screen and marks the form dirty. Without this the README leaked the
    # developer's own environment: the Ollama model name and server URL they
    # happened to have configured. Read-only; settings.json is never written.
    example = BUNDLE_DIR / "settings.example.json"
    if example.exists():
        with open(example, encoding="utf-8") as fh:
            controller._settings = json.load(fh)

    # The Reports page lists the real reports/ dir, which put the developer's
    # own export filenames and timestamps in the README. Show it as a fresh
    # install would: nothing exported yet.
    controller._exports = []
    view = QQuickView()
    view.rootContext().setContextProperty("Theme", theme)
    view.rootContext().setContextProperty("app", controller)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setColor(Qt.GlobalColor.white)
    view.resize(1280, 820)
    view.setSource(QUrl.fromLocalFile(str(BASE / "qml" / "Main.qml")))
    if view.status() == QQuickView.Status.Error:
        for e in view.errors():
            print("QML ERROR:", e.toString(), file=sys.stderr)
        return 1
    view.show()

    def settle(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    settle(600)
    controller.loadSamples()   # populate the Input list for the gallery

    # In-memory only — never written to the user's reports/. _dash is what
    # DashboardPage binds to; _results is what the Reports page and the
    # exporters read, so both stay consistent.
    controller._results = {"chief": DEMO_CHIEF}
    controller._dash = DEMO_CHIEF
    controller._date = "2026-08-04 09:30"
    controller.dashModelChanged.emit()
    controller.reportDateChanged.emit()

    # Outlast Main.qml's toastTimer (interval 3500) so loadSamples()'s
    # «حُمّلت 8 تقارير نموذجية» is gone before the first grab.
    settle(3800)
    root = view.rootObject()
    for i, name in enumerate(PAGES):
        root.setProperty("currentIndex", i)
        settle(500)
        img = view.grabWindow()
        path = out_dir / f"{i}-{name}.png"
        img.save(str(path))
        print("saved", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
