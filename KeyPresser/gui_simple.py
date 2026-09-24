"""简洁中文界面。

设计原则：只保留"选键 → 设间隔 → 启停"这条主线，其余全部隐藏。
核心逻辑复用上游：sender / hotkeys / keys / winutil / recorder 与上游**逐字节一致**；
engine.py 因修复"长按住导致系统级卡键"做了最小增量改动（可中断按住 + force_release）。
"""

import json
import os
import queue
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import engine as eng
import applog
import i18n
import keys
import profiles
import ui_fx
import ui_theme
import winutil
from gui import KeyCaptureDialog        # 复用上游的按键捕获对话框
from hotkeys import HotkeyManager

APP_TITLE = "自动按键工具"

# 本界面的状态存档（与上游 settings.json 分开，互不干扰）
SETTINGS_FILE = (Path(os.environ.get("APPDATA", Path.home()))
                 / "KeyPresser" / "simple.json")

ACTIVE_WINDOW = "（当前活动窗口）"

CJK_FONTS = ("Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "SimSun")


class SimpleApp(tk.Tk):
    POLL_MS = 50
    MAX_LOG_LINES = 300
    TITLE = APP_TITLE          # 子类（迷你版）可覆盖
    START_COUNTDOWN_S = 3      # 点「启动」按钮后的待命倒计时（秒）
    SAVE_DEBOUNCE_MS = 500     # 写盘合并窗口（毫秒）

    STATE_TEXTS = {"stopped": "已停止", "running": "运行中", "paused": "已暂停"}

    def __init__(self):
        super().__init__()
        i18n.set_language("zh")          # 本界面固定中文，引擎日志也随之中文

        self.logger = applog.get("ui")
        self.logger.info("初始化界面: %s", type(self).__name__)

        self.title(self.TITLE)
        self.resizable(False, False)
        self._setup_fonts()
        self.overrideredirect(True)      # 自绘顶栏（画板 1），靠任务栏/Alt+Tab 常驻

        self._settings = self._load_settings()
        self._theme_name = self._settings.get("theme", "dark")
        self.q: queue.Queue = queue.Queue()
        self._win_titles: list[str] = []
        self._poll_id: str | None = None

        # --- 存档落盘节流（详见 _save_settings / _flush_settings）---
        self._settings_ready = False      # 初始化完成前只缓存、不落盘
        self._settings_dirty = False
        self._flush_id: str | None = None

        # --- 3 秒待命倒计时 / 上一个非本进程前台窗口跟踪 ---
        self._prev_fg_hwnd = 0
        self._countdown_id: str | None = None
        self._countdown_left = 0
        self._relaunch_id: str | None = None   # 倒计时末尾 150ms 延迟启动的定时器
        self._fx_state_key: str | None = None  # 状态点当前所处状态（动效用）

        self.engine = eng.Engine(
            on_log=lambda m: self.q.put(("log", m)),
            on_state=lambda s: self.q.put(("state", s)),
            on_error=lambda m: self.q.put(("error", m)),
            on_finish=lambda: self.q.put(("finish", None)),
        )
        self.hotkeys = HotkeyManager(
            on_action=lambda a: self.q.put(("action", a)),
            on_error=lambda m: self.q.put(("log", m)),
        )

        self._init_vars()
        self._build_ui()
        self._refresh_hints()
        self._sync_cycles_state()
        self.refresh_windows()

        bindings = self._hotkey_bindings()
        self.hotkeys.set_bindings(bindings)
        for act in self.hotkeys.failed:
            self.log(f"热键“{self._hotkey_label(act)}”被其他程序占用，未能启用。")
        self.logger.info("热键注册: 成功=%s 失败=%s",
                         {a: c for a, c in bindings.items()
                          if a not in self.hotkeys.failed},
                         list(self.hotkeys.failed) or "无")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.log("就绪。在目标窗口中按 F1 启动，F2 暂停，F3 停止。")
        self._track_foreground()          # 记住点按钮前的前台窗口作为候选目标
        self._poll_id = self.after(self.POLL_MS, self._poll)
        if not self._needs_own_init():
            self._mark_settings_ready()

    def _needs_own_init(self) -> bool:
        """子类（迷你版）在 super().__init__ 之后还有定位等收尾步骤时返回 True。"""
        return False

    def _mark_settings_ready(self) -> None:
        """初始化收尾：此后才允许把设置写进磁盘（避免写入尚未定位的坐标）。"""
        self._settings_ready = True
        self._save_settings()

    # ------------------------------------------------------------ 子类扩展点 --
    def _hotkey_bindings(self) -> dict:
        """子类（迷你版）可追加自己的热键动作。"""
        return dict(profiles.DEFAULT_HOTKEYS)

    def _hotkey_label(self, action: str) -> str:
        return profiles.hotkey_label(action)

    # ------------------------------------------------------------------ 字体 --
    def _setup_fonts(self) -> None:
        from tkinter import font as tkfont
        available = set(tkfont.families(self))
        family = next((f for f in CJK_FONTS if f in available), None)
        if not family:
            return
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                     "TkHeadingFont", "TkTooltipFont"):
            try:
                tkfont.nametofont(name).configure(family=family, size=10)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ 变量 --
    def _init_vars(self) -> None:
        s = self._settings
        self.var_key = tk.StringVar(value=s.get("key", "space"))
        self.var_hold = tk.StringVar(value=str(s.get("hold_ms", 90)))
        self.var_delay = tk.StringVar(value=str(s.get("delay_ms", 1000)))
        self.var_infinite = tk.BooleanVar(value=s.get("cycles", 0) == 0)
        self.var_cycles = tk.StringVar(value=str(s.get("cycles", 10) or 10))
        self.var_target = tk.StringVar(value=s.get("target", "") or ACTIVE_WINDOW)
        self.var_status = tk.StringVar(value="已停止")
        self.var_gap = tk.StringVar(value="")
        self.var_keyinfo = tk.StringVar(value="")
        self.var_summary = tk.StringVar(value="")
        self.var_tdesc = tk.StringVar(value="发送到 当前活动窗口")
        self.var_logtime = tk.StringVar(value="")
        self.var_logtext = tk.StringVar(value="")

        for v in (self.var_key, self.var_hold, self.var_delay):
            v.trace_add("write", lambda *_: self._refresh_hints())
        self.var_infinite.trace_add("write", lambda *_: self._sync_cycles_state())
        self.var_target.trace_add("write", lambda *_: self._update_tdesc())

    # ------------------------------------------------------------------ 界面 --
    # 布局常量（画板 1：560×650，顶栏 52，日志条 30，卡片圆角 12，内容边距 16）
    WIN_W, WIN_H = 560, 650
    TOPBAR_H, LOGBAR_H = 52, 30

    def _build_ui(self) -> None:
        t = self._theme = dict(ui_theme.LIGHT if self._theme_name == "light"
                               else ui_theme.DARK)
        # 首次启动放屏幕居中（无边框窗口没有系统默认定位，避免"开了但看不见"）
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.WIN_W}x{self.WIN_H}"
                      f"+{max(0, (sw - self.WIN_W) // 2)}"
                      f"+{max(0, (sh - self.WIN_H) // 2)}")
        self.cv = tk.Canvas(self, bg=t["bg"], highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self._build_topbar()
        self._build_cards()
        self._build_logbar()
        ui_theme.round_window(self)
        ui_theme.add_taskbar(self)
        ui_theme.enable_drag(self, self.cv,
                             zone=lambda e: e.y <= self.TOPBAR_H)

    # -- 控件快捷方式 ----------------------------------------------------
    def _lbl(self, x, y, text, font, fg, bg=None, anchor="w",
             tv: tk.StringVar | None = None) -> tk.Label:
        lb = tk.Label(self.cv, text=text, font=font, fg=fg, bd=0,
                      bg=bg or self._theme["card"], textvariable=tv)
        self.cv.create_window(x, y, window=lb, anchor=anchor)
        return lb

    def _entry(self, x, y, tv, w, h=36, mono=14, r=8) -> tk.Entry:
        """设计稿输入框：画布上画圆角底（r8 描边），Entry 内嵌左移 12px 作文字区。"""
        t = self._theme
        fid = ui_theme.rounded(self.cv, x, y - h / 2, x + w, y + h / 2, r,
                               fill=t["input_bg"], outline=t["border"])
        e = tk.Entry(self.cv, textvariable=tv, bg=t["input_bg"], fg=t["text1"],
                     insertbackground=t["text1"], relief="flat",
                     font=ui_theme.f_mono(mono), highlightthickness=0,
                     disabledbackground=t["fill3"],
                     disabledforeground=t["ghost"],
                     selectbackground=t["accent"], selectforeground="#FFFFFF")
        e._field_item = fid
        e.bind("<FocusIn>", lambda *_: self.cv.itemconfigure(
            fid, outline=t["accent"]))
        e.bind("<FocusOut>", lambda *_: self.cv.itemconfigure(
            fid, outline=t["border"]))
        self.cv.create_window(x + 12, y, window=e, anchor="w",
                              width=w - 24, height=h)
        return e

    def _card(self, x1, y1, x2, y2) -> None:
        ui_theme.rounded(self.cv, x1, y1, x2, y2, 12, fill=self._theme["card"],
                         outline=self._theme["border"])

    # -- 顶栏（画板 1 · 3:2-3:23） ---------------------------------------
    def _build_topbar(self) -> None:
        t, cv, H = self._theme, self.cv, self.TOPBAR_H
        logo = tk.Canvas(cv, width=24, height=24, bg=t["bg"],
                         highlightthickness=0)
        ui_theme.rounded(logo, 0, 0, 24, 24, 6, fill=t["accent"])
        for mx, my, mw, a in ((6, 8.5, 3.4, 1.0), (10.7, 8.5, 3.4, 0.7),
                              (15.4, 8.5, 2.6, 0.45), (6, 12.8, 5.6, 0.85),
                              (12.9, 12.8, 5.1, 0.55)):
            logo.create_rectangle(mx, my, mx + mw, my + 3, width=0,
                                  fill=ui_theme.mix(t["accent"], "#FFFFFF", a))
        cv.create_window(16, H / 2, window=logo, anchor="w")
        self._lbl(48, H / 2, "自动按键工具", ui_theme.f_cn(14), t["text1"],
                  bg=t["bg"])

        hover = ui_theme.mix(t["card"], "#FFFFFF", 0.06)
        x = self.WIN_W - 12
        self.btn_min = ui_theme.RButton(
            cv, self._minimize, backdrop=t["bg"], bg=t["card"],
            border=t["border"], radius=7, height=26, icon="minus",
            icon_size=12, pad=(8, 8), hover=hover)
        x -= self.btn_min.px_width()
        cv.create_window(x, H / 2, window=self.btn_min, anchor="w")
        x -= 6
        self.btn_lang = ui_theme.RButton(
            cv, None, backdrop=t["bg"], text="中文", font=ui_theme.f_cn(12),
            fg=t["text2"], bg=t["card"], border=t["border"], radius=7,
            height=26, pad=(10, 10), hover=hover)
        x -= self.btn_lang.px_width()
        cv.create_window(x, H / 2, window=self.btn_lang, anchor="w")
        x -= 6
        self.btn_theme = ui_theme.RButton(
            cv, self._toggle_theme, backdrop=t["bg"],
            text="浅色" if self._theme_name == "dark" else "深色",
            font=ui_theme.f_cn(12), fg=t["text2"], bg=t["card"],
            border=t["border"], radius=7, height=26, pad=(10, 10), hover=hover)
        x -= self.btn_theme.px_width()
        cv.create_window(x, H / 2, window=self.btn_theme, anchor="w")
        x -= 6
        self.pill = ui_theme.RPill(cv, backdrop=t["bg"], bg=t["card"],
                                   border=t["border"], fg=t["text2"],
                                   text="已停止", dot=t["dim"])
        x -= self.pill.px_width()
        cv.create_window(x, H / 2, window=self.pill, anchor="w")

    def _minimize(self) -> None:
        ui_theme.minimize_window(self)

    def _toggle_theme(self) -> None:
        """深/浅主题切换（画板 1 ↔ 画板 2）：销毁画布重建，业务对象不动。"""
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self.cv.destroy()
        self._build_ui()
        self._fx_state_key = None
        self._refresh_hints()
        self._sync_cycles_state()
        self.refresh_windows()
        self._update_tdesc()
        self._sync_buttons()
        self._save_settings()

    # -- 内容卡片（画板 1 · 3:25-3:111） ---------------------------------
    def _build_cards(self) -> None:
        t, cv = self._theme, self.cv

        # ── 运行控制卡（3:26-3:53）──────────────────────────────
        self._card(16, 68, 544, 214)
        self.lbl_dot = self._lbl(34, 94, "●", ui_theme.f_cn(11), t["dim"])
        self._fx_dot = ui_fx.Breath(self.lbl_dot)
        self._lbl(50, 94, "", ui_theme.f_cn(16), t["text1"], tv=self.var_status)
        self._lbl(160, 94, "", ui_theme.f_cn(12), t["dim"], tv=self.var_tdesc)
        self._lbl(34, 130, "", ui_theme.f_cn(13), t["text2"],
                  tv=self.var_summary)
        self.btn_start = ui_theme.RButton(
            cv, self.on_start_button, backdrop=t["card"], text="启动",
            font=ui_theme.f_cn(15), fg="#FFFFFF", bg=t["accent"], radius=8,
            height=44, icon="play", icon_size=16, keycap="F1",
            keycap_bg=ui_theme.mix(t["accent"], "#FFFFFF", 0.2),
            keycap_fg="#FFFFFF", pad=(18, 13), gap=9,
            hover=ui_theme.mix(t["accent"], "#FFFFFF", 0.1))
        self.btn_pause = ui_theme.RButton(
            cv, self.toggle_pause, backdrop=t["card"], text="暂停",
            font=ui_theme.f_cn(13), fg=t["text2"], bg=t["fill2"],
            border=t["border"], radius=8, height=44, icon="pause",
            icon_size=14, keycap="F2",
            keycap_bg=ui_theme.mix(t["fill2"], "#FFFFFF", 0.06),
            keycap_fg=t["dim"], pad=(14, 11), gap=7,
            hover=ui_theme.mix(t["fill2"], "#FFFFFF", 0.06))
        self.btn_stop = ui_theme.RButton(
            cv, self.stop_script, backdrop=t["card"], text="停止",
            font=ui_theme.f_cn(13), fg=t["text2"], bg=t["fill2"],
            border=t["border"], radius=8, height=44, icon="stop",
            icon_size=14, keycap="F3",
            keycap_bg=ui_theme.mix(t["fill2"], "#FFFFFF", 0.06),
            keycap_fg=t["dim"], pad=(14, 11), gap=7,
            hover=ui_theme.mix(t["fill2"], "#FFFFFF", 0.06))
        bx = 34
        for b in (self.btn_start, self.btn_pause, self.btn_stop):
            cv.create_window(bx, 176, window=b, anchor="w")
            bx += b.px_width() + 10

        # ── 按键卡（3:54-3:67）──────────────────────────────────
        self._card(16, 226, 544, 349)
        self._lbl(34, 250, "按键", ui_theme.f_cn(13), t["text1"])
        self._lbl(526, 250, "第 1 步", ui_theme.f_mono(11), t["faint"],
                  anchor="e")
        self.btn_capture = ui_theme.RButton(
            cv, self.capture_key, backdrop=t["card"], text="按下要按的键…",
            font=ui_theme.f_cn(13), fg=t["text2"], bg=t["fill2"],
            border=t["border"], radius=8, height=36, pad=(13, 13),
            hover=ui_theme.mix(t["fill2"], "#FFFFFF", 0.06))
        cap_w = self.btn_capture.px_width()
        cv.create_window(526 - cap_w, 288, window=self.btn_capture, anchor="w")
        self.entry_key = self._entry(34, 288, self.var_key, w=492 - cap_w - 8)
        self._lbl(34, 325, "✓", ui_theme.f_cn(12), t["green"])
        self._lbl(52, 325, "", ui_theme.f_cn(12), t["dim"], tv=self.var_keyinfo)

        # ── 间隔卡（3:68-3:86）──────────────────────────────────
        self._card(16, 361, 544, 509)
        self._lbl(34, 385, "间隔", ui_theme.f_cn(13), t["text1"])
        self._lbl(526, 385, "第 2 步", ui_theme.f_mono(11), t["faint"],
                  anchor="e")
        self._lbl(34, 414, "按住", ui_theme.f_cn(12), t["dim"])
        self._lbl(154, 414, "等待", ui_theme.f_cn(12), t["dim"])
        self.entry_hold = self._entry(34, 448, self.var_hold, w=104)
        self.entry_delay = self._entry(154, 448, self.var_delay, w=104)
        for ex in (34 + 104 - 30, 154 + 104 - 30):
            self._lbl(ex, 448, "ms", ui_theme.f_mono(11), t["faint"],
                      bg=t["input_bg"])
        self._lbl(34, 485, "实际触发间隔", ui_theme.f_cn(12), t["dim"])
        self._lbl(118, 485, "", ui_theme.f_mono(13, True), t["text1"],
                  tv=self.var_gap)
        self._lbl(170, 485, "毫秒", ui_theme.f_cn(12), t["dim"])

        # ── 循环卡（3:87-3:100）─────────────────────────────────
        self._card(16, 521, 274, 615)
        self._lbl(34, 545, "循环", ui_theme.f_cn(13), t["text1"])
        self._lbl(260, 545, "第 3 步", ui_theme.f_mono(11), t["faint"],
                  anchor="e")
        self.seg_infinite = ui_theme.RButton(
            cv, lambda: self.var_infinite.set(True), backdrop=t["card"],
            text="无限循环", font=ui_theme.f_cn(12), fg="#FFFFFF",
            bg=t["accent"], radius=6, height=30, pad=(11, 11))
        self.seg_fixed = ui_theme.RButton(
            cv, lambda: self.var_infinite.set(False), backdrop=t["card"],
            text="指定次数", font=ui_theme.f_cn(12), fg=t["text2"],
            bg=t["fill2"], border=t["border"], radius=6, height=30,
            pad=(11, 11))
        cv.create_window(34, 580, window=self.seg_infinite, anchor="w")
        cv.create_window(34 + self.seg_infinite.px_width() + 8, 580,
                         window=self.seg_fixed, anchor="w")
        cx = (34 + self.seg_infinite.px_width() + 8
              + self.seg_fixed.px_width() + 8)
        self.entry_cycles = self._entry(cx, 580, self.var_cycles, w=52,
                                        h=30, mono=13, r=6)
        self.lbl_unit = self._lbl(cx + 52 - 18, 580, "次", ui_theme.f_cn(11),
                                  t["ghost"], bg=t["fill3"])

        # ── 目标窗口卡（3:101-3:111）────────────────────────────
        self._card(286, 521, 544, 615)
        self._lbl(304, 545, "目标窗口", ui_theme.f_cn(13), t["text1"])
        self._lbl(526, 545, "可选", ui_theme.f_cn(11), t["faint"], anchor="e")
        self.btn_refresh = ui_theme.RButton(
            cv, self.refresh_windows, backdrop=t["card"], text="刷新",
            font=ui_theme.f_cn(13), fg=t["text2"], bg=t["fill2"],
            border=t["border"], radius=8, height=36, pad=(11, 11),
            hover=ui_theme.mix(t["fill2"], "#FFFFFF", 0.06))
        rw = self.btn_refresh.px_width()
        cv.create_window(526 - rw, 583, window=self.btn_refresh, anchor="w")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("KP.TCombobox", fieldbackground=t["input_bg"],
                        background=t["fill2"], foreground=t["text1"],
                        arrowcolor=t["dim"], bordercolor=t["border"],
                        lightcolor=t["border"], darkcolor=t["border"],
                        borderwidth=0, arrowsize=11, padding=(10, 0))
        # readonly 状态有自己的样式映射，优先级高于 configure，必须一并覆盖
        style.map("KP.TCombobox",
                  fieldbackground=[("readonly", t["input_bg"])],
                  foreground=[("readonly", t["text1"])],
                  background=[("readonly", t["fill2"])],
                  bordercolor=[("readonly", t["border"])])
        self.tk.call("option", "add", "*TCombobox*Listbox.background",
                     t["fill2"])
        self.tk.call("option", "add", "*TCombobox*Listbox.foreground",
                     t["text1"])
        self.tk.call("option", "add", "*TCombobox*Listbox.selectBackground",
                     t["accent"])
        self.tk.call("option", "add", "*TCombobox*Listbox.selectForeground",
                     "#FFFFFF")
        self.combo_target = ttk.Combobox(cv, textvariable=self.var_target,
                                         state="readonly",
                                         style="KP.TCombobox",
                                         font=ui_theme.f_cn(13))
        cv.create_window(304, 583, window=self.combo_target, anchor="w",
                         width=526 - 304 - 8 - rw, height=36)

    # -- 日志条（画板 1 · 3:112-3:116） ----------------------------------
    def _build_logbar(self) -> None:
        t, cv = self._theme, self.cv
        y = self.WIN_H - self.LOGBAR_H / 2
        self.btn_log = ui_theme.RButton(cv, self._toggle_log, backdrop=t["bg"],
                                        icon="chevron", icon_size=12,
                                        radius=4, height=20, pad=(4, 4),
                                        bg=t["bg"], fg=t["dim"])
        cv.create_window(16, y, window=self.btn_log, anchor="w")
        self._lbl(38, y, "", ui_theme.f_mono(11), t["ghost"], bg=t["bg"],
                  tv=self.var_logtime)
        self._lbl(100, y, "", ui_theme.f_cn(11), t["faint"], bg=t["bg"],
                  tv=self.var_logtext)
        self.txt_log = tk.Text(cv, height=6, wrap="word", state="disabled",
                               relief="flat", bg=t["card"], fg=t["text2"],
                               insertbackground=t["text1"],
                               font=ui_theme.f_cn(11), highlightthickness=1,
                               highlightbackground=t["border"], padx=10, pady=6)
        self._log_win = cv.create_window(280, 545, window=self.txt_log,
                                         width=528, height=118)
        cv.itemconfigure(self._log_win, state="hidden")

    def _toggle_log(self) -> None:
        self._log_open = not getattr(self, "_log_open", False)
        self.cv.itemconfigure(self._log_win,
                              state="normal" if self._log_open else "hidden")
        self.btn_log.set_icon("chevron_up" if self._log_open else "chevron")

    # -------------------------------------------------------------- 目标窗口 --
    def refresh_windows(self) -> None:
        self._win_titles = [title for _h, title in winutil.list_windows() if title]
        values = [ACTIVE_WINDOW, *self._win_titles]
        current = self.var_target.get()
        if current and current not in values:
            # 目标程序当前没运行（很常见）不能当成"设置无效"——保留原值，
            # 把它并进候选列表让它仍能选上，等程序启动后即可正常命中。
            values.append(current)
            self.logger.info("目标窗口 %r 当前不在运行列表中，已保留原设置", current)
        self.combo_target["values"] = values

    def _target_title(self) -> str:
        sel = self.var_target.get()
        return "" if sel == ACTIVE_WINDOW else sel

    # ------------------------------------------------------------------ 提示 --
    def _refresh_hints(self) -> None:
        spec = self.var_key.get().strip()
        try:
            mods, main = keys.parse_combo(spec)
            vk, sc, ext = keys.code_of(main)
            combo = "+".join([*mods, main])
            if sc:
                code = f"扫描码 {sc:02X}" + ("（扩展键）" if ext else "")
            else:
                code = f"虚拟键码 {vk:02X}"
            self.var_keyinfo.set(f"已识别：{combo}（{code}）")
        except Exception as exc:
            self.var_keyinfo.set(f"按键无效：{exc}")

        try:
            gap = max(0, int(self.var_hold.get())) + max(0, int(self.var_delay.get()))
            self.var_gap.set(str(gap))
        except ValueError:
            self.var_gap.set("--")

        self._update_summary()
        self._save_settings()

    def _update_summary(self) -> None:
        """配置摘要（画板 1 · 3:33）：space · 每 1090 毫秒触发一次 · 无限循环"""
        try:
            gap = max(0, int(self.var_hold.get())) + max(0, int(self.var_delay.get()))
            gap_txt = f"每 {gap} 毫秒触发一次 · "
        except ValueError:
            gap_txt = ""
        try:
            cycles = max(1, int(self.var_cycles.get()))
        except ValueError:
            cycles = 1
        tail = ("无限循环" if self.var_infinite.get() else f"循环 {cycles} 次")
        self.var_summary.set(f"{self.var_key.get().strip()} · {gap_txt}{tail}")

    def _update_tdesc(self) -> None:
        """目标说明（3:32）：发送到 当前活动窗口 / 目标标题"""
        self.var_tdesc.set("发送到 "
                           + (self._target_title() or "当前活动窗口"))

    def _sync_cycles_state(self) -> None:
        t = self._theme
        infinite = self.var_infinite.get()
        if getattr(self, "seg_infinite", None) is None:
            # 迷你版（画板 3）没有循环分段控件，只保留存档
            self._save_settings()
            return
        self.seg_infinite.set_state(
            bg=t["accent"] if infinite else t["fill2"],
            fg="#FFFFFF" if infinite else t["text2"],
            border=None if infinite else t["border"])
        self.seg_fixed.set_state(
            bg=t["accent"] if not infinite else t["fill2"],
            fg="#FFFFFF" if not infinite else t["text2"],
            border=None if not infinite else t["border"])
        self.entry_cycles.config(state="normal" if not infinite else "disabled")
        self.cv.itemconfigure(self.entry_cycles._field_item,
                              fill=t["input_bg"] if not infinite
                              else t["fill3"])
        self.lbl_unit.config(bg=t["input_bg"] if not infinite else t["fill3"])
        self._update_summary()
        self._save_settings()

    # ------------------------------------------------------------------ 日志 --
    def log(self, msg: str) -> None:
        """界面日志条（画板 1 · 3:112）显示一行 + 可展开面板，同时写磁盘日志。"""
        text = str(msg)
        self.logger.info("%s", text)
        stamp = datetime.now().strftime("%H:%M:%S")
        self.var_logtime.set(stamp)
        self.var_logtext.set(" ".join(text.split()))
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", f"{stamp}  {text}\n")
        lines = int(self.txt_log.index("end-1c").split(".")[0])
        if lines > self.MAX_LOG_LINES:
            self.txt_log.delete("1.0", f"{lines - self.MAX_LOG_LINES}.0")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    # ------------------------------------------------------------ 收集配置 --
    def _collect(self) -> eng.RunConfig | None:
        spec = self.var_key.get().strip()
        try:
            keys.parse_combo(spec)
        except Exception as exc:
            self.logger.warning("按键解析失败: %r -> %s", spec, exc)
            messagebox.showerror("按键有误", str(exc), parent=self)
            return None
        try:
            hold = max(1, int(self.var_hold.get()))
            delay = max(0, int(self.var_delay.get()))
            cycles = 0 if self.var_infinite.get() else max(1, int(self.var_cycles.get()))
        except ValueError as exc:
            self.logger.warning("数值非法: 按住=%r 等待=%r 循环=%r (%s)",
                                self.var_hold.get(), self.var_delay.get(),
                                self.var_cycles.get(), exc)
            messagebox.showerror("数值有误", "按住 / 等待 / 循环次数必须填整数。",
                                 parent=self)
            return None

        step = {"key": spec, "action": "tap", "hold_ms": hold, "delay_ms": delay,
                "repeat": 1, "enabled": True, "comment": ""}
        cfg = eng.RunConfig(steps=[step], mode=eng.MODE_FOREGROUND,
                            target_title=self._target_title(),
                            cycles=cycles, cycle_delay_ms=0, jitter_pct=0,
                            start_delay_ms=0)
        # 统一钳制：不再让界面各自绕过校验，避免超大 hold 直达 sender.tap() 造成卡键
        cfg, notes = profiles.validate_run_config(cfg)
        if notes:
            for note in notes:
                self.logger.warning("运行参数已修正: %s", note)
            self.log(f"已自动修正越界的数值：{'；'.join(notes)}")
        return cfg

    # -------------------------------------------------------------- 控制动作 --
    def on_start_button(self) -> None:
        """「启动」按钮：先进入几秒待命倒计时，再自动把焦点还给目标窗口。

        直接点按钮会让焦点落在本工具自身窗口上，按键被注入自己的窗口、
        目标程序收不到 —— 这就是长期存在的"焦点陷阱"。倒计时给用户时间切回
        目标窗口，结束时（若捕获到候选窗口）再主动 activate 一次兜底。
        """
        if self._countdown_id is not None:
            self._cancel_countdown("再次点击启动按钮")
            return
        if self.engine.is_running:
            self.logger.info("忽略启动请求: 已在运行")
            return
        cfg = self._collect()          # 先校验，参数不对立刻提示，不进入倒计时
        if cfg is None:
            return
        self._countdown_left = self.START_COUNTDOWN_S
        # 先排期、置好 _countdown_id，再刷新按钮，否则 _sync_buttons 会把
        # “待命 N…” 当成未倒计时、显示成“已停止”
        self._countdown_id = self.after(1000, self._countdown_tick)
        self._sync_buttons()           # 状态区显示 “待命 3…”
        self.logger.info("点击启动按钮：进入 %d 秒待命倒计时，候选目标 hwnd=%#x",
                         self.START_COUNTDOWN_S, self._prev_fg_hwnd)
        self.log(f"已进入 {self.START_COUNTDOWN_S} 秒待命倒计时，"
                 f"请把焦点切到目标窗口；再点一次「启动」可取消。")

    def _countdown_tick(self) -> None:
        self._countdown_id = None
        self._countdown_left -= 1
        if self._countdown_left <= 0:
            self._launch_after_countdown()
            return
        self._sync_buttons()           # 显示 “待命 2…” / “待命 1…”
        self._countdown_id = self.after(1000, self._countdown_tick)

    def _launch_after_countdown(self) -> None:
        self._countdown_id = None
        self._countdown_left = 0
        self._sync_buttons()
        target = self._prev_fg_hwnd
        if target and winutil.is_window(target):
            ok = winutil.activate(target)
            title = winutil.window_title(target) or "（无标题）"
            self.logger.info("倒计时结束：恢复焦点到 hwnd=%#x 标题=%r 成功=%s",
                             target, title, ok)
            self.log(f"已把焦点交还给“{title}”，随后启动。")
            # 存下 id：否则 on_close()/stop 无法取消它，会在窗口销毁后触发
            # "invalid command name ...start_script" 并泄漏定时器。
            self._relaunch_id = self.after(150, self._relaunch_start)
        else:
            self.logger.info("倒计时结束：没有捕获到候选目标窗口，直接启动"
                             "（按键将发送给当前活动窗口）")
            self.start_script()

    def _relaunch_start(self) -> None:
        """倒计时末尾 150ms 延迟启动的回调：先清 id 再真正启动（避免 id 悬空）。"""
        self._relaunch_id = None
        self.start_script()

    def _cancel_relaunch(self, reason: str) -> None:
        """取消倒计时末尾那个 150ms 延迟启动定时器（若有），并入日志。"""
        if self._relaunch_id is None:
            return
        try:
            self.after_cancel(self._relaunch_id)
        except tk.TclError:
            pass
        self._relaunch_id = None
        self.logger.info("已取消延迟启动: %s", reason)

    def _cancel_countdown(self, reason: str) -> bool:
        """取消进行中的待命倒计时（含倒计时末尾的延迟启动）。返回是否确有倒计时被取消。"""
        self._cancel_relaunch(reason)      # 末尾 150ms 的延迟启动也要一并撤掉
        if self._countdown_id is None:
            return False
        try:
            self.after_cancel(self._countdown_id)
        except tk.TclError:
            pass
        self._countdown_id = None
        self._countdown_left = 0
        self._sync_buttons()
        self.logger.info("待命倒计时已取消: %s", reason)
        self.log(f"已取消启动倒计时（{reason}）")
        return True

    def _track_foreground(self) -> None:
        """记住最近一个不属于本进程的前台窗口，作为待命倒计时的回焦目标。"""
        try:
            hwnd = winutil.foreground_hwnd()
            if not hwnd:
                return
            if winutil.window_pid(hwnd) == os.getpid():
                return
        except Exception as exc:
            self.logger.debug("前台窗口采样失败: %s", exc)
            return
        self._prev_fg_hwnd = hwnd

    def start_script(self) -> None:
        """立即启动（不倒数）。F1 走这里；待命倒计时结束也走这里。"""
        if self._countdown_id is not None:
            self._cancel_countdown("开始启动")
        if self.engine.is_running:
            self.logger.info("忽略启动请求: 已在运行")
            return
        if not self._check_elevation():
            return
        cfg = self._collect()
        if cfg is None:
            return
        self._save_settings()
        step = cfg.steps[0] if cfg.steps else {}
        self.logger.info("启动: 按键=%s 按住=%s 等待=%s 循环=%s 目标=%r",
                         step.get("key"), step.get("hold_ms"), step.get("delay_ms"),
                         cfg.cycles or "无限", cfg.target_title)
        if self.engine.start(cfg):
            self._sync_buttons()
        else:
            self.logger.warning("引擎拒绝启动（见上一条日志）")

    def _elevation_hwnd(self) -> int:
        """要做权限对比的窗口句柄。子类（迷你版）可改成前台窗口。"""
        title = self._target_title()
        return winutil.find_window(title) if title else 0

    def _check_elevation(self) -> bool:
        """目标窗口权限更高时提前提示，避免按键被静默丢弃。"""
        hwnd = self._elevation_hwnd()
        if not hwnd:
            return True
        title = winutil.window_title(hwnd) or "目标窗口"
        try:
            target = winutil.integrity_rank(
                winutil.process_integrity(winutil.window_pid(hwnd)))
            own = winutil.integrity_rank(winutil.own_integrity_level())
        except Exception as exc:
            self.logger.warning("权限检测失败，按放行处理: %s", exc)
            return True
        self.logger.debug("权限对比: 目标=%s(rank %s) 自身=%s(rank %s)",
                          title, target, winutil.own_integrity_level(), own)
        if target <= own:
            return True
        self.logger.warning("目标窗口权限更高，按键会被 Windows 丢弃: %r", title)
        if messagebox.askyesno(
                "需要管理员权限",
                f"窗口“{title}”以管理员身份运行，本工具没有。\n\n"
                "Windows 会丢弃发往该窗口的所有按键。\n\n"
                "是否以管理员身份重启本工具？（当前设置会保留）",
                parent=self):
            import instance
            ok, err = instance.relaunch_as_admin()
            if ok:
                self.logger.info("已发起提权重启")
                self.on_close()
            else:
                self.log(f"以管理员身份重启失败：{err}")
                messagebox.showerror("重启失败", err, parent=self)
        else:
            self.log("提示：该窗口权限更高，Windows 会拦截按键。建议以管理员身份运行。")
        return False

    def toggle_pause(self) -> None:
        if not self.engine.is_running:
            self.logger.info("忽略暂停请求: 未在运行")
            return
        paused = self.engine.toggle_pause()
        self.logger.info("暂停切换 -> %s", "已暂停" if paused else "已继续")
        self._sync_buttons()

    def stop_script(self) -> None:
        self._cancel_relaunch("停止了脚本")
        if self._cancel_countdown("停止了待命倒计时"):
            return
        if not self.engine.is_running:
            self.logger.info("忽略停止请求: 未在运行")
            return
        self.logger.info("停止")
        self.engine.stop(join=True)     # 按住已可中断，正常 10ms 量级即退出
        if self.engine.is_running:
            self.logger.warning("停止超时：线程仍在运行，强制松开已登记按键以防卡键")
            self.engine.force_release()
        self._sync_buttons()

    def capture_key(self) -> None:
        dlg = KeyCaptureDialog(self, "设置要按的键", allow_mouse=True)
        self.wait_window(dlg)
        if dlg.result:
            self.var_key.set(dlg.result)

    def _handle_action(self, action: str) -> None:
        self.logger.info("热键动作: %s", action)
        if action == "run_toggle":
            # F1 是在目标窗口里按的，焦点本来就对：取消任何待命倒计时后立即启动
            self._cancel_countdown("按下了启动热键 F1")
            self.start_script()
        elif action == "pause":
            if self._cancel_countdown("按下了暂停热键 F2"):
                return
            self.toggle_pause()
        elif action == "stop":
            self.stop_script()           # F3 停止（内部会先取消倒计时）
        elif action == "minimize":
            self._minimize()

    # ------------------------------------------------------------------ 同步 --
    def _sync_buttons(self) -> None:
        running = self.engine.is_running
        paused = self.engine.is_paused
        counting = self._countdown_id is not None
        self.btn_start.set_enabled(not running)
        if counting:
            self.btn_start.set_text("取消")     # 画板 1：待命态主按钮 = 取消
            self.btn_start.set_icon("close")
        else:
            self.btn_start.set_text("启动")
            self.btn_start.set_icon("play")
        self.btn_pause.set_enabled(running)
        self.btn_pause.set_text("继续" if paused else "暂停")
        self.btn_pause.set_icon("play" if paused else "pause")
        self.btn_stop.set_enabled(running)

        if counting:
            status, key = f"待命 {self._countdown_left}…", "countdown"
        elif running:
            status = "已暂停" if paused else "运行中"
            key = "paused" if paused else "running"
        else:
            status, key = "已停止", "stopped"
        self.var_status.set(status)
        self._fx_sync_state(key, status)

    # ------------------------------------------------------------------ 动效 --
    # 状态点语义色（画板 4 · 语义色区：只在状态点和状态文字上出现）
    _DOT_STATIC = {"stopped": "#71717A", "paused": "#F59E0B",
                   "countdown": "#F59E0B"}
    _DOT_BREATH = {"running": ("#10B981", "#34D399", 1300),
                   "countdown": ("#F59E0B", "#FBBF24", 500)}

    def _fx_sync_state(self, key: str, status: str | None = None) -> None:
        """状态变化时切换状态点动效与顶栏药丸；切换瞬间从白色脉冲一次。"""
        if status is not None and getattr(self, "pill", None) is not None:
            self.pill.set(text=status)
        dot_color = self._DOT_STATIC.get(key, "#71717A")
        if getattr(self, "pill", None) is not None:
            self.pill.set(dot=dot_color)
        if key == self._fx_state_key:
            return
        first = self._fx_state_key is None
        self._fx_state_key = key
        dot = self._fx_dot
        if first:                     # 首次同步不脉冲，直接就位
            dot.set_static(dot_color)
            return
        breath = self._DOT_BREATH.get(key)

        def settle():
            if breath:
                dot.breathe(*breath)
            else:
                dot.set_static(dot_color)

        dot.pulse("#FFFFFF", dot_color, 240, then=settle)

    def _poll(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        self._track_foreground()          # 每轮采样：记住候选目标窗口
        try:
            while True:
                kind, payload = self.q.get_nowait()
                try:
                    self._handle_message(kind, payload)
                except Exception:
                    # 单条消息失败只记日志，绝不拖垮整轮轮询
                    self.logger.exception("处理队列消息失败 kind=%s", kind)
        except queue.Empty:
            pass
        except Exception:
            self.logger.exception("轮询异常")
        finally:
            # 关键：重新武装放进 finally。任何 handler 抛异常都不会让
            # 轮询永久停摆（否则 F1/F2/F3 会静默失效且界面无任何提示）。
            try:
                if self.winfo_exists():
                    self._poll_id = self.after(self.POLL_MS, self._poll)
            except tk.TclError:
                pass

    def _handle_message(self, kind: str, payload) -> None:
        if kind == "log":
            self.log(payload)
        elif kind == "state":
            self.var_status.set(f"状态：{payload}")
        elif kind == "error":
            self.logger.error("引擎报错: %s", payload)
            self.log(f"错误：{payload}")
        elif kind == "action":
            self._handle_action(payload)
        elif kind == "finish":
            self._sync_buttons()

    # ------------------------------------------------------------------ 存档 --
    def _load_settings(self) -> dict:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return {}                     # 首次运行，正常情况
        except Exception as exc:
            self.logger.warning("读取设置失败，改用默认值: %s: %s",
                                type(exc).__name__, exc)
            return {}
        if not isinstance(data, dict):
            self.logger.warning("设置文件格式异常（不是对象），改用默认值")
            return {}
        return data

    def _extra_settings(self) -> dict:
        """子类（迷你版）可追加自己的存档字段。"""
        return {}

    def _save_settings(self) -> None:
        """排期合并写盘：SAVE_DEBOUNCE_MS 内的多次调用只落盘一次。

        初始化完成前（_settings_ready 为 False）只记脏、不写盘，避免把
        尚未定位的坐标写进存档（进程被强杀时会留下错误位置）。
        """
        self._settings_dirty = True
        if not self._settings_ready:
            return
        if self._flush_id is not None:
            return
        self._flush_id = self.after(self.SAVE_DEBOUNCE_MS, self._flush_settings)

    def _flush_settings(self) -> None:
        self._flush_id = None
        if not self._settings_ready:
            return
        self._write_settings()

    def _save_settings_now(self) -> None:
        """退出等时机强制立即落盘，保证设置不丢。"""
        if self._flush_id is not None:
            try:
                self.after_cancel(self._flush_id)
            except tk.TclError:
                pass
            self._flush_id = None
        if not self._settings_ready:
            return
        self._write_settings()

    def _write_settings(self) -> None:
        try:
            cycles = 0 if self.var_infinite.get() else int(self.var_cycles.get() or 1)
        except ValueError:
            cycles = 0
        data = {"key": self.var_key.get().strip(),
                "hold_ms": self.var_hold.get(),
                "delay_ms": self.var_delay.get(),
                "cycles": cycles,
                "target": self._target_title(),
                "theme": self._theme_name}
        data.update(self._extra_settings())
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            self._settings_dirty = False
        except Exception as exc:
            self.logger.error("保存设置失败: %s: %s", type(exc).__name__, exc)

    def on_close(self) -> None:
        self.logger.info("退出程序: 脚本运行中=%s", self.engine.is_running)
        # 动效定时器先撤，避免与销毁流程赛跑
        if getattr(self, "_fx_dot", None):
            self._fx_dot.stop()
        ui_fx.cancel_fade(self)
        self._cancel_relaunch("退出程序")   # 清掉末尾 150ms 延迟启动，防 after 泄漏
        self._cancel_countdown("退出程序")
        self._save_settings_now()          # 退出时强制立即落盘
        if self._poll_id:
            try:
                self.after_cancel(self._poll_id)
            except tk.TclError:
                pass
            self._poll_id = None
        try:
            self.engine.stop(join=True)
            if self.engine.is_running:
                self.logger.warning("退出时线程未能在超时内结束，强制松开已登记按键")
                self.engine.force_release()
            self.hotkeys.stop()
        except Exception as exc:
            self.logger.warning("退出清理失败: %s", exc)
        self.logger.info("已退出，日志结束")
        self.destroy()


def main() -> int:
    SimpleApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
