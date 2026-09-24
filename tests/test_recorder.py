# -*- coding: utf-8 -*-
"""recorder.py 纯函数单元测试：events_to_steps / drop_altgr_ghosts。"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import kp_test_env  # noqa: E402,F401

import recorder  # noqa: E402


class TestDropAltgrGhosts(unittest.TestCase):
    def test_drops_matching_lctrl(self):
        events = [(1.0, "lctrl", True), (1.003, "ralt", True),
                  (1.1, "ralt", False), (1.101, "lctrl", False)]
        kept = recorder.drop_altgr_ghosts(events)
        self.assertEqual(kept, [(1.003, "ralt", True), (1.1, "ralt", False)])

    def test_keeps_lctrl_without_ralt(self):
        events = [(1.0, "lctrl", True), (1.2, "lctrl", False)]
        self.assertEqual(recorder.drop_altgr_ghosts(events), events)

    def test_keeps_lctrl_far_from_ralt(self):
        # 相隔 100ms 大于 5ms 窗口 -> 不是幽灵，保留
        events = [(1.0, "lctrl", True), (1.1, "ralt", True),
                  (1.2, "ralt", False), (1.3, "lctrl", False)]
        self.assertEqual(len(recorder.drop_altgr_ghosts(events)), 4)


class TestEventsToSteps(unittest.TestCase):
    def test_simple_tap(self):
        steps = recorder.events_to_steps([(0.0, "a", True), (0.09, "a", False)], 0.1)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["key"], "a")
        self.assertEqual(steps[0]["hold_ms"], 90)
        self.assertEqual(steps[0]["delay_ms"], 200)   # 尾延迟

    def test_combo(self):
        events = [(0.0, "ctrl", True), (0.02, "c", True),
                  (0.05, "c", False), (0.06, "ctrl", False)]
        steps = recorder.events_to_steps(events, 0.1)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["key"], "ctrl+c")
        self.assertEqual(steps[0]["hold_ms"], 30)

    def test_modifier_alone(self):
        steps = recorder.events_to_steps([(0.0, "ctrl", True), (0.05, "ctrl", False)], 0.1)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["key"], "ctrl")
        self.assertEqual(steps[0]["hold_ms"], 50)

    def test_delay_is_gap_until_tail(self):
        events = [(0.0, "a", True), (0.05, "a", False),
                  (0.2, "b", True), (0.25, "b", False)]
        steps = recorder.events_to_steps(events, 0.3)
        self.assertEqual([s["key"] for s in steps], ["a", "b"])
        self.assertEqual(steps[0]["delay_ms"], 150)   # 两 tap 间隔
        self.assertEqual(steps[1]["delay_ms"], 200)   # 末尾尾延迟

    def test_open_key_at_stop(self):
        steps = recorder.events_to_steps([(0.0, "a", True)], 0.08)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["hold_ms"], 80)     # 到 stop_time 为止

    def test_altgr_ghost_filtered_in_pipeline(self):
        # 幽灵 lctrl 被剔除后，只剩 ralt 一个动作
        events = [(1.0, "lctrl", True), (1.003, "ralt", True),
                  (1.1, "ralt", False), (1.101, "lctrl", False)]
        steps = recorder.events_to_steps(events, 1.2)
        self.assertEqual([s["key"] for s in steps], ["ralt"])

    def test_empty(self):
        self.assertEqual(recorder.events_to_steps([], 0.0), [])


if __name__ == "__main__":
    unittest.main()
