"""Fix round 1, important finding 3: tests/_isolation.py's isolated_state()
never restored api.app.DATA_DIR on the normal path.

api.app is typically imported *during* an isolated_state() block (that is
the whole point of entering the helper before the first import), so at
entry `sys.modules.get("api.app")` found nothing and the original code's
entry-time snapshot was None — the restore in `finally` was gated on that
snapshot being non-None and so was silently skipped. core.paths.DATA_DIR
was correctly restored either way, so api.app.DATA_DIR (and any module
constant derived from it at import time, e.g. api/app.py's _REPORTS_DIR)
permanently diverged from core.paths.DATA_DIR for the rest of the process
— a deleted temp directory. The reviewer confirmed this by running
test_api_auth then test_api_uploads in one process.

This module tests the test infrastructure itself, not application code, so
it does not fit naturally into any of the existing per-feature test files.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ["MARSAD_API_ENABLE"] = "1"

from tests._isolation import isolated_state  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


class IsolationRestoreTests(unittest.TestCase):
    def test_api_app_data_dir_matches_paths_data_dir_after_exit(self):
        """The reviewer's prescribed invariant: whenever api.app is loaded,
        its DATA_DIR must track core.paths.DATA_DIR once an isolated_state()
        block has exited — never left pointing at a deleted temp dir."""
        import core.paths as paths
        real_data_dir = paths.DATA_DIR

        with isolated_state() as root:
            import api.app as api_app
            self.assertEqual(api_app.DATA_DIR, root)

        import api.app as api_app  # already loaded; re-import just binds the name
        self.assertEqual(paths.DATA_DIR, real_data_dir)
        self.assertEqual(api_app.DATA_DIR, paths.DATA_DIR)

    def test_first_import_of_api_app_inside_the_block_still_restores(self):
        """Reproduces the exact bug scenario in a fresh subprocess: api.app
        is not yet imported when isolated_state() is entered — so the
        entry-time sys.modules lookup finds nothing — and is only imported
        *during* the block. This is the case the original code's entry-time
        snapshot (captured before the import could happen) could not see,
        so the restore silently no-op'd."""
        script = (
            "import os\n"
            "os.environ['MARSAD_API_ENABLE'] = '1'\n"
            "from tests._isolation import isolated_state\n"
            "import core.paths as paths\n"
            "real = paths.DATA_DIR\n"
            "with isolated_state():\n"
            "    import api.app as api_app\n"
            "assert api_app.DATA_DIR == paths.DATA_DIR, "
            "(str(api_app.DATA_DIR), str(paths.DATA_DIR))\n"
            "assert paths.DATA_DIR == real, (str(paths.DATA_DIR), str(real))\n"
            "print('OK')\n"
        )
        proc = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
