"""Redirect all writable-state module globals into a temp dir for the duration
of a test. Nothing in tests/ may ever touch the user's real settings.json,
reports/ or data/.

This guard exists because it once failed: an early version of tools/test_api.py
ran against the real DATA_DIR and destroyed reports/latest.json, which was only
noticed by a checksum manifest. Every test that touches state goes through here.
"""
import contextlib
import sys
import tempfile
from pathlib import Path


@contextlib.contextmanager
def isolated_state():
    import backend.settings_bridge as sb
    import core.engine as eng
    import core.contacts as contacts
    import core.paths as paths

    saved = (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS, contacts.CONTACTS_FILE,
             paths.DATA_DIR)

    # backend.controller reads its path globals at import time, so redirect
    # them by name too — but only if it is already imported. Importing it here
    # would pull in Qt for tests that do not need it.
    ctrl = sys.modules.get("backend.controller")
    ctrl_saved = None
    if ctrl:
        ctrl_saved = (ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F, ctrl.DATA_DIR)

    def _rebind_controller(root):
        """Point backend.controller's import-time path globals at `root`.

        Called on entry AND on exit, re-fetching from sys.modules each time.
        A module first imported *during* the block is invisible to the
        entry-time lookup above — and that is the common case, since entering
        the helper before the first import is the whole point. Without the
        exit-time re-fetch its globals stay pinned to a temp directory that no
        longer exists, for the rest of the process. That exact bug shipped
        once against the web API's module and was caught by a reviewer running
        two suites in one process.
        """
        mod = sys.modules.get("backend.controller")
        if mod is None:
            return
        mod.DATA_DIR = root
        mod.REPORTS = root / "reports"
        mod.SAMPLES_F = root / "sample_reports.json"    # deliberately absent
        mod.LATEST_F = root / "reports" / "latest.json"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "reports").mkdir()
        sb.SETTINGS_F = root / "settings.json"
        sb.EXAMPLE_F = root / "settings.example.json"   # deliberately absent
        eng.REPORTS = root / "reports"
        contacts.CONTACTS_FILE = root / "data" / "contacts.json"
        paths.DATA_DIR = root

        _rebind_controller(root)

        try:
            yield root
        finally:
            (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS, contacts.CONTACTS_FILE,
             paths.DATA_DIR) = saved
            if ctrl_saved:
                ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F, ctrl.DATA_DIR = ctrl_saved
            else:
                # Imported during the block: restore it to the real paths
                # rather than leaving it on the temp root we are deleting.
                _rebind_controller(paths.DATA_DIR)
