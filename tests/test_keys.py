# -*- coding: utf-8 -*-
"""keys.py 纯函数单元测试：parse_combo / code_of / normalize / _parse_raw。"""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import kp_test_env  # noqa: E402,F401  (重定向 APPDATA + 加 sys.path)

import keys  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_lower_strip(self):
        self.assertEqual(keys.normalize("  SPACE  "), "space")

    def test_aliases(self):
        self.assertEqual(keys.normalize("escape"), "esc")
        self.assertEqual(keys.normalize("return"), "enter")
        self.assertEqual(keys.normalize("altgr"), "ralt")
        self.assertEqual(keys.normalize("lmb"), "mouse_left")
        self.assertEqual(keys.normalize("del"), "delete")

    def test_unknown_passthrough(self):
        self.assertEqual(keys.normalize("nosuchkey"), "nosuchkey")


class TestParseCombo(unittest.TestCase):
    def test_empty_raises(self):
        for spec in ("", "   "):
            with self.assertRaises(ValueError):
                keys.parse_combo(spec)

    def test_plus_is_equal(self):
        self.assertEqual(keys.parse_combo("+"), ([], "="))
        self.assertEqual(keys.parse_combo("="), ([], "="))

    def test_trailing_plus(self):
        self.assertEqual(keys.parse_combo("ctrl+"), ([], "ctrl"))

    def test_leading_plus(self):
        self.assertEqual(keys.parse_combo("+c"), ([], "c"))

    def test_two_nonimodifiers_rejected(self):
        with self.assertRaises(ValueError):
            keys.parse_combo("a+b")

    def test_case_and_spaces(self):
        self.assertEqual(keys.parse_combo("CTRL + C"), (["ctrl"], "c"))

    def test_full_combo(self):
        self.assertEqual(keys.parse_combo("ctrl+shift+f1"), (["ctrl", "shift"], "f1"))

    def test_raw_scancode_main(self):
        self.assertEqual(keys.parse_combo("sc:0x11"), ([], "sc:0x11"))

    def test_unknown_main_raises(self):
        with self.assertRaises(ValueError):
            keys.parse_combo("nosuchkey")


class TestCodeOf(unittest.TestCase):
    def test_named_keys(self):
        self.assertEqual(keys.code_of("space"), (0x20, 0x39, False))
        self.assertEqual(keys.code_of("numenter"), (0x0D, 0x1C, True))
        self.assertEqual(keys.code_of("num/"), (0x6F, 0x35, True))

    def test_raw_scancode(self):
        self.assertEqual(keys.code_of("sc:0x11"), (0, 0x11, False))
        self.assertEqual(keys.code_of("sc:e0:0x35"), (0, 0x35, True))

    def test_raw_vk_known_returns_table(self):
        # vk:0x41 == 'a'
        self.assertEqual(keys.code_of("vk:0x41"), (0x41, 0x1E, False))

    def test_raw_vk_unknown(self):
        self.assertEqual(keys.code_of("vk:0xFE"), (0xFE, 0, False))

    def test_unknown_raises_keyerror(self):
        with self.assertRaises(KeyError):
            keys.code_of("nosuchkey")


class TestParseRaw(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(keys._parse_raw("sc:0x11"), (0, 0x11, False))
        self.assertEqual(keys._parse_raw("sc:e0:0x35"), (0, 0x35, True))
        self.assertEqual(keys._parse_raw("sc:17"), (0, 17, False))   # 十进制

    def test_out_of_range(self):
        with self.assertRaises(ValueError):
            keys._parse_raw("sc:0x100")
        with self.assertRaises(ValueError):
            keys._parse_raw("vk:0x0")

    def test_not_raw_returns_none(self):
        self.assertIsNone(keys._parse_raw("space"))
        self.assertIsNone(keys._parse_raw("foo:0x1"))


class TestNameFromScan(unittest.TestCase):
    def test_extended(self):
        self.assertEqual(keys.name_from_scan(0x35, True), "num/")
        self.assertEqual(keys.name_from_scan(0x35, False), "/")

    def test_unknown_returns_raw(self):
        self.assertEqual(keys.name_from_scan(0x7F, False), "sc:0x7f")
        self.assertEqual(keys.name_from_scan(0x7F, True), "sc:e0:0x7f")


class TestIsKnown(unittest.TestCase):
    def test_mouse_buttons_known(self):
        for name in ("lmb", "rmb", "mmb", "mouse_left"):
            self.assertTrue(keys.is_known(name))

    def test_bad_range_not_known(self):
        self.assertFalse(keys.is_known("sc:0x100"))


if __name__ == "__main__":
    unittest.main()
