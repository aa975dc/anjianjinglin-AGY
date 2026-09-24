# -*- coding: utf-8 -*-
"""profiles.py 单元测试：normalize_step / normalize_config / validate_run_config。"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import kp_test_env  # noqa: E402,F401

import engine     # noqa: E402
import i18n       # noqa: E402
import profiles   # noqa: E402


class TestNormalizeStep(unittest.TestCase):
    def test_clamps_hold(self):
        # N2 契约：hold 上限统一为 profiles.HOLD_MS_RANGE[1]（=60000）
        step = profiles.normalize_step({"key": "space", "hold_ms": 999999999})
        self.assertEqual(step["hold_ms"], profiles.HOLD_MS_RANGE[1])
        self.assertEqual(step["hold_ms"], 60_000)

    def test_drops_bad_key(self):
        self.assertIsNone(profiles.normalize_step({"key": ""}))
        self.assertIsNone(profiles.normalize_step("not-a-dict"))
        self.assertIsNone(profiles.normalize_step({"key": "!!!bad"}))

    def test_action_fallback(self):
        step = profiles.normalize_step({"key": "a", "action": "weird"})
        self.assertEqual(step["action"], "tap")

    def test_defaults(self):
        step = profiles.normalize_step({"key": "a"})
        self.assertEqual(step["hold_ms"], 90)
        self.assertEqual(step["delay_ms"], 100)
        self.assertTrue(step["enabled"])


class TestNormalizeConfig(unittest.TestCase):
    def test_bad_language_falls_back(self):
        cfg = profiles.normalize_config({"language": "xx"})
        self.assertEqual(cfg["language"], i18n.DEFAULT_LANGUAGE)

    def test_clamps_numbers(self):
        cfg = profiles.normalize_config(
            {"cycles": 10 ** 9, "jitter_pct": 500, "start_delay_ms": 10 ** 9})
        self.assertEqual(cfg["cycles"], 1_000_000)
        self.assertEqual(cfg["jitter_pct"], 90)
        self.assertEqual(cfg["start_delay_ms"], 60_000)

    def test_bad_hotkey_falls_back(self):
        cfg = profiles.normalize_config({"hotkeys": {"pause": "!!!bad"}})
        self.assertEqual(cfg["hotkeys"]["pause"], "f2")

    def test_bad_mode_falls_back(self):
        cfg = profiles.normalize_config({"mode": "nonsense"})
        self.assertEqual(cfg["mode"], engine.MODE_FOREGROUND)

    def test_steps_filtered(self):
        cfg = profiles.normalize_config({"steps": [{"key": "a"}, {"key": ""}, "x"]})
        self.assertEqual(len(cfg["steps"]), 1)

    def test_non_dict(self):
        cfg = profiles.normalize_config(None)
        self.assertEqual(cfg["steps"], [])

    def test_default_hotkeys_has_minimize(self):
        self.assertEqual(profiles.DEFAULT_HOTKEYS.get("minimize"), "f4")


class TestValidateRunConfig(unittest.TestCase):
    def test_clamps_out_of_range(self):
        cfg = engine.RunConfig(
            steps=[{"key": "space", "hold_ms": 999999999, "delay_ms": -5}],
            cycles=-1, cycle_delay_ms=-100, jitter_pct=1000, start_delay_ms=99999999)
        fixed, notes = profiles.validate_run_config(cfg)
        self.assertEqual(fixed.steps[0]["hold_ms"], 60_000)
        self.assertEqual(fixed.steps[0]["delay_ms"], 0)
        self.assertEqual(fixed.cycles, 0)
        self.assertEqual(fixed.cycle_delay_ms, 0)
        self.assertEqual(fixed.jitter_pct, 90)
        self.assertEqual(fixed.start_delay_ms, 60_000)
        self.assertTrue(notes)                       # 有修正必须报告

    def test_valid_range_untouched(self):
        cfg = engine.RunConfig(
            steps=[{"key": "space", "hold_ms": 60_000, "delay_ms": 3_600_000}],
            cycles=1_000_000, jitter_pct=90, start_delay_ms=60_000)
        fixed, notes = profiles.validate_run_config(cfg)
        self.assertEqual(notes, [])
        self.assertEqual(fixed.steps[0]["hold_ms"], 60_000)

    def test_nonnumeric_uses_low_bound(self):
        cfg = engine.RunConfig(steps=[{"key": "space", "hold_ms": "abc"}])
        fixed, notes = profiles.validate_run_config(cfg)
        self.assertEqual(fixed.steps[0]["hold_ms"], 1)
        self.assertTrue(notes)

    def test_mode_and_target_preserved(self):
        cfg = engine.RunConfig(mode=engine.MODE_POST, target_title="X",
                               target_hwnd=123, steps=[{"key": "a"}])
        fixed, _ = profiles.validate_run_config(cfg)
        self.assertEqual(fixed.mode, engine.MODE_POST)
        self.assertEqual(fixed.target_title, "X")
        self.assertEqual(fixed.target_hwnd, 123)

    def test_hold_range_consistent_across_layers(self):
        """N2：normalize_step(加载) / validate_run_config(运行) / UI 上限 三处口径一致。"""
        raw = {"key": "space", "action": "tap", "hold_ms": 500_000}
        norm = profiles.normalize_step(dict(raw))["hold_ms"]
        fixed, _ = profiles.validate_run_config(
            engine.RunConfig(steps=[dict(raw)], start_delay_ms=0))
        val = fixed.steps[0]["hold_ms"]
        ui_hi = profiles.HOLD_MS_RANGE[1]
        self.assertEqual(norm, val)
        self.assertEqual(val, ui_hi)
        self.assertEqual(ui_hi, 60_000)


if __name__ == "__main__":
    unittest.main()
