import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asfi_monitor_app.application.instance_lock import InstanceLock
from asfi_monitor_app.application.runner import run_once_guarded
from asfi_monitor_app.storage import api as reportes_db
from asfi_monitor_app.storage.connection import configure_playwright_browser_path
from asfi_monitor_app.storage.state import cargar_estado, guardar_estado


class RuntimeTests(unittest.TestCase):
    def test_instance_lock_allows_only_one_owner(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "monitor.lock"
            first = InstanceLock(path)
            second = InstanceLock(path)
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()
            self.assertTrue(second.acquire())
            second.release()

    def test_state_write_is_readable_after_atomic_replace(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            guardar_estado(path, {"alertas_enviadas": {"x": {"estado": "ERROR"}}})
            self.assertEqual(cargar_estado(path)["alertas_enviadas"]["x"]["estado"], "ERROR")
            self.assertFalse(list(Path(directory).glob("*.tmp")))

    def test_frozen_paths_use_local_app_data_and_bundled_resources(self):
        with TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}, clear=False), patch.object(
                sys, "frozen", True, create=True
            ), patch.object(sys, "_MEIPASS", directory, create=True):
                self.assertEqual(
                    reportes_db.resolve_data_path("asfi_monitor.db"),
                    Path(directory) / "ASFI Monitor" / "asfi_monitor.db",
                )
                self.assertEqual(
                    reportes_db.resolve_resource_path("reportes_seed.json"),
                    Path(directory) / "reportes_seed.json",
                )

    def test_guarded_review_reports_success(self):
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"ASFI_MONITOR_DATA_DIR": directory}, clear=False
        ), patch(
            "asfi_monitor_app.application.runner.service.ejecutar_revision"
        ) as review:
            self.assertTrue(run_once_guarded())
            review.assert_called_once_with()

    def test_frozen_install_migrates_legacy_database_once(self):
        with TemporaryDirectory() as directory:
            legacy = Path(directory) / "legacy"
            target = Path(directory) / "profile"
            legacy.mkdir()
            target.mkdir()
            legacy_db = legacy / "asfi_monitor.db"
            reportes_db.initialize_database(legacy_db, Path(__file__).parents[1] / "reportes_seed.json")
            with patch.dict(
                os.environ, {"ASFI_MONITOR_DATA_DIR": str(target)}, clear=False
            ), patch.object(sys, "frozen", True, create=True):
                copied = reportes_db.migrate_legacy_data([legacy])
                self.assertIn(target / "asfi_monitor.db", copied)
                self.assertTrue((target / "asfi_monitor.db").exists())

    def test_frozen_browser_path_skips_empty_executable_folder(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "agent"
            shared = root / "ms-playwright" / "chromium_headless_shell-1234" / "chrome-headless-shell-win64"
            agent_browser = agent / "ms-playwright"
            agent_browser.mkdir(parents=True)
            shared.mkdir(parents=True)
            (shared / "chrome-headless-shell.exe").write_bytes(b"")
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
                with patch.object(sys, "frozen", True, create=True), patch.object(
                    sys, "_MEIPASS", str(agent / "_internal"), create=True
                ), patch.object(sys, "executable", str(agent / "ASFI_Monitor_Agent.exe")):
                    selected = configure_playwright_browser_path()
            self.assertEqual(Path(selected).resolve(), (root / "ms-playwright").resolve())


if __name__ == "__main__":
    unittest.main()
