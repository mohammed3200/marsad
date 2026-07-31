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
    # DATA_DIR keep their own binding, which is why it's patched by name below
    # too — both on entry (if already imported) and on exit (re-fetched fresh,
    # since api.app is commonly imported *during* the block, after this
    # function's own entry-time lookup already ran and found nothing).
    api_app = sys.modules.get("api.app")

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
        if api_app is not None:
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
            # Re-fetch rather than trust the entry-time reference: api.app is
            # commonly imported *during* the block (that is the whole point
            # of entering this helper before the first import), so at entry
            # sys.modules had no "api.app" yet and there was nothing to save
            # from it. Always re-point it at the just-restored paths.DATA_DIR
            # — not at whatever api.app.DATA_DIR held before entry, which for
            # a module imported inside the block is itself the temp root we
            # are tearing down — or api.app.DATA_DIR is left stuck on a
            # deleted temp directory for the rest of the process.
            api_app = sys.modules.get("api.app")
            if api_app is not None:
                api_app.DATA_DIR = paths.DATA_DIR
            if ctrl_saved:
                ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F = ctrl_saved
