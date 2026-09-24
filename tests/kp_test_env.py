# -*- coding: utf-8 -*-
"""测试环境引导：把 KeyPresser 加入 sys.path，并把 APPDATA 重定向到临时目录。

必须在 import 任何项目模块（profiles / gui_simple / applog …）之前执行，
这些模块在 import 时就会按 %APPDATA% 计算存档与日志路径。
"""
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_KP = _ROOT / "KeyPresser"
if str(_KP) not in sys.path:
    sys.path.insert(0, str(_KP))

# 同一进程内只建一次临时目录（本模块被缓存，import 一次即执行一次）
_TMP = os.environ.get("KP_UNITTEST_APPDATA")
if not _TMP:
    _TMP = tempfile.mkdtemp(prefix="kp_unittest_")
    os.environ["KP_UNITTEST_APPDATA"] = _TMP

# 关键：绝不触碰用户真实 %APPDATA%\KeyPresser
os.environ["APPDATA"] = _TMP

PROJECT_ROOT = _ROOT
KEYPRESSER_DIR = _KP
TEMP_APPDATA = Path(_TMP)
