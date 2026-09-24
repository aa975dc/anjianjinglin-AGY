"""GUI приложения KeyPresser (tkinter/ttk).

Все подписи идут через i18n.t(). Переключение языка пересобирает виджеты:
tk-переменные живут отдельно от виджетов, поэтому значения полей и состояние
списка шагов при пересборке сохраняются.
"""

import queue
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import applog
import engine as eng
import i18n
import keys
import profiles
import recorder as rec_mod
import sender
import version
import winutil
from hotkeys import HotkeyManager
from i18n import t

ACTION_KEYS = ("tap", "down", "up")
MODE_ORDER = (eng.MODE_FOREGROUND, eng.MODE_ACTIVATE, eng.MODE_POST)
MODE_LABEL_KEYS = {eng.MODE_FOREGROUND: "mode.foreground",
                   eng.MODE_ACTIVATE: "mode.activate",
                   eng.MODE_POST: "mode.post"}


class KeyCaptureDialog(tk.Toplevel):
    """Модальное окно: ловит физическую клавишу/комбинацию.

    Читаем event.keycode -- это virtual-key код, одинаковый для позиции клавиши
    в US и русской раскладке, поэтому захват не зависит от раскладки.
    """

    GHOST_MS = 40      # окно, в котором Ctrl считается фантомом от AltGr

    def __init__(self, master, title: str, allow_mouse: bool = False,
                 allow_modifier_only: bool = True):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.result: str | None = None
        self._held: list[str] = []
        self._down_ms: dict[str, int] = {}
        self._allow_modifier_only = allow_modifier_only
        self.transient(master)

        hint = t("dlg.hint")
        if allow_modifier_only:
            hint += "\n" + t("dlg.hint_modifier")
        if allow_mouse:
            hint += "\n" + t("dlg.hint_mouse")
        self._label = ttk.Label(self, text=hint, padding=18, anchor="center",
                                justify="center")
        self._label.pack(fill="both", expand=True)
        self._echo = ttk.Label(self, text="—", anchor="center",
                               font=("Segoe UI", 11, "bold"))
        self._echo.pack(fill="x", pady=(0, 6))
        ttk.Button(self, text=t("dlg.cancel"), command=self._cancel).pack(pady=(0, 10))

        self.bind("<KeyPress>", self._on_down)
        self.bind("<KeyRelease>", self._on_up)
        if allow_mouse:
            for num, name in ((1, "mouse_left"), (2, "mouse_middle"), (3, "mouse_right")):
                self._label.bind(f"<Button-{num}>", lambda _e, n=name: self._finish(n))
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        self.focus_force()

    def _name_of(self, event) -> str | None:
        name = keys.name_from_vk(event.keycode)
        if name:
            return name
        # неизвестная клавиша -- запомним сырым VK-кодом, воспроизведение это умеет
        return f"vk:0x{event.keycode:02x}" if event.keycode else None

    def _on_down(self, event):
        name = self._name_of(event)
        if not name:
            self._echo.config(text=t("dlg.unknown", vk=event.keycode))
            return "break"
        if name in keys.MODIFIER_NAMES:
            if name == "ralt":
                # Windows подмешивает к правому Alt фантомный левый Ctrl (AltGr)
                ghost = self._down_ms.get("lctrl")
                if ghost is not None and abs(event.time - ghost) <= self.GHOST_MS:
                    if "lctrl" in self._held:
                        self._held.remove("lctrl")
                    self._down_ms.pop("lctrl", None)   # не оставлять грязный _down_ms
            if name not in self._held:
                self._held.append(name)
                self._down_ms[name] = event.time
            tail = "" if self._allow_modifier_only else " + ..."
            self._echo.config(text=" + ".join(self._held) + tail)
            return "break"
        self._finish(keys.format_combo(self._held, name))
        return "break"

    def _on_up(self, event):
        name = self._name_of(event)
        if name not in self._held:
            return "break"
        self._held.remove(name)
        self._down_ms.pop(name, None)
        if self._allow_modifier_only:
            # отпустили модификатор, других клавиш не было -> это и есть результат
            self._finish(keys.format_combo(self._held, name))
        elif not self._held:
            self._echo.config(text=t("dlg.mod_not_hotkey"))
        return "break"

    def _finish(self, combo: str):
        self.result = combo
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()


class SelfTestWindow(tk.Toplevel):
    """Отправляет последовательность в собственное окно и показывает, что дошло.

    Окно без рамки специально: у окна с заголовком одиночный Alt открывает
    системное меню и вешает цикл сообщений. Перед каждым нажатием проверяется,
    что активно именно это окно -- иначе нажатия ушли бы в чужое окно.
    """

    STEP_GAP_MS = 160

    def __init__(self, master, steps: list[dict]):
        super().__init__(master)
        self.steps = steps
        self.got: list[str] = []
        self.overrideredirect(True)
        self.configure(padx=16, pady=14)
        self.transient(master)

        ttk.Label(self, text=t("selftest.title"), font=("Segoe UI", 12, "bold")).pack()
        ttk.Label(self, text=t("selftest.hint"), justify="center").pack(pady=(4, 8))
        self.lbl_now = ttk.Label(self, text="", foreground="#0a6")
        self.lbl_now.pack()
        self.lbl_got = ttk.Label(self, text=t("selftest.got", n=0, list="—"),
                                 wraplength=460, justify="center",
                                 font=("Segoe UI", 10, "bold"))
        self.lbl_got.pack(pady=(6, 8))
        self.btn_close = ttk.Button(self, text=t("selftest.close"), command=self.destroy)
        self.btn_close.pack()

        self.bind("<KeyPress>", self._on_key)
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.lift()
        self._hwnd = winutil.root_hwnd(self.winfo_id())
        winutil.activate(self._hwnd)
        self.focus_force()
        self.after(300, self._fire, 0)

    def _on_key(self, event):
        name = keys.name_from_vk(event.keycode) or f"vk:0x{event.keycode:02x}"
        self.got.append(name)
        self.lbl_got.config(text=t("selftest.got", n=len(self.got),
                                   list=", ".join(self.got)))
        return "break"

    def _fire(self, i: int) -> None:
        if not self.winfo_exists():
            return
        if i >= len(self.steps):
            self.lbl_now.config(text=t("selftest.done"))
            if not self.got:
                self.lbl_got.config(text=t("selftest.none"), foreground="#c00")
            return
        if not winutil.is_foreground(self._hwnd):
            # фокус ушёл -- прекращаем, чтобы не сыпать нажатия в чужое окно
            self.lbl_now.config(text=t("diag.target_not_fg"), foreground="#c00")
            return
        step = self.steps[i]
        self.lbl_now.config(text=t("selftest.sending",
                                   key=keys.describe_combo(step["key"])))
        try:
            mods, main = keys.parse_combo(step["key"])
            sender.tap(mods, main, int(step.get("hold_ms", 40)))
        except Exception as exc:
            self.lbl_now.config(text=str(exc), foreground="#c00")
            return
        self.after(self.STEP_GAP_MS, self._fire, i + 1)


