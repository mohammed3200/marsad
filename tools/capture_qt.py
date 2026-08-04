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
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import Qt, QUrl, QTimer, QEventLoop

from backend.theme import Theme
from backend.controller import AppController

PAGES = ["input", "analysis", "dashboard", "reports", "settings", "contacts"]

# A realistic chief result for the documentation shots. Same shape as
# _ensure_chief_schema guarantees; the field names match what
# qml/DashboardPage.qml reads (kpis: name/value/status, top_actions:
# action/owner/deadline/impact) and what core/exporters.py consumes.
DEMO_CHIEF = {
    "overall_health": "متوسط",
    "executive_summary": (
        "يسير مشروع توسعة الجيل الرابع والخامس ضمن الحدود المقبولة مع تأخر "
        "ملموس في مسار الأعمال الإنشائية. أُنجزت ١٤ موقعاً من أصل ٢٠ في "
        "المنطقة الشمالية، ويتركّز الخطر الحالي في تأخر توريد أبراج الشد "
        "وفي ازدحام تصاريح الحفر لدى البلديات. التكاليف ضمن الاعتماد المرصود "
        "بفارق طفيف، ويوصى بإعادة جدولة المواقع الستة المتبقية على دفعتين "
        "لتفادي تعطّل فرق التركيب."
    ),
    "kpis": [
        {"name": "المواقع المُسلَّمة",      "value": "14/20",  "status": "متوسط"},
        {"name": "الالتزام بالجدول الزمني", "value": "78%",    "status": "متأخر"},
        {"name": "انحراف التكلفة",          "value": "+4.2%",  "status": "متوسط"},
        {"name": "بلاغات السلامة",          "value": "0",      "status": "آمن"},
        {"name": "جاهزية شبكة النواة",      "value": "92%",    "status": "جيد"},
        {"name": "طلبات التوريد المعلّقة",   "value": "7",      "status": "تحذير"},
    ],
    "top_actions": [
        {"action": "تصعيد طلب تصاريح الحفر للمواقع الستة المتبقية إلى البلدية",
         "owner": "إدارة العقود", "deadline": "خلال ٥ أيام", "impact": "يفكّ اختناق التركيب"},
        {"action": "تثبيت موعد توريد أبراج الشد مع المورّد البديل",
         "owner": "المشتريات", "deadline": "خلال أسبوع", "impact": "يقلّص التأخر بأسبوعين"},
        {"action": "إعادة جدولة المواقع المتبقية على دفعتين",
         "owner": "مكتب إدارة المشاريع", "deadline": "قبل نهاية الشهر", "impact": "يمنع تعطّل الفرق"},
        {"action": "مراجعة انحراف التكلفة في بند الأعمال المدنية",
         "owner": "التكاليف", "deadline": "الأسبوع القادم", "impact": "يحمي هامش الاعتماد"},
    ],
    "dept_scores": [
        {"dept": "شبكة الراديو RAN", "score": 88, "note": "ضمن المستهدف"},
        {"dept": "شبكة النواة Core", "score": 92, "note": "جاهزية عالية"},
        {"dept": "الأعمال الإنشائية", "score": 64, "note": "تأخر في ستة مواقع"},
        {"dept": "المشتريات",        "score": 71, "note": "طلبات توريد معلّقة"},
        {"dept": "السلامة",          "score": 96, "note": "لا بلاغات"},
    ],
    "achievements": [
        "تشغيل أربعة مواقع جيل خامس في المنطقة الوسطى قبل الموعد بأسبوع",
        "إغلاق جميع ملاحظات تدقيق السلامة للربع الماضي",
        "خفض زمن تركيب الهوائي إلى ١٫٥ يوم للموقع الواحد",
    ],
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
