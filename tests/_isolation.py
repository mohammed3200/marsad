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

    saved = (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS, contacts.CONTACTS_FILE,
             svc.REPORTS, svc.SAMPLES_F, svc.LATEST_F)

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

        if ctrl:
            ctrl.REPORTS = root / "reports"
            ctrl.SAMPLES_F = root / "sample_reports.json"
            ctrl.LATEST_F = root / "reports" / "latest.json"

        try:
            yield root
        finally:
            (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS, contacts.CONTACTS_FILE,
             svc.REPORTS, svc.SAMPLES_F, svc.LATEST_F) = saved
            if ctrl_saved:
                ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F = ctrl_saved
