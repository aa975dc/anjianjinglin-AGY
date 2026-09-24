"""自检：三语言包 / 三个界面 / 热键分发 / 迷你窗口生命周期 / 文件日志 / 本轮修复回归。

三条安全技巧：
1. 把目标窗口设成不存在的标题，引擎会在发送任何按键之前就因"找不到窗口"退出，
   于是能在**不注入按键**的前提下走通 start_script 的真实代码路径。
2. `make()` 里把 `_elevation_hwnd` 打桩返回 0：自检调 start_script 会触发
   _check_elevation，迷你版查的是前台窗口，若前台恰好是高权限进程会弹出阻塞对话框。
3. 所有配置与日志都重定向到临时目录：自检**绝不**触碰用户真实的
   simple.json / settings.json / 日志（早期版本会污染真实配置且不恢复）。

注意：同一进程里反复创建/销毁 Tk 根窗口会互相抢全局热键，
每个 GUI 用例之间必须走 on_close() + 休眠；直接 destroy() 会绕过清理并留下 stderr 噪音。
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "KeyPresser"))

# --- 隔离：配置与日志全部落在临时目录，绝不改用户真实存档 / 日志 ---
# 目录布局与真实环境一致（%APPDATA%\KeyPresser\...），这样把子进程的 APPDATA
# 指到 TMP_DIR 后，子进程与父进程读写的是同一套临时文件。
TMP_DIR = Path(tempfile.mkdtemp(prefix="kp_smoke_"))
_TMP_KP = TMP_DIR / "KeyPresser"

import applog
applog.LOG_DIR = _TMP_KP / "logs"
applog.LOG_FILE = applog.LOG_DIR / "keypresser.log"

import gui_simple
gui_simple.SETTINGS_FILE = _TMP_KP / "simple.json"

import profiles
profiles.SETTINGS_FILE = _TMP_KP / "settings.json"

# 解释器探测：优先取与当前解释器同目录的 pythonw.exe，换机可用
PYW = str(Path(sys.executable).with_name("pythonw.exe"))
if not Path(PYW).exists():
    PYW = sys.executable

WM_CLOSE = 0x0010
user32 = ctypes.WinDLL("user32", use_last_error=True)

results = []


def check(name, fn):
    try:
        results.append((name, fn()))
    except Exception as exc:
        results.append((name, f"FAIL  {type(exc).__name__}: {exc}"))


def make(cls_name):
    import gui_mini
    import gui_simple
    cls = gui_mini.MiniApp if cls_name == "mini" else gui_simple.SimpleApp
    app = cls()
    # 真打桩：避免 _check_elevation 在前台为高权限进程时弹阻塞对话框
    app._elevation_hwnd = lambda: 0
    app.update_idletasks()
    return app


def make_simple():
    return make("simple")


def drop(app):
    app.on_close()            # 走真实退出路径：取消 after 轮询 + 释放热键
    time.sleep(0.25)


def write_settings(data: dict) -> None:
    from gui_simple import SETTINGS_FILE
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def wait_window(seconds: float = 8.0) -> int:
    import instance
    end = time.time() + seconds
    while time.time() < end:
        hwnd = instance.find_existing_window()
        if hwnd:
            return hwnd
        time.sleep(0.12)
    return 0


# ----------------------------------------------------------------- 基础 --
def t_i18n():
    import string

    import i18n

    def fields(text):
        return sorted(f for _l, f, _s, _c in string.Formatter().parse(text) if f)

    packs = {"EN": i18n.EN, "ZH": i18n.ZH, "RU": i18n.RU}
    base = set(i18n.EN)
    problems = []
    for name, pack in packs.items():
        miss = base - set(pack)
        extra = set(pack) - base
        if miss or extra:
            problems.append(f"{name} 缺={sorted(miss)[:4]} 多={sorted(extra)[:4]}")
    for key in base:
        ph = {n: fields(packs[n][key]) for n in packs}
        if not (ph["EN"] == ph["ZH"] == ph["RU"]):
            problems.append(f"{key} 占位符不一致 {ph}")
    if problems:
        return "FAIL  " + " | ".join(problems[:4])
    return (f"OK  EN={len(i18n.EN)} ZH={len(i18n.ZH)} RU={len(i18n.RU)} "
            f"key 集合与占位符三方一致, 默认语言={i18n.DEFAULT_LANGUAGE}")


def t_full_gui_still_works():
    import gui
    app = gui.App()
    app.withdraw()
    app.update_idletasks()
    bound, failed = app.hotkeys.bindings, list(app.hotkeys.failed)
    app.on_close()
    time.sleep(0.25)
    if failed:
        return f"FAIL  {failed}"
    return f"OK  完整界面仍可用, 热键={bound}"


def t_simple_build():
    app = make_simple()
    app.withdraw()
    info = {"标题": app.title(), "热键": app.hotkeys.bindings,
            "失败": list(app.hotkeys.failed), "按键提示": app.var_keyinfo.get(),
            "间隔提示": app.var_gap.get(), "目标选项数": len(app.combo_target["values"])}
    drop(app)
    if info["失败"]:
        return f"FAIL  热键失败={info['失败']}"
    return "OK  " + " | ".join(f"{k}={v}" for k, v in info.items())


def t_collect_and_dispatch():
    app = make_simple()
    app.withdraw()
    app.var_key.set("ctrl+c")
    app.var_hold.set("120")
    app.var_delay.set("880")
    app.var_infinite.set(False)
    app.var_cycles.set("7")
    app.var_target.set("不存在的窗口__TEST__")
    cfg = app._collect()

    calls = []

    class Stub:
        def __init__(self):
            self.is_running = False
            self.is_paused = False

        def start(self, _c):
            calls.append("start")
            self.is_running = True
            return True

        def stop(self, join=False):
            calls.append("stop")
            self.is_running = False

        def toggle_pause(self):
            calls.append("pause")

    app.engine = Stub()
    app._handle_action("run_toggle")
    app._handle_action("pause")
    app._handle_action("stop")
    snap = list(calls)
    info = (f"steps={cfg.steps} cycles={cfg.cycles} "
            f"target={cfg.target_title!r} | 分发={snap}")
    drop(app)
    if snap != ["start", "pause", "stop"]:
        return f"FAIL  分发={snap}"
    return "OK  " + info


def t_real_start_no_injection():
    app = make_simple()
    app.withdraw()
    app.var_key.set("space")
    app.var_target.set("不存在的窗口__TEST__")
    app.start_script()
    time.sleep(0.4)
    app.update()
    log_text = app.txt_log.get("1.0", "end")
    drop(app)
    if "找不到窗口" not in log_text:
        return f"FAIL  引擎未走到'找不到窗口': {log_text.strip()[-140:]!r}"
    return "OK  无按键注入即退出，提示命中"


# ----------------------------------------------------------------- 迷你 --
def t_mini_build_and_corner():
    """默认右下无存档时应停在屏幕**左上角**。"""
    write_settings({"key": "space", "hold_ms": "90", "delay_ms": "1000",
                    "cycles": 0, "target": ""})       # 故意不带 pos
    app = make("mini")
    app.update_idletasks()
    w, h = app.winfo_width(), app.winfo_height()
    x, y = app.winfo_x(), app.winfo_y()
    info = {"标题": app.title(), "尺寸": f"{w}x{h}", "位置": f"({x},{y})",
            "热键": app.hotkeys.bindings, "失败": list(app.hotkeys.failed),
            "置顶": app.var_top.get(), "间隔拆分": app.var_gap.get()}
    app.withdraw()
    drop(app)
    if info["失败"]:
        return f"FAIL  热键失败={info['失败']}"
    if (x, y) != (app.MARGIN, app.MARGIN):
        return f"FAIL  默认位置应为左上角 ({app.MARGIN},{app.MARGIN})，实际 ({x},{y})"
    if "toggle_window" not in info["热键"]:
        return f"FAIL  缺少 F4 显示/隐藏热键: {info['热键']}"
    return "OK  " + " | ".join(f"{k}={v}" for k, v in info.items())


def t_mini_interval_split():
    app = make("mini")
    app.withdraw()
    cases = []
    for total, want in ((1000, (90, 910)), (50, (50, 0)), (90, (90, 0)), (5000, (90, 4910))):
        app.var_interval.set(str(total))
        app.update_idletasks()
        got = (int(app.var_hold.get()), int(app.var_delay.get()))
        if got != want:
            drop(app)
            return f"FAIL  {total} 拆成 {got}，期望 {want}"
        cases.append(f"{total}->{got[0]}+{got[1]}")
    app.var_interval.set("1000")
    cfg = app._collect()
    step = cfg.steps[0]
    ok_target = app._target_title() == ""
    drop(app)
    return (f"OK  拆分={cases} | 引擎收到 hold={step['hold_ms']} "
            f"delay={step['delay_ms']} | 目标为空={ok_target}")


def t_mini_settings_roundtrip():
    """迷你版不应破坏简洁版保存的目标窗口设置。"""
    from gui_simple import SETTINGS_FILE, ACTIVE_WINDOW
    write_settings({"key": "e", "hold_ms": "90", "delay_ms": "910", "cycles": 0,
                    "target": "记事本"})
    app = make("mini")
    app.withdraw()
    app.var_interval.set("500")
    app._save_settings()
    drop(app)
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    if data.get("target") != "记事本":
        return f"FAIL  目标窗口被覆盖成 {data.get('target')!r}"
    if data.get("hold_ms") != "90" or data.get("delay_ms") != "410":
        return f"FAIL  间隔未写入: hold={data.get('hold_ms')} delay={data.get('delay_ms')}"
    if "pos" not in data or "topmost" not in data:
        return "FAIL  置顶/位置未存档"
    return (f"OK  目标窗口保留={data['target']!r} | 间隔={data['hold_ms']}+"
            f"{data['delay_ms']} | pos={data['pos']} | 置顶={data['topmost']}")


def t_mini_hide_background():
    """真机：F4 隐藏 → 后台仍在跑 → F4 显示 → 点X隐藏且进程不死。"""
    import instance
    import sender
    import winutil

    p = subprocess.Popen([PYW, str(ROOT / "KeyPresser" / "main.py"), "mini"],
                         env={**os.environ, "APPDATA": str(TMP_DIR)})
    try:
        hwnd = wait_window()
        if not hwnd:
            return "FAIL  迷你窗口未出现"
        time.sleep(1.2)                     # 留足热键注册时间
        title = winutil.window_title(hwnd)
        steps = [f"启动: {title!r}"]

        def toggle_until(want_hidden, tries=4):
            """合成 F4 偶有丢失，轮询重试到目标状态（真机全局热键本就不可靠）。"""
            for _ in range(tries):
                if (instance.find_existing_window() == 0) == want_hidden:
                    return True
                sender.tap([], "f4", 40)
                end = time.time() + 1.5
                while time.time() < end:
                    if (instance.find_existing_window() == 0) == want_hidden:
                        return True
                    time.sleep(0.12)
            return (instance.find_existing_window() == 0) == want_hidden

        hidden = toggle_until(True)         # F4 -> 隐藏
        alive_hidden = p.poll() is None
        steps.append(f"F4后隐藏={hidden} 进程存活={alive_hidden}")

        back = toggle_until(False)          # F4 -> 显示
        steps.append(f"再按F4已显示={back}")

        hwnd2 = instance.find_existing_window()
        if hwnd2:
            user32.PostMessageW(hwnd2, WM_CLOSE, 0, 0)   # 点 X
        time.sleep(1.0)
        closed_hidden = instance.find_existing_window() == 0
        alive_after_x = p.poll() is None
        steps.append(f"点X后隐藏={closed_hidden} 进程存活={alive_after_x}")

        if not (hidden and alive_hidden and back and closed_hidden and alive_after_x):
            return "FAIL  " + " | ".join(steps)
        return "OK  " + " | ".join(steps)
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        time.sleep(0.4)


def t_log_file():
    """日志要真的落盘，并包含关键事件。"""
    text = ""
    if applog.LOG_FILE.exists():
        text = applog.LOG_FILE.read_text(encoding="utf-8", errors="replace")
    must = {
        "启动记录": "启动 界面模式=",
        "热键注册": "热键注册:",
        "界面初始化": "初始化界面:",
        "窗口隐藏": "窗口已隐藏到后台",
        "窗口显示": "窗口已显示",
        "退出记录": "日志结束",
    }
    missing = [k for k, v in must.items() if v not in text]
    if missing:
        return f"FAIL  日志缺少: {missing} (日志 {len(text)} 字符)"
    lines = text.count("\n")
    return (f"OK  {applog.LOG_FILE.name} {len(text)} 字符 / {lines} 行，"
            f"关键事件齐全: {list(must)}")


def t_hotkeys_reacquirable():
    """上一条用例强杀了进程，热键释放后应能重新注册。"""
    import hotkeys
    mgr = hotkeys.HotkeyManager(on_action=lambda a: None)
    mgr.set_bindings({"run_toggle": "f1", "pause": "f2", "stop": "f3",
                      "toggle_window": "f4"})
    time.sleep(0.35)
    failed = list(mgr.failed)
    mgr.stop()
    return "OK  全部释放，F1~F4 可重新注册" if not failed else f"FAIL  残留={failed}"


# ------------------------------------------------------- 本轮修复回归 --
def t_poll_survives_handler_exception():
    """A1：某条 handler 抛非 Empty 异常后，轮询必须继续消费队列。"""
    app = make_simple()
    app.withdraw()
    consumed = []
    real = app._handle_message

    def fake(kind, payload):
        if payload == "BOOM":
            raise RuntimeError("注入的 handler 异常")
        consumed.append(payload)
        real(kind, payload)

    app._handle_message = fake
    app.q.put(("log", "BOOM"))          # 第一条让 handler 崩
    app.q.put(("log", "SENTINEL"))      # 第二条（哨兵）必须仍被消费
    for _ in range(8):
        app.update()
        time.sleep(0.06)
    drop(app)
    if "SENTINEL" not in consumed:
        return "FAIL  轮询被 handler 异常拖死（哨兵未被消费）"
    return "OK  handler 抛异常后轮询仍存活，哨兵已被消费"


def t_collect_clamps_hold():
    """A2：简洁版 _collect 必须钳制 hold，不能让超大值直达引擎。"""
    app = make_simple()
    app.withdraw()
    app.var_hold.set("999999999")
    app.var_delay.set("0")
    app.var_target.set("不存在的窗口__TEST__")
    cfg = app._collect()
    hold = cfg.steps[0]["hold_ms"]
    target = cfg.target_title
    drop(app)
    if not 1 <= hold <= 60000:
        return f"FAIL  按住未被钳制: {hold}"
    return f"OK  hold 999999999 -> {hold}（≤60000）| 目标保留={target!r}"


def t_target_preserved_when_not_running():
    """C1：目标程序没运行（不在窗口列表）时，设置不能被静默重置写空。"""
    from gui_simple import SETTINGS_FILE
    write_settings({"key": "space", "hold_ms": "90", "delay_ms": "1000",
                    "cycles": 0, "target": "记事本__不存在__"})
    app = make_simple()
    app.withdraw()
    app._save_settings_now()            # 强制立即落盘
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    got = data.get("target")
    drop(app)
    if got != "记事本__不存在__":
        return f"FAIL  未运行的目标窗口被重置为 {got!r}"
    return f"OK  未运行的目标窗口保留 = {got!r}"


def t_launch_target_keeps_mode():
    """A3：提权重启必须透传界面模式，否则会回到错误的界面。"""
    import instance
    old = sys.argv
    try:
        sys.argv = ["main.py", "mini"]
        _, p_mini = instance._launch_target()
        sys.argv = ["main.py", "full"]
        _, p_full = instance._launch_target()
        sys.argv = ["main.py"]
        _, p_simple = instance._launch_target()
    finally:
        sys.argv = old
    ok = ("mini" in p_mini and "full" in p_full
          and "mini" not in p_simple and "full" not in p_simple)
    if not ok:
        return f"FAIL  mini={p_mini!r} full={p_full!r} simple={p_simple!r}"
    return f"OK  mini→{p_mini!r} full→{p_full!r} simple→{p_simple!r}"


def t_hold_range_consistent():
    """N2：normalize_step / validate_run_config / 完整版 UI 上限三处 hold 口径必须一致。"""
    import engine
    import profiles
    raw = {"key": "space", "action": "tap", "hold_ms": 500_000}
    norm = profiles.normalize_step(dict(raw))["hold_ms"]
    fixed, _notes = profiles.validate_run_config(
        engine.RunConfig(steps=[dict(raw)], start_delay_ms=0))
    val = fixed.steps[0]["hold_ms"]
    ui_hi = profiles.HOLD_MS_RANGE[1]        # 完整版 Spinbox 上限即取此常量
    if not (norm == val == ui_hi == 60_000):
        return f"FAIL normalize={norm} validate={val} UI上限={ui_hi}"
    return (f"OK  同一 hold=500000 → normalize={norm} / validate={val} / "
            f"UI上限={ui_hi}（三处口径一致）")


# 开始时清掉旧日志，让断言只针对本次运行
applog.setup()
try:
    applog.LOG_FILE.unlink(missing_ok=True)
except Exception:
    pass

check("中文语言包", t_i18n)
check("完整界面兼容", t_full_gui_still_works)
check("简洁界面构建", t_simple_build)
check("配置收集+热键分发", t_collect_and_dispatch)
check("真实启动路径(无注入)", t_real_start_no_injection)
check("迷你界面构建+左上角", t_mini_build_and_corner)
check("迷你-间隔拆分", t_mini_interval_split)
check("迷你-存档不串味", t_mini_settings_roundtrip)
check("迷你-隐藏/后台运行", t_mini_hide_background)
check("文件日志落盘", t_log_file)
check("热键释放验证", t_hotkeys_reacquirable)
check("回归-轮询存活", t_poll_survives_handler_exception)
check("回归-按住被钳制", t_collect_clamps_hold)
check("回归-目标窗口保留", t_target_preserved_when_not_running)
check("回归-提权保留模式", t_launch_target_keeps_mode)
check("回归-hold口径一致", t_hold_range_consistent)

print("-" * 78)
for name, msg in results:
    print(f"{name:<22} {msg}")
print("-" * 78)
print("PASS" if all("FAIL" not in m for _n, m in results) else "存在失败项")
