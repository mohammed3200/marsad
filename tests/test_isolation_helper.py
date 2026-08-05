"""Tests the test infrastructure itself.

`isolated_state()` redirects module-level path globals into a temp dir. The
subtle failure mode: a module that is first imported *during* the block is
invisible to the entry-time `sys.modules` lookup, so the entry-time snapshot
is None — and a restore gated on that snapshot silently no-ops. The module's
globals then stay pinned to a temp directory that has been deleted, for the
rest of the process, while `core.paths.DATA_DIR` is correctly restored. The
two diverge and nothing notices.

That bug shipped once, against the web API's module, and was found only by
running two suites in one process. The API is gone; `backend.controller` has
the identical shape — it computes REPORTS/LATEST_F/SAMPLES_F from DATA_DIR at
import time, and entering the helper before importing it is the normal
pattern. These tests hold that invariant.
"""
import subprocess
import sys
import unittest
from pathlib import Path

from tests._isolation import isolated_state

REPO_ROOT = Path(__file__).resolve().parent.parent


class IsolationRestoreTests(unittest.TestCase):

    def test_controller_paths_track_data_dir_after_exit(self):
        """Whenever backend.controller is loaded, its path globals must track
        core.paths.DATA_DIR once the block has exited — never left pointing at
        a deleted temp dir."""
        import core.paths as paths
        real = paths.DATA_DIR

        with isolated_state() as root:
            import backend.controller as ctrl
            self.assertEqual(ctrl.DATA_DIR, root)
            self.assertEqual(ctrl.REPORTS, root / "reports")

        import backend.controller as ctrl
        self.assertEqual(paths.DATA_DIR, real)
        self.assertEqual(ctrl.DATA_DIR, paths.DATA_DIR)
        self.assertEqual(ctrl.REPORTS, paths.DATA_DIR / "reports")

    def test_first_import_inside_the_block_still_restores(self):
        """The exact bug scenario, in a fresh subprocess: the module is not
        imported when isolated_state() is entered — so the entry-time lookup
        finds nothing — and is imported only during the block."""
        script = (
            "from tests._isolation import isolated_state\n"
            "import core.paths as paths\n"
            "real = paths.DATA_DIR\n"
            "with isolated_state() as root:\n"
            "    import backend.controller as ctrl\n"
            "    assert ctrl.DATA_DIR == root, (str(ctrl.DATA_DIR), str(root))\n"
            "assert paths.DATA_DIR == real, (str(paths.DATA_DIR), str(real))\n"
            "assert ctrl.DATA_DIR == paths.DATA_DIR, "
            "(str(ctrl.DATA_DIR), str(paths.DATA_DIR))\n"
            "assert ctrl.REPORTS == paths.DATA_DIR / 'reports', str(ctrl.REPORTS)\n"
            "print('OK')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
            env={"QT_QPA_PLATFORM": "offscreen", "PATH": "/usr/bin:/bin",
                 "HOME": str(Path.home())})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_the_helper_leaves_no_temp_root_behind(self):
        with isolated_state() as root:
            self.assertTrue(root.exists())
        self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
