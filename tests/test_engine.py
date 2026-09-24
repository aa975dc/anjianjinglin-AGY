# -*- coding: utf-8 -*-
"""engine.py 时序 / 可中断按住 / force_release 单元测试。

绝不真发按键：用打桩 sender 或把 sender._send 换成记录器。
"""
import os
import sys
import threading
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import kp_test_env  # noqa: E402,F401

import engine     # noqa: E402
import sender     # noqa: E402


class _StubSender:
    MOD_GAP_S = sender.MOD_GAP_S

    def __init__(self):
        self.calls = []

    def key_down(self, n):
        self.calls.append(("down", n))

    def key_up(self, n):
        self.calls.append(("up", n))

    def release_all(self, names):
        self.calls.append(("release_all", tuple(names)))


class _SwapSender:
    def __init__(self, stub):
        self.stub = stub

    def __enter__(self):
        self.orig = engine.sender
        engine.sender = self.stub
        return self.stub

    def __exit__(self, *a):
        engine.sender = self.orig
        return False


class TestSleep(unittest.TestCase):
    def test_sleep_full_duration(self):
        eng = engine.Engine()
        t0 = time.perf_counter()
        ok = eng._sleep(0.05)
        dt = time.perf_counter() - t0
        self.assertTrue(ok)
        self.assertGreaterEqual(dt, 0.04)
        self.assertLess(dt, 0.4)

    def test_sleep_interrupted(self):
        eng = engine.Engine()
        eng._stop.set()
        t0 = time.perf_counter()
        ok = eng._sleep(5.0)
        dt = time.perf_counter() - t0
        self.assertFalse(ok)
        self.assertLess(dt, 0.1)


class TestJitter(unittest.TestCase):
    def test_zero_jitter_identity(self):
        eng = engine.Engine()
        eng._cfg = engine.RunConfig(jitter_pct=0)
        self.assertEqual(eng._jitter(123), 123)

    def test_nonpositive_ms(self):
        eng = engine.Engine()
        eng._cfg = engine.RunConfig(jitter_pct=50)
        self.assertEqual(eng._jitter(0), 0)
        self.assertLessEqual(eng._jitter(-5), 0)

    def test_jitter_within_range(self):
        eng = engine.Engine()
        eng._cfg = engine.RunConfig(jitter_pct=50)
        vals = [eng._jitter(100) for _ in range(300)]
        self.assertTrue(all(50 <= v <= 150 for v in vals))


class TestTapInterruptible(unittest.TestCase):
    def test_stop_interrupts_long_hold(self):
        stub = _StubSender()
        eng = engine.Engine()
        with _SwapSender(stub):
            t = threading.Thread(target=eng._tap_interruptible,
                                 args=(["ctrl"], "c", 60000))
            t.start()
            time.sleep(0.12)
            t0 = time.perf_counter()
            eng._stop.set()
            t.join(timeout=2.0)
            dt = time.perf_counter() - t0
        self.assertFalse(t.is_alive())
        self.assertLess(dt, 0.5)
        self.assertEqual(eng._held, [])
        ups = [c for c in stub.calls if c[0] == "up"]
        self.assertTrue(ups)

    def test_exception_still_releases(self):
        stub = _StubSender()

        def boom(n):
            stub.calls.append(("down", n))
            if n == "c":
                raise OSError("模拟 SendInput 拒绝")

        stub.key_down = boom
        eng = engine.Engine()
        with _SwapSender(stub):
            with self.assertRaises(OSError):
                eng._tap_interruptible(["ctrl", "shift"], "c", 90)
        self.assertEqual(eng._held, [])
        ups = [c[1] for c in stub.calls if c[0] == "up"]
        self.assertIn("ctrl", ups)
        self.assertIn("shift", ups)

    def test_no_held_leak(self):
        stub = _StubSender()
        eng = engine.Engine()
        with _SwapSender(stub):
            for _ in range(4):
                eng._tap_interruptible(["ctrl"], "c", 20)
        self.assertEqual(eng._held, [])


class TestEquivalence(unittest.TestCase):
    """engine._tap_interruptible 与 sender.tap 实际发出的 INPUT 序列一致。"""

    def _capture(self, runner):
        seq = []

        def fake_send(*inputs):
            for inp in inputs:
                if inp.type == sender.INPUT_MOUSE:
                    seq.append(("mouse", inp.mi.dwFlags))
                else:
                    seq.append(("key", inp.ki.wVk, inp.ki.wScan, inp.ki.dwFlags))

        real_send = sender._send
        real_sleep = time.sleep
        sender._send = fake_send
        sender.time.sleep = lambda _s: None
        try:
            runner()
        finally:
            sender._send = real_send
            sender.time.sleep = real_sleep
        return seq

    def test_mod_combo_sequence_equal(self):
        tap_seq = self._capture(lambda: sender.tap(["ctrl", "shift"], "c", 90))

        def run_int():
            eng = engine.Engine()
            eng._sleep = lambda _s: True
            eng._tap_interruptible(["ctrl", "shift"], "c", 90)

        int_seq = self._capture(run_int)
        self.assertEqual(tap_seq, int_seq)
        self.assertTrue(tap_seq)

    def test_mouse_sequence_equal(self):
        tap_seq = self._capture(lambda: sender.tap([], "mouse_left", 50))

        def run_int():
            eng = engine.Engine()
            eng._sleep = lambda _s: True
            eng._tap_interruptible([], "mouse_left", 50)

        int_seq = self._capture(run_int)
        self.assertEqual(tap_seq, int_seq)
        self.assertTrue(tap_seq)

    def test_mod_gap_preserved(self):
        sleeps = []
        real_send = sender._send
        real_sleep = time.sleep
        sender._send = lambda *a: None
        sender.time.sleep = lambda s: sleeps.append(round(s, 4))
        try:
            sender.tap(["ctrl"], "c", 90)
            tap_sleeps = list(sleeps)
        finally:
            sender._send = real_send
            sender.time.sleep = real_sleep
        self.assertEqual(tap_sleeps[0], round(sender.MOD_GAP_S, 4))
        self.assertEqual(tap_sleeps[1], 0.09)


class TestForceRelease(unittest.TestCase):
    def test_idempotent(self):
        stub = _StubSender()
        eng = engine.Engine()
        with _SwapSender(stub):
            eng._held_add(["ctrl", "c"])
            r1 = eng.force_release()
            r2 = eng.force_release()
        self.assertEqual(sorted(r1), ["c", "ctrl"])
        self.assertEqual(r2, [])
        self.assertEqual(eng._held, [])

    def test_while_worker_running(self):
        stub = _StubSender()
        eng = engine.Engine()
        with _SwapSender(stub):
            t = threading.Thread(target=eng._tap_interruptible,
                                 args=(["ctrl"], "c", 1500))
            t.start()
            time.sleep(0.12)
            for _ in range(10):
                eng.force_release()          # 不应抛异常（含并发）
            eng._stop.set()
            t.join(timeout=2.0)
        self.assertFalse(t.is_alive())
        self.assertEqual(eng._held, [])


if __name__ == "__main__":
    unittest.main()
