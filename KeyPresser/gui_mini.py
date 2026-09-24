"""迷你界面：左上角的紧凑浮动窗口，关掉不影响后台运行。

继承 SimpleApp —— 引擎、热键、轮询队列、配置存档、文件日志全部复用，只重画界面。

三个关键行为：
  * 窗口默认停**屏幕左上角**，位置会被记住。
  * **点 X = 隐藏到后台**，脚本继续跑（引擎在独立线程里，与窗口可见性无关）；
    按 **F4** 可以随时把窗口叫回来。要彻底退出请用窗口里的「退出程序」按钮。
  * 「打开日志」按钮直接打开日志目录，方便事后查 bug。

简化取舍：间隔只填一个数（总间隔），内部固定"按住 90ms"，
剩余部分算作"等待"，界面上会把拆分结果显式写出来，不做隐藏。

不提供目标窗口选择：按键发送给当前活动窗口（先用鼠标把焦点点到目标窗口，再按 F1）。
"""

import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk

import applog
import ui_fx
import ui_theme
import winutil
from gui_simple import ACTIVE_WINDOW, SimpleApp

# 迷你版的热键：在简洁版基础上多一个 F4 用来显示/隐藏窗口
MINI_HOTKEYS = {
    "run_toggle": "f1",        # 启动
    "pause": "f2",             # 暂停 / 继续
    "stop": "f3",              # 停止
    "toggle_window": "f4",     # 显示 / 隐藏本窗口
}

EXTRA_LABELS = {"toggle_window": "显示/隐藏窗口"}


