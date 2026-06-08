"""
Tests for the effective-data-mode fallback logic introduced in src/config.py.

These tests verify that:
  - PIERWATCH_DATA_MODE=demo always yields DATA_MODE="demo".
  - When the private workbook is absent AND local mode is requested,
    DATA_MODE falls back to "demo" and DEMO_FALLBACK is True.
  - is_data_available() returns True in the public/demo environment.
  - No FileNotFoundError is raised for the missing private workbook in demo mode.
"""
import importlib
import os
import unittest


def _with_env(env_value, fn):
    """
    Run fn(cfg_module) with PIERWATCH_DATA_MODE set to env_value, then restore.
    Captures the return value of fn() before restoring env + reloading module,
    so callers see the values from the temporary mode, not the restored state.
    """
    import src.config as cfg_mod
    old = os.environ.get("PIERWATCH_DATA_MODE")
    try:
        if env_value is None:
            os.environ.pop("PIERWATCH_DATA_MODE", None)
        else:
            os.environ["PIERWATCH_DATA_MODE"] = env_value
        importlib.reload(cfg_mod)
        result = fn(cfg_mod)          # capture before finally restores
    finally:
        if old is None:
            os.environ.pop("PIERWATCH_DATA_MODE", None)
        else:
            os.environ["PIERWATCH_DATA_MODE"] = old
        importlib.reload(cfg_mod)     # restore module to original env state
    return result


class TestEffectiveDataMode(unittest.TestCase):

    def test_demo_env_forces_demo_mode(self):
        """PIERWATCH_DATA_MODE=demo → DATA_MODE='demo', DEMO_FALLBACK=False."""
        mode, fallback = _with_env("demo", lambda c: (c.DATA_MODE, c.DEMO_FALLBACK))
        self.assertEqual(mode, "demo")
        self.assertFalse(fallback,
                         "DEMO_FALLBACK must be False when demo was explicitly requested")

    def test_fallback_to_demo_when_workbook_absent(self):
        """local mode + absent workbook → DATA_MODE='demo', DEMO_FALLBACK=True."""
        import src.config as cfg
        if cfg.PRIVATE_WORKBOOK_AVAILABLE:
            self.skipTest("Private workbook present — fallback path not active here")
        # Force PIERWATCH_DATA_MODE=local to exercise the fallback logic
        mode, fallback, avail = _with_env(
            "local",
            lambda c: (c.DATA_MODE, c.DEMO_FALLBACK, c.PRIVATE_WORKBOOK_AVAILABLE),
        )
        self.assertFalse(avail, "Workbook should still be absent during this test")
        self.assertEqual(mode, "demo",
                         "DATA_MODE must fall back to 'demo' when workbook is absent")
        self.assertTrue(fallback,
                        "DEMO_FALLBACK must be True when fallback occurred")

    def test_is_data_available_true_in_public_repo(self):
        """In the public repo (no workbook), is_data_available() returns True via demo CSVs."""
        import src.config as cfg
        if cfg.PRIVATE_WORKBOOK_AVAILABLE:
            self.skipTest("Private workbook present — this test targets demo-only env")
        import src.data_sources as ds
        self.assertTrue(ds.is_data_available(),
                        "Demo CSVs must be present and is_data_available() must return True")

    def test_no_file_not_found_in_demo_mode(self):
        """Loading demo data must not raise FileNotFoundError when workbook is absent."""
        import src.config as cfg
        if cfg.PRIVATE_WORKBOOK_AVAILABLE:
            self.skipTest("Private workbook present — this test targets demo-only env")
        try:
            from src.demo_data_loader import (
                load_demo_river_stage,
                load_demo_gps_data,
                load_all_demo_primary_device_data,
            )
            load_demo_river_stage()
            load_demo_gps_data()
            load_all_demo_primary_device_data()
        except FileNotFoundError as exc:
            self.fail(f"Demo loaders raised FileNotFoundError: {exc}")

    def test_local_mode_preserved_when_workbook_present(self):
        """When the workbook exists and local is requested, DATA_MODE stays 'local'."""
        import src.config as cfg
        if not cfg.PRIVATE_WORKBOOK_AVAILABLE:
            self.skipTest("Private workbook absent — local-mode test not applicable")
        mode, fallback = _with_env("local", lambda c: (c.DATA_MODE, c.DEMO_FALLBACK))
        self.assertEqual(mode, "local")
        self.assertFalse(fallback)
