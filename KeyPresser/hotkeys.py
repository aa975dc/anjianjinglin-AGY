"""Глобальные горячие клавиши (RegisterHotKey).

Работают, когда фокус в окне игры -- обычный bind в tkinter так не умеет.
Хоткей привязан к потоку, который его зарегистрировал, поэтому вся работа идёт
в отдельном потоке с собственным циклом сообщений.
"""

import ctypes
import threading
from ctypes import wintypes

import i18n
import keys

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 1, 2, 4, 8, 0x4000

_MOD_BITS = {
    "alt": MOD_ALT, "lalt": MOD_ALT, "ralt": MOD_ALT,
    "ctrl": MOD_CONTROL, "lctrl": MOD_CONTROL, "rctrl": MOD_CONTROL,
    "shift": MOD_SHIFT, "lshift": MOD_SHIFT, "rshift": MOD_SHIFT,
    "lwin": MOD_WIN, "rwin": MOD_WIN,
}


class HotkeyManager:
    """on_action(action) вызывается из потока хоткеев (в GUI -- через after)."""

    def __init__(self, on_action, on_error=None):
        self._on_action = on_action
        self._on_error = on_error or (lambda msg: None)
        self._bindings: dict[str, str] = {}
        self._thread: threading.Thread | None = None
        self._tid: int | None = None
        self._ready = threading.Event()
        self.failed: list[str] = []

    @property
    def bindings(self) -> dict[str, str]:
        return dict(self._bindings)

    def set_bindings(self, bindings: dict[str, str]) -> None:
        """{'run_toggle': 'f6', 'record_toggle': 'f9', ...} -- перерегистрирует всё."""
        self.stop()
        self._bindings = {a: c for a, c in bindings.items() if c and c.strip()}
        self.start()

    def start(self) -> None:
        if not self._bindings or (self._thread and self._thread.is_alive()):
            return
        self._ready.clear()
        self.failed = []
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def stop(self) -> None:
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread, self._tid = None, None

    # --- внутреннее --------------------------------------------------------
    def _run(self) -> None:
        self._tid = kernel32.GetCurrentThreadId()
        ids: dict[int, str] = {}
        for i, (action, combo) in enumerate(self._bindings.items(), start=1):
            try:
                mods, main = keys.parse_combo(combo)
                vk = keys.vk_of(main)
                if not vk:
                    raise ValueError(i18n.t("hk.err.raw"))
            except Exception as exc:
                self.failed.append(action)
                self._on_error(i18n.t("hk.err.parse", combo=combo, action=action, err=exc))
                continue
            mod_flags = MOD_NOREPEAT
            for m in mods:
                mod_flags |= _MOD_BITS.get(m, 0)
            if user32.RegisterHotKey(None, i, mod_flags, vk):
                ids[i] = action
            else:
                self.failed.append(action)
                self._on_error(i18n.t("hk.err.busy", combo=combo, action=action))
        self._ready.set()

        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    action = ids.get(msg.wParam)
                    if action:
                        try:
                            self._on_action(action)
                        except Exception as exc:
                            self._on_error(i18n.t("hk.err.handler", err=exc))
        finally:
            for i in ids:
                user32.UnregisterHotKey(None, i)
