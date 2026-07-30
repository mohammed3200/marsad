"""Redirect all writable-state module globals into a temp dir for the duration
of a test. Nothing in tests/ may ever touch the user's real settings.json,
reports/ or data/."""
import contextlib
import sys
import tempfile
from pathlib import Path


@contextlib.contextmanager
def isolated_state():
    import backend.settings_bridge as sb
    import core.engine as eng
    import core.contacts as contacts
    # Qt-free (api/services.py mirrors backend/controller.py without PySide6),
    # so — unlike backend.controller below — it's safe to import unconditionally.
    # It must be imported *before* api.app's module-level `service = AppService()`
    # runs, or the patch below would have nothing to redirect.
    import api.services as svc
    import core.paths as paths

    saved = (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS, contacts.CONTACTS_FILE,
             svc.REPORTS, svc.SAMPLES_F, svc.LATEST_F, paths.DATA_DIR)

    # api/app.py does `from core.paths import DATA_DIR` at import time and uses
    # it to place uploads. Because this helper is entered *before* api.app is
    # first imported, redirecting the name on core.paths is what makes api.app
    # bind the temp path when it does import. Modules that already imported
    # DATA_DIR keep their own binding, which is why each is patched by name
    # above.
    api_app = sys.modules.get("api.app")
    api_app_saved = api_app.DATA_DIR if api_app else None

    # Also redirect backend.controller path globals if it's already imported
    ctrl = sys.modules.get("backend.controller")
    ctrl_saved = None
    if ctrl:
        ctrl_saved = (ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "reports").mkdir()
        sb.SETTINGS_F = root / "settings.json"
        sb.EXAMPLE_F = root / "settings.example.json"   # deliberately absent
        eng.REPORTS = root / "reports"
        contacts.CONTACTS_FILE = root / "data" / "contacts.json"
        svc.REPORTS = root / "reports"
        svc.SAMPLES_F = root / "sample_reports.json"     # deliberately absent
        svc.LATEST_F = root / "reports" / "latest.json"
        paths.DATA_DIR = root
        if api_app:
            api_app.DATA_DIR = root

        if ctrl:
            ctrl.REPORTS = root / "reports"
            ctrl.SAMPLES_F = root / "sample_reports.json"
            ctrl.LATEST_F = root / "reports" / "latest.json"

        try:
            yield root
        finally:
            (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS, contacts.CONTACTS_FILE,
             svc.REPORTS, svc.SAMPLES_F, svc.LATEST_F, paths.DATA_DIR) = saved
            if api_app_saved is not None:
                api_app.DATA_DIR = api_app_saved
            if ctrl_saved:
                ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F = ctrl_saved
