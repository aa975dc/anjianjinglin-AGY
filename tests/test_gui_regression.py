# -*- coding: utf-8 -*-
"""关键回归（GUI 层）：
  * test_poll_survives_handler_exception
  * test_collect_clamps_hold
  * test_target_preserved_when_not_running
  * test_launch_target_keeps_mode
配置全部落在临时 APPDATA（见 kp_test_env）。
"""
import json
import os
import sys
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import kp_test_env  # noqa: E402,F401

try:
    import tkinter as tk
    _probe = tk.Tk()
    _probe.withdraw()
    _probe.destroy()
    TK_OK = True
except Exception:                       # noqa: BLE001
    TK_OK = False

import gui_simple     # noqa: E402
import instance       # noqa: E402


def _pump(win, seconds):
    end = time.time() + seconds
    while time.time() < end:
        try:
            win.update()
        except tk.TclError:
            return
        time.sleep(0.02)


@unittest.skipUnless(TK_OK, "无可用 Tk 显示环境")
class TestGuiRegressions(unittest.TestCase):
    def _new_app(self):
        app = gui_simple.SimpleApp()
        app.withdraw()
        app._elevation_hwnd = lambda: 0
        app._check_elevation = lambda: True
        return app

    def tearDown(self):
        time.sleep(0.2)

    def test_poll_survives_handler_exception(self):
        """A1：某条 handler 抛非 Empty 异常后，轮询必须继续消费队列。"""
        app = self._new_app()
        try:
            consumed = []
            real = app._handle_message

            def fake(kind, payload):
                if payload == "BOOM":
                    raise RuntimeError("注入的 handler 异常")
                consumed.append(payload)
                real(kind, payload)

            app._handle_message = fake
            app.q.put(("log", "BOOM"))
            app.q.put(("log", "SENTINEL"))
            _pump(app, 0.6)
            self.assertIn("SENTINEL", consumed)
            self.assertIsNotNone(app._poll_id)
        finally:
            app.on_close()

    def test_collect_clamps_hold(self):
        """A2：简洁版 _collect 必须走 validate_run_config 钳制 hold。"""
        app = self._new_app()
        try:
            app.var_hold.set("999999999")
            app.var_delay.set("0")
            cfg = app._collect()
            self.assertIsNotNone(cfg)
            self.assertLessEqual(cfg.steps[0]["hold_ms"], 60000)
            self.assertGreaterEqual(cfg.steps[0]["hold_ms"], 1)
        finally:
            app.on_close()

    def test_target_preserved_when_not_running(self):
        """C1：目标程序未运行时，设置不能被静默重置写空。"""
        sf = gui_simple.SETTINGS_FILE
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps(
            {"key": "space", "hold_ms": "90", "delay_ms": "1000",
             "cycles": 0, "target": "记事本__不存在__"}, ensure_ascii=False),
            encoding="utf-8")
        app = self._new_app()
        try:
            app._save_settings_now()
            data = json.loads(sf.read_text(encoding="utf-8"))
            self.assertEqual(data.get("target"), "记事本__不存在__")
        finally:
            app.on_close()


class TestLaunchTargetMode(unittest.TestCase):
    def test_launch_target_keeps_mode(self):
        old = sys.argv
        try:
            sys.argv = ["main.py", "mini"]
            _, p_mini = instance._launch_target()
            sys.argv = ["main.py", "full"]
            _, p_full = instance._launch_target()
            sys.argv = ["main.py"]
            _, p_simple = instance._launch_target()
            sys.argv = ["main.py", "MINI"]
            _, p_upper = instance._launch_target()
            sys.argv = ["main.py", "--foo"]
            _, p_junk = instance._launch_target()
        finally:
            sys.argv = old
        self.assertIn("mini", p_mini.split())
        self.assertIn("full", p_full.split())
        self.assertNotIn("mini", p_simple.split())
        self.assertNotIn("full", p_simple.split())
        self.assertIn("mini", p_upper.split())          # 大小写不敏感
        self.assertNotIn("--foo", p_junk.split())       # 无关键参数不透传


if __name__ == "__main__":
    unittest.main()