class MiniApp(SimpleApp):
    TITLE = "自动按键工具 · 迷你"

    HOLD_FIXED = 90          # "按住"固定值（毫秒），只让用户填总间隔
    HINT_FG = "#0a7a3d"
    DIM_FG = "#888"
    MARGIN = 20              # 首次运行距屏幕左上角的边距
    FADE_MS = 120            # 显示/隐藏的淡入淡出时长

    # ------------------------------------------------------------------ 变量 --
    def _init_vars(self) -> None:
        super()._init_vars()
        self.var_interval = tk.StringVar(value=str(self._current_interval()))
        self.var_interval.trace_add("write", lambda *_: self._split_interval())
        self.var_top = tk.BooleanVar(value=bool(self._settings.get("topmost", True)))
        self.var_last = tk.StringVar(value="")
        self._hidden = False

    def _current_interval(self) -> int:
        try:
            return max(1, int(self.var_hold.get()) + int(self.var_delay.get()))
        except ValueError:
            return 1000

    def _split_interval(self) -> None:
        """把用户填的总间隔拆成「按住 + 等待」，写回引擎真正读的两个变量。"""
        try:
            total = max(1, int(self.var_interval.get()))
        except ValueError:
            return
        hold = min(self.HOLD_FIXED, total)
        self.var_hold.set(str(hold))
        self.var_delay.set(str(total - hold))

    # ------------------------------------------------------------------ 界面 --
    # 画板 3：单栏极简条 —— 只保留 运行状态 + 继续(启动/取消/暂停)/停止/放大/关闭
    BAR_W, BAR_H = 296, 40

    def _build_ui(self) -> None:
        t = self._theme = dict(ui_theme.DARK)    # 迷你条只有深色（画板 3）
        self.geometry(f"{self.BAR_W}x{self.BAR_H}")
        cv = self.cv = tk.Canvas(self, bg=t["card"], highlightthickness=0)
        cv.pack(fill="both", expand=True)
        ui_theme.rounded(cv, 1, 1, self.BAR_W - 1, self.BAR_H - 1, 10,
                         fill=t["card"], outline=t["border"])
        ui_theme.round_window(self)

        # 左区：状态点(8px) + 状态文字（画板 3 · 状态组）
        self.lbl_dot = tk.Label(cv, text="●", font=ui_theme.f_cn(9),
                                fg=t["dim"], bg=t["card"], bd=0)
        cv.create_window(16, self.BAR_H / 2, window=self.lbl_dot)
        self._fx_dot = ui_fx.Breath(self.lbl_dot)
        self.lbl_status = tk.Label(cv, textvariable=self.var_status,
                                   font=ui_theme.f_cn(12), fg=t["text1"],
                                   bg=t["card"], bd=0)
        cv.create_window(30, self.BAR_H / 2, window=self.lbl_status, anchor="w")

        # 右区（画板 3 · 右区：主按钮 / 停止 / 放大 / 关闭，间距 6，右边距 8）
        dim_icon = t["dim"]
        x = self.BAR_W - 8
        self.btn_close = ui_theme.RButton(
            cv, self.hide_window, backdrop=t["card"], icon="close",
            icon_size=12, radius=6, height=26, pad=(7, 7), fg=dim_icon,
            bg=t["card"], hover=ui_theme.mix(t["card"], "#FFFFFF", 0.06))
        x -= self.btn_close.px_width()
        cv.create_window(x, self.BAR_H / 2, window=self.btn_close, anchor="w")
        x -= 6
        self.btn_expand = ui_theme.RButton(
            cv, self._switch_to_simple, backdrop=t["card"], icon="max",
            icon_size=13, radius=6, height=26, pad=(6, 6), fg=dim_icon,
            bg=t["card"], hover=ui_theme.mix(t["card"], "#FFFFFF", 0.06))
        x -= self.btn_expand.px_width()
        cv.create_window(x, self.BAR_H / 2, window=self.btn_expand, anchor="w")
        x -= 6
        self.btn_stop = ui_theme.RButton(
            cv, self.stop_script, backdrop=t["card"], text="停止",
            font=ui_theme.f_cn(12), fg="#FFFFFF", bg=t["fill3"], radius=6,
            height=28, icon="stop", icon_size=11, pad=(10, 10), gap=5,
            disabled={"bg": t["fill3"], "fg": t["ghost"], "border": None})
        x -= self.btn_stop.px_width()
        cv.create_window(x, self.BAR_H / 2, window=self.btn_stop, anchor="w")
        x -= 6
        self.btn_main = ui_theme.RButton(
            cv, self.on_start_button, backdrop=t["card"], text="启动",
            font=ui_theme.f_cn(12), fg="#FFFFFF", bg=t["accent"], radius=6,
            height=28, icon="play", icon_size=13, pad=(10, 10), gap=5,
            hover=ui_theme.mix(t["accent"], "#FFFFFF", 0.1))
        cv.create_window(x - self.btn_main.px_width(), self.BAR_H / 2,
                         window=self.btn_main, anchor="w")

        ui_theme.enable_drag(self, cv, self.lbl_status, self.lbl_dot)
        # 右键菜单：设计稿砍掉的「打开日志 / 退出程序」收进这里，不占视觉
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="打开日志", command=self.open_logs)
        self._menu.add_command(label="退出程序", command=self.on_close)
        for w in (cv, self.lbl_status, self.lbl_dot):
            w.bind("<Button-3>",
                   lambda e: self._menu.tk_popup(e.x_root, e.y_root))

    def _switch_to_simple(self) -> None:
        """放大 = 回主界面：延迟 0.3s 新起简洁版进程（等互斥体释放），本窗口退出。"""
        if getattr(sys, "frozen", False):
            cmd = [sys.executable]
            cwd = str(Path(sys.executable).parent)
        else:
            py = Path(sys.executable).with_name("pythonw.exe")
            script = Path(sys.argv[0]).resolve()
            cmd = [str(py if py.exists() else sys.executable), str(script)]
            cwd = str(script.parent)
        threading.Timer(0.3, lambda: subprocess.Popen(cmd, cwd=cwd),
                        daemon=True).start()
        self.on_close()

    # -------------------------------------------------------------- 生命周期 --
    def __init__(self):
        super().__init__()
        # 点 X 只隐藏，不退出 —— 覆盖父类绑定的"真正退出"
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self._apply_topmost()
        self._restore_pos()
        self._mark_settings_ready()      # 定位完成，此后才允许落盘（修正存档坐标）

    def _needs_own_init(self) -> bool:
        """迷你版在 super().__init__ 之后还有置顶 / 定位步骤，故延迟允许落盘。"""
        return True

    def _apply_topmost(self) -> None:
        try:
            self.attributes("-topmost", bool(self.var_top.get()))
        except tk.TclError:
            pass
        self.logger.info("窗口置顶: %s", bool(self.var_top.get()))
        self._save_settings()            # 切换后即时落盘（经 debounce 合并）

    def _restore_pos(self) -> None:
        """回到上次的位置；首次运行放在屏幕**左上角**。"""
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        pos = self._settings.get("pos")
        x, y = self.MARGIN, self.MARGIN
        if isinstance(pos, list) and len(pos) == 2:
            try:
                x = max(0, min(int(pos[0]), max(0, sw - w)))
                y = max(0, min(int(pos[1]), max(0, sh - h)))
            except (TypeError, ValueError):
                x, y = self.MARGIN, self.MARGIN
        self.geometry(f"+{x}+{y}")
        self.logger.info("窗口位置: (%d, %d) 尺寸 %dx%d", x, y, w, h)

    # -------------------------------------------------------- 隐藏 / 显示 --
    def hide_window(self) -> None:
        """隐藏窗口但保持后台运行 —— 脚本不受影响。先淡出再撤窗。"""
        self._save_settings()
        self._hidden = True
        self.logger.info("窗口已隐藏到后台（脚本运行中=%s），按 F4 可重新显示",
                         self.engine.is_running)
        ui_fx.fade(self, 1.0, 0.0, self.FADE_MS, on_done=self.withdraw)

    def show_window(self) -> None:
        ui_fx.cancel_fade(self)          # 淡出途中被唤回：掐掉旧链再淡入
        self._hidden = False
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self.deiconify()
        self._apply_topmost()
        self.lift()
        try:
            self.focus_force()
        except tk.TclError:
            pass
        ui_fx.fade(self, 0.0, 1.0, self.FADE_MS)
        self.logger.info("窗口已显示")

    def toggle_window(self) -> None:
        if self._hidden:
            self.show_window()
        else:
            self.hide_window()

    def open_logs(self) -> None:
        path = applog.open_log_folder(self.logger)
        self.log(f"日志目录：{path}")

    # -------------------------------------------------------------- 行为覆盖 --
    def _hotkey_bindings(self) -> dict:
        return dict(MINI_HOTKEYS)

    def _hotkey_label(self, action: str) -> str:
        return EXTRA_LABELS.get(action, super()._hotkey_label(action))

    def _handle_action(self, action: str) -> None:
        if action == "toggle_window":
            self.logger.info("热键动作: toggle_window")
            self.toggle_window()
        else:
            super()._handle_action(action)

    def _target_title(self) -> str:
        """迷你版不提供目标窗口选择，一律发送给当前活动窗口。"""
        return ""

    def refresh_windows(self) -> None:
        """迷你版没有窗口下拉框；同时保留已存的 target 设置，不覆盖掉。"""
        self._win_titles = []

    def _elevation_hwnd(self) -> int:
        """迷你版没有目标窗口设置，就检查按下 F1 时的前台窗口。

        用户是"在目标窗口里按 F1"的，所以此刻的前台窗口就是他要操作的那个。
        """
        return winutil.foreground_hwnd()

    def _refresh_hints(self) -> None:
        super()._refresh_hints()
        try:
            hold = int(self.var_hold.get())
            delay = int(self.var_delay.get())
            self.var_gap.set(f"按住 {hold} + 等待 {delay} 毫秒")
        except ValueError:
            self.var_gap.set("间隔必须填数字")

    def _sync_buttons(self) -> None:
        running = self.engine.is_running
        paused = self.engine.is_paused
        counting = self._countdown_id is not None
        if counting:
            main, stop_on = ("close", "取消"), False
            status, key = f"待命 {self._countdown_left}…", "countdown"
        elif running:
            stop_on = True
            if paused:
                main, status, key = ("play", "继续"), "已暂停", "paused"
            else:
                main, status, key = ("pause", "暂停"), "运行中", "running"
        else:
            main, stop_on = ("play", "启动"), False
            status, key = "已停止", "stopped"
        self.btn_main.set_icon(main[0])
        self.btn_main.set_text(main[1])
        self.btn_stop.set_enabled(stop_on)
        self.var_status.set(status)
        self._fx_sync_state(key)

    def log(self, msg: str) -> None:
        """迷你版不放日志框：写进文件，并把最后一条压成一行显示。"""
        text = str(msg)
        self.logger.info("%s", text)
        flat = " ".join(text.split())
        self.var_last.set(flat if len(flat) <= 46 else flat[:45] + "…")

    def _extra_settings(self) -> dict:
        try:
            pos = [self.winfo_x(), self.winfo_y()]
        except tk.TclError:
            pos = None
        # target 由 _target_title() 置空，这里把原值放回去，免得覆盖简洁版的设置
        saved_target = self.var_target.get()
        return {"topmost": bool(self.var_top.get()), "pos": pos,
                "target": "" if saved_target == ACTIVE_WINDOW else saved_target}


def main() -> int:
    MiniApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