class App(tk.Tk):
    POLL_MS = 60

    def __init__(self):
        super().__init__()
        self.q: queue.Queue = queue.Queue()
        self.logger = applog.get("full")
        self.cfg = profiles.load_settings()
        i18n.set_language(self.cfg.get("language", i18n.DEFAULT_LANGUAGE))
        self.steps: list[dict] = list(self.cfg["steps"])
        self.profile_path: Path | None = None
        self.window_map: dict[str, dict] = {}
        self.own_level = winutil.own_integrity_level()
        self._log_buffer: list[str] = []
        self._active_step: int | None = None
        self._syncing = False        # True -> поля заполняем сами, это не правка шага

        self.title(self._window_title())
        self.minsize(920, 780)
        self.geometry("980x880")

        self.engine = eng.Engine(
            on_log=lambda m: self.q.put(("log", m)),
            on_state=lambda s: self.q.put(("state", s)),
            on_step=lambda i: self.q.put(("step", i)),
            on_finish=lambda: self.q.put(("finish", None)),
            on_error=lambda m: self.q.put(("error", m)),
        )
        self.recorder = rec_mod.Recorder(
            on_event=lambda n, d, c: self.q.put(("rec", (n, d, c))),
            on_error=lambda m: self.q.put(("log", t("rec.prefix", msg=m))),
        )
        self.hotkeys = HotkeyManager(
            on_action=lambda a: self.q.put(("action", a)),
            on_error=lambda m: self.q.put(("log", t("hk.prefix", msg=m))),
        )

        self._init_vars()
        self._build_ui()
        self.refresh_windows()
        self.refresh_tree()
        self.apply_hotkeys(quiet=True)

        self.log(f"KeyPresser {t('app.version', v=version.VERSION)} "
                 f"({version.BUILT_AT})")
        if not winutil.is_admin():
            self.log(t("msg.admin_hint"))
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._poll_id = self.after(self.POLL_MS, self._poll)

    # ------------------------------------------------------- переменные ----
    def _init_vars(self) -> None:
        """tk-переменные создаются один раз и переживают пересборку виджетов."""
        cfg = self.cfg
        self.var_lang = tk.StringVar(value=i18n.LANGUAGES[i18n.language()])
        self.var_window = tk.StringVar()
        self.var_mode = tk.StringVar(value=cfg["mode"])
        self.var_key = tk.StringVar(value="space")
        self.var_action = tk.StringVar(value=t("action.tap"))
        self._action_key = "tap"
        self.var_hold = tk.IntVar(value=90)   # короче ~50 мс игры теряют тап
        self.var_delay = tk.IntVar(value=500)
        self.var_repeat = tk.IntVar(value=1)
        self.var_comment = tk.StringVar()
        self.var_rec_mouse = tk.BooleanVar(value=cfg["record_mouse"])
        self.var_rec_replace = tk.BooleanVar(value=cfg["record_replace"])
        self.var_rec_tail = tk.IntVar(value=cfg["record_tail_delay_ms"])
        self.var_cycles = tk.IntVar(value=cfg["cycles"])
        self.var_cycle_delay = tk.IntVar(value=cfg["cycle_delay_ms"])
        self.var_jitter = tk.IntVar(value=cfg["jitter_pct"])
        self.var_start_delay = tk.IntVar(value=cfg["start_delay_ms"])
        self.var_status = tk.StringVar(value=t("status.ready"))
        self.var_hk = {a: tk.StringVar(value=cfg["hotkeys"].get(a, d))
                       for a, d in profiles.DEFAULT_HOTKEYS.items()}
        self.var_key.trace_add("write", lambda *_: self._update_key_preview())
        for var in (self.var_key, self.var_action, self.var_hold, self.var_delay,
                    self.var_repeat, self.var_comment):
            var.trace_add("write", self._on_editor_changed)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        self._syncing = True
        try:
            self._build_widgets()
        finally:
            self._syncing = False

    def _build_widgets(self) -> None:
        self._build_menu()
        root = ttk.Frame(self, padding=8)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=3)
        root.rowconfigure(7, weight=2)

        self._build_topbar(root, row=0)
        self._build_target(root, row=1)
        self._build_sequence(root, row=2)
        self._build_editor(root, row=3)
        self._build_record(root, row=4)
        self._build_loop_and_hotkeys(root, row=5)
        self._build_controls(root, row=6)
        self._build_log(root, row=7)
        self._update_key_preview()
        self._sync_run_buttons()
        self._sync_record_ui()
        for line in self._log_buffer:
            self._append_log(line)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        m_prof = tk.Menu(menubar, tearoff=0)
        m_prof.add_command(label=t("menu.new"), command=self.profile_new)
        m_prof.add_command(label=t("menu.open"), command=self.profile_open)
        m_prof.add_command(label=t("menu.save"), command=self.profile_save)
        m_prof.add_command(label=t("menu.save_as"), command=self.profile_save_as)
        m_prof.add_separator()
        m_prof.add_command(label=t("menu.exit"), command=self.on_close)
        menubar.add_cascade(label=t("menu.profile"), menu=m_prof)

        m_lang = tk.Menu(menubar, tearoff=0)
        for code, name in i18n.LANGUAGES.items():
            m_lang.add_radiobutton(label=name, value=name, variable=self.var_lang,
                                   command=lambda c=code: self.set_language(c))
        menubar.add_cascade(label=t("menu.language"), menu=m_lang)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label=t("menu.how"), command=self.show_help)
        menubar.add_cascade(label=t("menu.help"), menu=m_help)
        self.config(menu=menubar)

    def _build_topbar(self, parent, row: int) -> None:
        bar = ttk.Frame(parent)
        bar.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        bar.columnconfigure(0, weight=1)
        ttk.Label(bar, text=t("lang.label")).grid(row=0, column=1, sticky="e")
        cmb = ttk.Combobox(bar, textvariable=self.var_lang, state="readonly", width=12,
                           values=list(i18n.LANGUAGES.values()))
        cmb.grid(row=0, column=2, sticky="e", padx=(4, 0))
        cmb.bind("<<ComboboxSelected>>", self._on_lang_combo)

    def _build_target(self, parent, row: int) -> None:
        frm = ttk.LabelFrame(parent, text=t("target.frame"), padding=8)
        frm.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text=t("target.window")).grid(row=0, column=0, sticky="w")
        self.cmb_window = ttk.Combobox(frm, textvariable=self.var_window, state="readonly")
        self.cmb_window.grid(row=0, column=1, sticky="ew", padx=6)
        self.cmb_window.bind("<<ComboboxSelected>>", self.on_window_selected)
        ttk.Button(frm, text=t("target.refresh"), width=12,
                   command=self.refresh_windows).grid(row=0, column=2)
        ttk.Button(frm, text=t("target.grab"), width=24,
                   command=self.grab_foreground).grid(row=0, column=3, padx=(6, 0))

        modes = ttk.Frame(frm)
        modes.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
        for i, mode in enumerate(MODE_ORDER):
            ttk.Radiobutton(modes, text=t(MODE_LABEL_KEYS[mode]), value=mode,
                            variable=self.var_mode).grid(row=i, column=0, sticky="w")

    def _build_sequence(self, parent, row: int) -> None:
        frm = ttk.LabelFrame(parent, text=t("seq.frame"), padding=8)
        frm.grid(row=row, column=0, sticky="nsew", pady=(0, 6))
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0, weight=1)

        cols = ("n", "key", "act", "hold", "delay", "rep", "on", "cm")
        widths = {"n": 36, "key": 235, "act": 90, "hold": 84, "delay": 118,
                  "rep": 62, "on": 46, "cm": 180}
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=t(f"col.{c}"))
            self.tree.column(c, width=widths[c],
                             anchor="w" if c in ("key", "cm") else "center",
                             stretch=(c == "cm"))
        self.tree.tag_configure("off", foreground="#888888")
        self.tree.tag_configure("active", background="#d7f0d7")
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", lambda _e: self.toggle_enabled())

        side = ttk.Frame(frm)
        side.grid(row=0, column=2, sticky="ns", padx=(8, 0))
        for key, cmd in (("btn.up", self.move_up), ("btn.down", self.move_down),
                         ("btn.dup", self.duplicate_step),
                         ("btn.toggle", self.toggle_enabled),
                         ("btn.delete", self.delete_step),
                         ("btn.clear", self.clear_steps)):
            ttk.Button(side, text=t(key), width=15, command=cmd).pack(pady=2)

    def _build_editor(self, parent, row: int) -> None:
        frm = ttk.LabelFrame(parent, text=t("step.frame"), padding=8)
        frm.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text=t("step.key")).grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_key, width=18).grid(
            row=0, column=1, sticky="ew", padx=(4, 4))
        ttk.Button(frm, text=t("step.capture"), width=20,
                   command=self.capture_step_key).grid(row=0, column=2)

        ttk.Label(frm, text=t("step.action")).grid(row=0, column=3, sticky="e", padx=(10, 2))
        self.var_action.set(t(f"action.{self._action_key}"))
        ttk.Combobox(frm, textvariable=self.var_action, state="readonly", width=12,
                     values=[t(f"action.{a}") for a in ACTION_KEYS]).grid(row=0, column=4)

        for col, (label_key, var, hi) in enumerate([
                ("step.hold", self.var_hold, profiles.HOLD_MS_RANGE[1]),
                ("step.delay", self.var_delay, 3600000),
                ("step.repeat", self.var_repeat, 100000)], start=5):
            box = ttk.Frame(frm)
            box.grid(row=0, column=col, padx=(10, 0))
            ttk.Label(box, text=t(label_key)).pack(side="left", padx=(0, 3))
            ttk.Spinbox(box, from_=0, to=hi, textvariable=var, width=7).pack(side="left")

        ttk.Label(frm, text=t("step.comment")).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(frm, textvariable=self.var_comment).grid(
            row=1, column=1, columnspan=4, sticky="ew", padx=(4, 4), pady=(6, 0))
        ttk.Button(frm, text=t("step.add"), width=16, command=self.add_step).grid(
            row=1, column=5, pady=(6, 0), padx=(10, 0))
        ttk.Button(frm, text=t("step.apply"), width=24, command=self.apply_step).grid(
            row=1, column=6, columnspan=2, pady=(6, 0), padx=(6, 0))
        self.lbl_key_preview = ttk.Label(frm, text="", foreground="#0a6")
        self.lbl_key_preview.grid(row=2, column=0, columnspan=8, sticky="w", pady=(6, 0))

    def _build_record(self, parent, row: int) -> None:
        frm = ttk.LabelFrame(parent, text=t("rec.frame"), padding=8)
        frm.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        frm.columnconfigure(6, weight=1)

        self.btn_record = ttk.Button(frm, text="● " + t("rec.start"), width=22,
                                     command=self.toggle_record)
        self.btn_record.grid(row=0, column=0)
        ttk.Checkbutton(frm, text=t("rec.mouse"), variable=self.var_rec_mouse).grid(
            row=0, column=1, padx=(10, 0))
        ttk.Checkbutton(frm, text=t("rec.replace"), variable=self.var_rec_replace).grid(
            row=0, column=2, padx=(10, 0))
        ttk.Label(frm, text=t("rec.tail")).grid(row=0, column=3, padx=(10, 2))
        ttk.Spinbox(frm, from_=0, to=600000, textvariable=self.var_rec_tail,
                    width=8).grid(row=0, column=4)
        self.lbl_rec = ttk.Label(frm, text=t("rec.off"), foreground="#666")
        self.lbl_rec.grid(row=0, column=6, sticky="e")

    def _build_loop_and_hotkeys(self, parent, row: int) -> None:
        wrap = ttk.Frame(parent)
        wrap.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        wrap.columnconfigure(0, weight=1)
        wrap.columnconfigure(1, weight=1)

        loop = ttk.LabelFrame(wrap, text=t("loop.frame"), padding=8)
        loop.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        rows = [("loop.cycles", self.var_cycles, 1_000_000),
                ("loop.cycle_delay", self.var_cycle_delay, 3_600_000),
                ("loop.jitter", self.var_jitter, 90),
                ("loop.start_delay", self.var_start_delay, 60_000)]
        for i, (label_key, var, hi) in enumerate(rows):
            ttk.Label(loop, text=t(label_key)).grid(row=i, column=0, sticky="w", pady=1)
            ttk.Spinbox(loop, from_=0, to=hi, textvariable=var, width=10).grid(
                row=i, column=1, sticky="w", padx=(6, 0))

        hk = ttk.LabelFrame(wrap, text=t("hk.frame"), padding=8)
        hk.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        hk.columnconfigure(1, weight=1)
        for i, action in enumerate(profiles.DEFAULT_HOTKEYS):
            ttk.Label(hk, text=profiles.hotkey_label(action) + ":").grid(
                row=i, column=0, sticky="w", pady=1)
            ttk.Entry(hk, textvariable=self.var_hk[action], width=14).grid(
                row=i, column=1, sticky="ew", padx=4)
            ttk.Button(hk, text=t("hk.set"), width=9,
                       command=lambda a=action: self.capture_hotkey(a)).grid(row=i, column=2)
        ttk.Button(hk, text=t("hk.apply"), command=self.apply_hotkeys).grid(
            row=len(profiles.DEFAULT_HOTKEYS), column=0, columnspan=3,
            sticky="ew", pady=(6, 0))

    def _build_controls(self, parent, row: int) -> None:
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        frm.columnconfigure(3, weight=1)
        ttk.Button(frm, text=t("diag.button"), width=22,
                   command=self.run_diagnostics).grid(row=1, column=0, pady=(6, 0))
        ttk.Button(frm, text=t("selftest.button"), width=22,
                   command=self.open_selftest).grid(row=1, column=1, pady=(6, 0), padx=6)
        # 一键最小化：省得把鼠标移到标题栏去找 — 按钮
        ttk.Button(frm, text=t("ctl.minimize"), width=22,
                   command=self.iconify).grid(row=1, column=2, pady=(6, 0))
        self.btn_start = ttk.Button(frm, text="▶ " + t("ctl.start"), width=16,
                                    command=self.start_script)
        self.btn_start.grid(row=0, column=0)
        self.btn_pause = ttk.Button(frm, text="‖ " + t("ctl.pause"), width=16,
                                    command=self.toggle_pause)
        self.btn_pause.grid(row=0, column=1, padx=6)
        self.btn_stop = ttk.Button(frm, text="■ " + t("ctl.stop"), width=16,
                                   command=self.stop_script)
        self.btn_stop.grid(row=0, column=2)
        ttk.Label(frm, textvariable=self.var_status,
                  font=("Segoe UI", 10, "bold")).grid(row=0, column=3, sticky="e")

    def _build_log(self, parent, row: int) -> None:
        frm = ttk.LabelFrame(parent, text=t("log.frame"), padding=6)
        frm.grid(row=row, column=0, sticky="nsew")
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0, weight=1)
        self.txt_log = tk.Text(frm, height=8, wrap="word", state="disabled")
        self.txt_log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(frm, orient="vertical", command=self.txt_log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.txt_log.configure(yscrollcommand=sb.set)

    # ---------------------------------------------------------- язык -------
    def _on_lang_combo(self, _event=None) -> None:
        name = self.var_lang.get()
        code = next((c for c, n in i18n.LANGUAGES.items() if n == name), None)
        if code:
            self.set_language(code)

    def set_language(self, code: str) -> None:
        if code == i18n.language():
            return
        self._action_key = self.current_action_key()
        i18n.set_language(code)
        self.var_lang.set(i18n.LANGUAGES[i18n.language()])
        self.rebuild_ui()
        self.log(t("lang.changed", name=i18n.LANGUAGES[code]))

    def rebuild_ui(self) -> None:
        """Пересобрать виджеты под новый язык, сохранив состояние."""
        selected = self.selected_index()
        window_label = self.var_window.get()
        self.title(self._window_title())
        for child in list(self.winfo_children()):
            child.destroy()
        self._build_ui()
        self.refresh_windows(keep=window_label)
        self.refresh_tree(select=selected, active=self._active_step)
        if not self.engine.is_running and not self.recorder.is_recording:
            self.var_status.set(t("status.ready"))

    # -------------------------------------------------------- helpers ------
    def log(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self._log_buffer.append(line)
        del self._log_buffer[:-300]
        self._append_log(line)

    def _append_log(self, line: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", line + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def current_action_key(self) -> str:
        label = self.var_action.get()
        return next((a for a in ACTION_KEYS if t(f"action.{a}") == label), "tap")

    def _update_key_preview(self) -> None:
        if not hasattr(self, "lbl_key_preview"):
            return
        spec = self.var_key.get().strip()
        if not spec:
            self.lbl_key_preview.config(text="", foreground="#0a6")
            return
        try:
            keys.parse_combo(spec)
        except Exception as exc:
            self.lbl_key_preview.config(text=t("preview.err", err=exc), foreground="#c00")
            return
        self.lbl_key_preview.config(
            text=t("preview.ok", desc=keys.describe_combo(spec)), foreground="#0a6")

    def _sync_run_buttons(self) -> None:
        running = self.engine.is_running
        self.btn_start.config(state="disabled" if running else "normal")
        self.btn_pause.config(
            state="normal" if running else "disabled",
            text=("▶ " + t("ctl.resume")) if self.engine.is_paused
            else ("‖ " + t("ctl.pause")))
        self.btn_stop.config(state="normal" if running else "disabled")

    def _sync_record_ui(self) -> None:
        if self.recorder.is_recording:
            self.btn_record.config(text="■ " + t("rec.stop"))
            self.lbl_rec.config(text=t("rec.on"), foreground="#c00")
        else:
            self.btn_record.config(text="● " + t("rec.start"))
            self.lbl_rec.config(text=t("rec.off"), foreground="#666")

    def _window_title(self, profile: str = "") -> str:
        base = f"{t('app.title')} {version.VERSION}"
        return f"{base} — {profile}" if profile else base

    def _own_hwnd(self) -> int:
        return winutil.root_hwnd(self.winfo_id())

    def _window_label(self, hwnd: int, title: str) -> tuple[str, dict]:
        """Подпись для списка + сведения об окне. Права игры видно сразу в списке."""
        level = winutil.process_integrity(winutil.window_pid(hwnd))
        elevated = winutil.integrity_rank(level) > winutil.integrity_rank(self.own_level)
        mark = f"   [{t('target.admin_mark')}]" if elevated else ""
        label = f"{title}{mark}   [hwnd {hwnd:#x}]"
        return label, {"hwnd": hwnd, "title": title, "level": level,
                       "elevated": elevated}

    def refresh_windows(self, keep: str | None = None) -> None:
        self.own_level = winutil.own_integrity_level()
        self.window_map = {}
        items = []
        own = self._own_hwnd()
        for hwnd, title in winutil.list_windows():
            if hwnd == own:                     # себя целью выбирать незачем
                continue
            label, info = self._window_label(hwnd, title)
            self.window_map[label] = info
            items.append(label)
        none_label = t("target.none")
        self.cmb_window["values"] = [none_label] + items
        wanted = keep or self.var_window.get() or ""
        if wanted in items:
            self.var_window.set(wanted)
            return
        current = self.cfg.get("target_title", "")
        match = next((i for i in items if current and current.lower() in i.lower()), None)
        self.var_window.set(match or none_label)

    def target_info(self) -> dict | None:
        """Сведения о выбранном окне или None, если цель не выбрана."""
        return self.window_map.get(self.var_window.get())

    def on_window_selected(self, _event=None) -> None:
        """Выбрали окно с правами выше наших -- сразу предлагаем перезапуск."""
        info = self.target_info()
        if info and info["elevated"]:
            self.offer_elevation(info)

    def offer_elevation(self, info: dict) -> bool:
        """True -- перезапуск запущен (это окно скоро закроется)."""
        if messagebox.askyesno(
                t("admin.ask_title"),
                t("admin.ask", title=info["title"], level=info["level"],
                  own=self.own_level),
                parent=self):
            return self.restart_as_admin()
        self.log(t("admin.declined", title=info["title"]))
        return False

    def restart_as_admin(self) -> bool:
        """Сохранить состояние, поднять себя через UAC и уйти."""
        import instance

        self.log(t("admin.restarting"))
        self.update_idletasks()
        profiles.save_settings(self._ui_to_cfg())      # состояние переедет в новый процесс
        self.engine.stop(join=True)
        if self.recorder.is_recording:
            self.recorder.stop()
        self.hotkeys.stop()
        ok, err = instance.relaunch_as_admin()
        if ok:
            self.destroy()
            return True
        self.log(t("admin.failed", err=err))
        self.apply_hotkeys(quiet=True)                 # UAC отклонён -- работаем дальше
        return False

    def grab_foreground(self) -> None:
        """Для полноэкранных игр: свернуться, дать 3 с на переключение, взять активное."""
        self.log(t("msg.grab_hint"))
        self.iconify()
        self.after(3000, self._grab_foreground_now)

    def _grab_foreground_now(self) -> None:
        hwnd = winutil.foreground_hwnd()
        title = winutil.window_title(hwnd)
        self.deiconify()
        if not title:
            self.log(t("msg.grab_fail"))
            return
        label, info = self._window_label(hwnd, title)
        self.window_map[label] = info
        values = list(self.cmb_window["values"])
        if label not in values:
            values.append(label)
            self.cmb_window["values"] = values
        self.var_window.set(label)
        self.log(t("msg.target", title=title))
        if info["elevated"]:
            self.offer_elevation(info)

    def selected_index(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def _row_values(self, i: int, step: dict) -> tuple:
        return (i + 1, keys.describe_combo(step["key"]),
                t(f"action.{step.get('action', 'tap')}"),
                step.get("hold_ms", 90), step.get("delay_ms", 100),
                step.get("repeat", 1),
                t("yes") if step.get("enabled", True) else t("no"),
                step.get("comment", ""))

    def _row_tags(self, i: int, step: dict) -> tuple:
        tags = []
        if not step.get("enabled", True):
            tags.append("off")
        if self._active_step == i:
            tags.append("active")
        return tuple(tags)

    def refresh_tree(self, select: int | None = None, active: int | None = None) -> None:
        self._active_step = active
        self.tree.delete(*self.tree.get_children())
        for i, s in enumerate(self.steps):
            self.tree.insert("", "end", iid=str(i), tags=self._row_tags(i, s),
                             values=self._row_values(i, s))
        if select is not None and 0 <= select < len(self.steps):
            iid = str(select)
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def _refresh_row(self, idx: int) -> None:
        """Обновить одну строку, не пересобирая список (иначе слетает выделение)."""
        iid = str(idx)
        if self.tree.exists(iid):
            step = self.steps[idx]
            self.tree.item(iid, values=self._row_values(idx, step),
                           tags=self._row_tags(idx, step))

    def on_tree_select(self, _event=None) -> None:
        idx = self.selected_index()
        if idx is None:
            return
        s = self.steps[idx]
        self._syncing = True                 # заполняем поля -- это не правка шага
        try:
            self.var_key.set(s["key"])
            self._action_key = s.get("action", "tap")
            self.var_action.set(t(f"action.{self._action_key}"))
            self.var_hold.set(s.get("hold_ms", 90))
            self.var_delay.set(s.get("delay_ms", 100))
            self.var_repeat.set(s.get("repeat", 1))
            self.var_comment.set(s.get("comment", ""))
        finally:
            self._syncing = False

    def _on_editor_changed(self, *_args) -> None:
        """Правка полей сразу уходит в выбранный шаг.

        Раньше значения жили только в полях до нажатия «Применить», и запуск
        работал со старым шагом -- выглядело так, будто колонка игнорируется.
        """
        if self._syncing:
            return
        idx = self.selected_index()
        if idx is None:
            return
        step = self._step_from_editor(silent=True)
        if not step:
            return
        step["enabled"] = self.steps[idx].get("enabled", True)
        if step == self.steps[idx]:
            return
        self.steps[idx] = step
        self._refresh_row(idx)

    def _step_from_editor(self, silent: bool = False) -> dict | None:
        """silent -- для правки на ходу: молча отдаём None, пока ввод недоделан."""
        spec = self.var_key.get().strip()
        try:
            keys.parse_combo(spec)
        except Exception as exc:
            if not silent:
                messagebox.showerror(t("title.key"), str(exc), parent=self)
            return None
        try:
            hold = max(1, int(self.var_hold.get()))
            delay = max(0, int(self.var_delay.get()))
            repeat = max(1, int(self.var_repeat.get()))
        except (tk.TclError, ValueError):
            if not silent:
                messagebox.showerror(t("title.numbers"), t("msg.numbers"), parent=self)
            return None
        return {"key": spec, "action": self.current_action_key(), "hold_ms": hold,
                "delay_ms": delay, "repeat": repeat, "enabled": True,
                "comment": self.var_comment.get().strip()[:120]}

    # ------------------------------------------------------- список шагов --
    def add_step(self) -> None:
        step = self._step_from_editor()
        if not step:
            return
        idx = self.selected_index()
        pos = len(self.steps) if idx is None else idx + 1
        self.steps.insert(pos, step)
        self.refresh_tree(select=pos)
        self.log(t("msg.step_added", n=pos + 1, key=keys.describe_combo(step["key"])))

    def apply_step(self) -> None:
        idx = self.selected_index()
        if idx is None:
            messagebox.showinfo(t("step.frame"), t("msg.select_step"), parent=self)
            return
        step = self._step_from_editor()
        if not step:
            return
        step["enabled"] = self.steps[idx].get("enabled", True)
        self.steps[idx] = step
        self.refresh_tree(select=idx)

    def delete_step(self) -> None:
        idx = self.selected_index()
        if idx is None:
            return
        self.steps.pop(idx)
        self.refresh_tree(select=min(idx, len(self.steps) - 1) if self.steps else None)

    def duplicate_step(self) -> None:
        idx = self.selected_index()
        if idx is None:
            return
        self.steps.insert(idx + 1, dict(self.steps[idx]))
        self.refresh_tree(select=idx + 1)

    def toggle_enabled(self) -> None:
        idx = self.selected_index()
        if idx is None:
            return
        self.steps[idx]["enabled"] = not self.steps[idx].get("enabled", True)
        self.refresh_tree(select=idx)

    def move_up(self) -> None:
        idx = self.selected_index()
        if idx is None or idx == 0:
            return
        self.steps[idx - 1], self.steps[idx] = self.steps[idx], self.steps[idx - 1]
        self.refresh_tree(select=idx - 1)

    def move_down(self) -> None:
        idx = self.selected_index()
        if idx is None or idx >= len(self.steps) - 1:
            return
        self.steps[idx + 1], self.steps[idx] = self.steps[idx], self.steps[idx + 1]
        self.refresh_tree(select=idx + 1)

    def clear_steps(self) -> None:
        if self.steps and messagebox.askyesno(t("msg.clear_title"), t("msg.clear_text"),
                                              parent=self):
            self.steps.clear()
            self.refresh_tree()

    # ------------------------------------------------------------ захваты --
    def capture_step_key(self) -> None:
        dlg = KeyCaptureDialog(self, t("dlg.step_key"), allow_mouse=True)
        self.wait_window(dlg)
        if dlg.result:
            self.var_key.set(dlg.result)

    def capture_hotkey(self, action: str) -> None:
        # для хоткея нужна не-модификаторная клавиша: RegisterHotKey иначе бесполезен
        dlg = KeyCaptureDialog(self, t("dlg.hotkey", action=profiles.hotkey_label(action)),
                               allow_modifier_only=False)
        self.wait_window(dlg)
        if dlg.result:
            self.var_hk[action].set(dlg.result)
            self.apply_hotkeys()

    def apply_hotkeys(self, quiet: bool = False) -> None:
        bindings = {a: v.get().strip() for a, v in self.var_hk.items()}
        for action, combo in bindings.items():
            if not combo:
                continue
            try:
                _mods, main = keys.parse_combo(combo)
            except Exception as exc:
                messagebox.showerror(t("title.hotkey"),
                                     f"{profiles.hotkey_label(action)}: {exc}", parent=self)
                return
            if main in keys.MODIFIER_NAMES:
                messagebox.showerror(
                    t("title.hotkey"),
                    t("msg.hk_modifier_only", action=profiles.hotkey_label(action)),
                    parent=self)
                return
        self.hotkeys.set_bindings(bindings)
        self._sync_recorder_ignores()
        if not quiet:
            active = ", ".join(f"{combo} — {profiles.hotkey_label(a)}"
                               for a, combo in bindings.items() if combo)
            self.log(t("hk.assigned", list=active))

    def _sync_recorder_ignores(self) -> None:
        """Сами хоткеи не должны попадать в запись."""
        ignore: set[str] = set()
        for var in self.var_hk.values():
            try:
                mods, main = keys.parse_combo(var.get().strip())
            except Exception:
                continue
            ignore.add(main)
            ignore.update(mods)
        self.recorder.ignore_names = ignore

    # ------------------------------------------------------------- запуск --
    def collect_config(self) -> eng.RunConfig:
        info = self.target_info()
        hwnd = info["hwnd"] if info else 0
        title = info["title"] if info else ""
        cfg = eng.RunConfig(
            steps=self.steps, mode=self.var_mode.get(),
            target_title=title, target_hwnd=hwnd,
            cycles=max(0, int(self.var_cycles.get() or 0)),
            cycle_delay_ms=max(0, int(self.var_cycle_delay.get() or 0)),
            jitter_pct=max(0, min(90, int(self.var_jitter.get() or 0))),
            start_delay_ms=max(0, int(self.var_start_delay.get() or 0)))
        # 统一钳制：与简洁版走同一个入口，避免任一界面绕过校验导致卡键
        cfg, notes = profiles.validate_run_config(cfg)
        if notes:
            self.log(t("msg.param_clamped", list="; ".join(notes)))
            self.logger.warning("运行参数已修正: %s", "; ".join(notes))
        return cfg

    def start_script(self) -> None:
        if self.engine.is_running:
            return
        if self.recorder.is_recording:
            self.log(t("msg.rec_running"))
            return
        info = self.target_info()
        if info and info["elevated"]:
            # запускать бессмысленно: Windows отбросит нажатия в окно с большими правами
            self.log(t("admin.blocked_start"))
            self.offer_elevation(info)
            return
        try:
            cfg = self.collect_config()
        except (tk.TclError, ValueError):
            messagebox.showerror(t("title.settings"), t("msg.settings_numbers"), parent=self)
            return
        if self.engine.start(cfg):
            self.var_status.set(t("status.starting"))
            self._sync_run_buttons()

    def stop_script(self) -> None:
        if self.engine.is_running:
            self.engine.stop()

    def toggle_pause(self) -> None:
        if not self.engine.is_running:
            return
        self.engine.toggle_pause()
        self._sync_run_buttons()

    def toggle_run(self) -> None:
        if self.engine.is_running:
            self.stop_script()
        else:
            self.start_script()

    # ------------------------------------------------------------- запись --
    def toggle_record(self) -> None:
        if self.recorder.is_recording:
            self.finish_record()
            return
        if self.engine.is_running:
            self.log(t("rec.engine_busy"))
            self.engine.stop(join=True)
        self.recorder.record_mouse = bool(self.var_rec_mouse.get())
        self._sync_recorder_ignores()
        if not self.recorder.start():
            return
        self._sync_record_ui()
        self.var_status.set(t("status.recording"))
        self.log(t("rec.started"))

    def finish_record(self) -> None:
        try:
            tail = max(0, int(self.var_rec_tail.get() or 0))
        except (tk.TclError, ValueError):
            tail = 200
        steps = self.recorder.stop(tail_delay_ms=tail)
        self._sync_record_ui()
        self.var_status.set(t("status.ready"))
        if not steps:
            self.log(t("rec.empty"))
            return
        if self.var_rec_replace.get():
            self.steps = steps
        else:
            self.steps.extend(steps)
        self.refresh_tree(select=len(self.steps) - len(steps))
        self.log(t("rec.done", n=len(steps)))

    # ------------------------------------------------------- диагностика --
    def run_diagnostics(self) -> None:
        """Отчёт по фактам: кто активен, чьи права выше, пускает ли Windows ввод."""
        self.log(t("diag.wait"))
        self.after(3000, self._diagnostics_now)

    def _diagnostics_now(self) -> None:
        import os

        mark = len(self._log_buffer)          # чтобы выдрать отчёт для файла
        self.log(t("diag.header"))
        self.log(t("diag.self", pid=os.getpid(),
                   admin=t("yes") if winutil.is_admin() else t("no"),
                   level=winutil.own_integrity_level()))

        fg = winutil.foreground_hwnd()
        fg_pid = winutil.window_pid(fg)
        exe, _err = winutil.process_info(fg_pid)
        self.log(t("diag.fg", title=winutil.window_title(fg) or "?",
                   cls=winutil.window_class(fg), pid=fg_pid, exe=exe or "?"))
        own_level = winutil.own_integrity_level()
        fg_level = winutil.process_integrity(fg_pid)
        self.log(t("diag.fg_integrity", level=fg_level, own=own_level))
        privileged = (winutil.integrity_rank(fg_level)
                      > winutil.integrity_rank(own_level))
        if privileged:
            self.log(t("diag.fg_higher"))
        elif fg_level == "?":
            self.log(t("diag.fg_unknown"))
        else:
            self.log(t("diag.fg_same"))

        info = self.target_info()
        target = info["hwnd"] if info else 0
        if target:
            self.log(t("diag.target", title=info["title"], hwnd=hex(target)))
            self.log(t("diag.target_is_fg") if target == fg else t("diag.target_not_fg"))
        else:
            self.log(t("diag.target_none"))
        self.log(t("diag.mode", mode=t(MODE_LABEL_KEYS[self.var_mode.get()])))

        send_ok = True
        try:
            sender.key_down("rshift")
            sender.key_up("rshift")
            self.log(t("diag.test_ok"))
        except Exception as exc:
            send_ok = False
            self.log(t("diag.test_fail", err=exc))

        if not send_ok or privileged:
            verdict = t("diag.verdict_admin")
        elif target and target != fg:
            verdict = t("diag.verdict_focus")
        elif not target and fg == self.winfo_id():
            verdict = t("diag.verdict_focus")
        else:
            verdict = t("diag.verdict_ok")
        self.log(t("diag.verdict", text=verdict))
        self.log(t("diag.footer"))

        # отчёт в файл: удобно переслать, не переписывая журнал руками
        try:
            path = profiles.SETTINGS_DIR / "diagnostics.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(self._log_buffer[mark:]) + "\n\n")
            self.log(t("diag.file", path=path))
        except Exception as exc:
            self.log(f"{exc}")

    def open_selftest(self) -> None:
        """Прогнать последовательность в своё окно: видно, доходят ли нажатия вообще."""
        active = [s for s in self.steps if s.get("enabled", True)]
        if not active:
            messagebox.showinfo(t("selftest.title"), t("selftest.no_steps"), parent=self)
            return
        SelfTestWindow(self, active[:12])

    # ------------------------------------------------------------ очередь --
    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                try:
                    self._handle_message(kind, payload)
                except Exception:
                    self.logger.exception("处理队列消息失败 kind=%s", kind)
        except queue.Empty:
            pass
        except Exception:
            self.logger.exception("轮询异常")
        finally:
            # 重新武装必须在 finally 里：任一 handler 抛非 Empty 异常时，
            # 绝不能跳过重新排期，否则轮询永久停摆、所有热键静默失效。
            try:
                if self.winfo_exists():
                    self._poll_id = self.after(self.POLL_MS, self._poll)
            except tk.TclError:
                pass

    def _handle_message(self, kind: str, payload) -> None:
        if kind == "log":
            self.log(payload)
        elif kind == "state":
            self.var_status.set(payload)
        elif kind == "step":
            self.refresh_tree(select=self.selected_index(), active=payload)
        elif kind == "finish":
            self._sync_run_buttons()
        elif kind == "error":
            # отправка отклонена системой -- это надо показать, а не спрятать в лог
            messagebox.showerror(t("err.send.title"), payload, parent=self)
        elif kind == "rec":
            name, is_down, count = payload
            if is_down and self.recorder.is_recording:
                self.lbl_rec.config(
                    text=t("rec.progress", n=count, key=keys.describe(name)),
                    foreground="#c00")
        elif kind == "action":
            self._handle_hotkey(payload)

    def _handle_hotkey(self, action: str) -> None:
        if action == "run_toggle":
            # F1 = только запуск (start_script сам игнорирует повторный вызов,
            # если скрипт уже идёт). Остановка -- отдельная клавиша F3.
            self.start_script()
        elif action == "pause":
            self.toggle_pause()
        elif action == "stop":
            if self.recorder.is_recording:
                self.finish_record()
            self.stop_script()
        elif action == "record_toggle":
            self.toggle_record()
        elif action == "minimize":
            self.iconify()

    # ------------------------------------------------------------ профили --
    def _ui_to_cfg(self) -> dict:
        cfg = profiles.default_config()
        cfg["language"] = i18n.language()
        cfg["steps"] = [dict(s) for s in self.steps]
        cfg["mode"] = self.var_mode.get()
        info = self.target_info()
        cfg["target_title"] = info["title"] if info else ""
        for key, var in (("cycles", self.var_cycles),
                         ("cycle_delay_ms", self.var_cycle_delay),
                         ("jitter_pct", self.var_jitter),
                         ("start_delay_ms", self.var_start_delay),
                         ("record_tail_delay_ms", self.var_rec_tail)):
            try:
                cfg[key] = max(0, int(var.get() or 0))
            except (tk.TclError, ValueError):
                pass
        cfg["hotkeys"] = {a: v.get().strip() for a, v in self.var_hk.items()}
        cfg["record_mouse"] = bool(self.var_rec_mouse.get())
        cfg["record_replace"] = bool(self.var_rec_replace.get())
        return cfg

    def _load_cfg_into_ui(self, cfg: dict) -> None:
        self._syncing = True
        try:
            self._apply_cfg(cfg)
        finally:
            self._syncing = False

    def _apply_cfg(self, cfg: dict) -> None:
        self.steps = [dict(s) for s in cfg["steps"]]
        self.var_mode.set(cfg["mode"])
        self.var_cycles.set(cfg["cycles"])
        self.var_cycle_delay.set(cfg["cycle_delay_ms"])
        self.var_jitter.set(cfg["jitter_pct"])
        self.var_start_delay.set(cfg["start_delay_ms"])
        self.var_rec_mouse.set(cfg["record_mouse"])
        self.var_rec_replace.set(cfg["record_replace"])
        self.var_rec_tail.set(cfg["record_tail_delay_ms"])
        for action, var in self.var_hk.items():
            var.set(cfg["hotkeys"].get(action, profiles.DEFAULT_HOTKEYS[action]))
        self.cfg = cfg
        lang = cfg.get("language", i18n.language())
        if lang != i18n.language():
            self.set_language(lang)

    def profile_new(self) -> None:
        if self.steps and not messagebox.askyesno(t("msg.new_title"), t("msg.new_text"),
                                                  parent=self):
            return
        self.profile_path = None
        keep_lang = i18n.language()
        cfg = profiles.default_config()
        cfg["language"] = keep_lang
        self._load_cfg_into_ui(cfg)
        self.refresh_tree()
        self.apply_hotkeys(quiet=True)
        self.title(self._window_title())
        self.log(t("msg.new_profile"))

    def profile_open(self) -> None:
        profiles.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.askopenfilename(
            parent=self, title=t("title.open"),
            initialdir=str(profiles.PROFILE_DIR),
            filetypes=[(t("title.profile_filter"), "*.json"), (t("title.all_files"), "*.*")])
        if not path:
            return
        try:
            cfg = profiles.load(path)
        except Exception as exc:
            messagebox.showerror(t("title.open"), t("msg.open_error", err=exc), parent=self)
            return
        self.profile_path = Path(path)
        self._load_cfg_into_ui(cfg)
        self.refresh_tree()
        self.refresh_windows()
        self.apply_hotkeys(quiet=True)
        self.title(self._window_title(self.profile_path.name))
        self.log(t("msg.loaded", name=self.profile_path.name, n=len(self.steps)))

    def profile_save(self) -> None:
        if not self.profile_path:
            self.profile_save_as()
            return
        try:
            profiles.save(self.profile_path, self._ui_to_cfg())
            self.log(t("msg.saved", name=self.profile_path.name))
        except Exception as exc:
            messagebox.showerror(t("menu.save"), str(exc), parent=self)

    def profile_save_as(self) -> None:
        profiles.PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self, title=t("title.save"), defaultextension=".json",
            initialdir=str(profiles.PROFILE_DIR),
            filetypes=[(t("title.profile_filter"), "*.json")])
        if not path:
            return
        self.profile_path = Path(path)
        self.profile_save()
        self.title(self._window_title(self.profile_path.name))

    def show_help(self) -> None:
        head = f"KeyPresser {t('app.version', v=version.VERSION)} ({version.BUILT_AT})"
        messagebox.showinfo(t("menu.how"), head + "\n\n" + t("help.text"), parent=self)

    def on_close(self) -> None:
        try:
            poll_id = getattr(self, "_poll_id", None)
            if poll_id:
                self.after_cancel(poll_id)
                self._poll_id = None
            self.engine.stop(join=True)
            if self.engine.is_running:
                self.logger.warning("退出时线程未能在超时内结束，强制松开已登记按键")
                self.engine.force_release()
            if self.recorder.is_recording:
                self.recorder.stop()
            self.hotkeys.stop()
            profiles.save_settings(self._ui_to_cfg())
        finally:
            self.destroy()
