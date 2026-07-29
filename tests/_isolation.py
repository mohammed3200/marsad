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

    saved = (sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS)

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

        if ctrl:
            ctrl.REPORTS = root / "reports"
            ctrl.SAMPLES_F = root / "sample_reports.json"
            ctrl.LATEST_F = root / "reports" / "latest.json"

        try:
            yield root
        finally:
            sb.SETTINGS_F, sb.EXAMPLE_F, eng.REPORTS = saved
            if ctrl_saved:
                ctrl.REPORTS, ctrl.SAMPLES_F, ctrl.LATEST_F = ctrl_saved
