"""Запись нажатий: низкоуровневый хук клавиатуры и мыши (WH_KEYBOARD_LL / WH_MOUSE_LL).

Хук отдаёт СКАН-КОД физической клавиши, поэтому запись не зависит от раскладки:
нажатие "ц" при русской раскладке запишется как шаг "w" (sc 11) и при
воспроизведении нажмёт ту же самую клавишу.

Свой собственный ввод (метка sender.INJECT_TAG / флаг INJECTED) игнорируется,
чтобы запись не поймала воспроизведение.
"""

import ctypes
import threading
import time
from ctypes import wintypes

import i18n
import keys
import sender

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_QUIT = 0x0012

LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10
LLKHF_UP = 0x80
LLMHF_INJECTED = 0x01

_MOUSE_EVENTS = {
    0x0201: ("mouse_left", True), 0x0202: ("mouse_left", False),
    0x0204: ("mouse_right", True), 0x0205: ("mouse_right", False),
    0x0207: ("mouse_middle", True), 0x0208: ("mouse_middle", False),
}

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                              wintypes.WPARAM, wintypes.LPARAM)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD)
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = (wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
user32.CallNextHookEx.restype = ctypes.c_ssize_t


GHOST_WINDOW_S = 0.005      # окно, в котором Ctrl считается фантомом от AltGr


def drop_altgr_ghosts(events):
    """Windows подмешивает к правому Alt фантомный левый Ctrl (наследие AltGr).

    Живая клавиатура делает то же самое, поэтому такой Ctrl надо выбросить,
    иначе в записи появляется лишний шаг. Человек физически не успевает нажать
    Ctrl и RAlt в пределах 5 мс, так что ложных срабатываний не будет.
    """
    ralt_times = [(t, is_down) for t, name, is_down in events if name == "ralt"]
    if not ralt_times:
        return list(events)
    kept = []
    for t, name, is_down in events:
        if name in ("lctrl", "ctrl") and any(
                d == is_down and abs(t - rt) <= GHOST_WINDOW_S for rt, d in ralt_times):
            continue
        kept.append((t, name, is_down))
    return kept


def events_to_steps(events, stop_time: float, tail_delay_ms: int = 200,
                    min_delay_ms: int = 0) -> list[dict]:
    """[(t, name, is_down)] -> список шагов для движка.

    Модификатор, зажатый вокруг другой клавиши, склеивается в комбинацию
    (ctrl+alt+space), одиночное нажатие модификатора остаётся отдельным шагом.
    delay_ms шага = пауза ПОСЛЕ него, т.е. зазор до следующего нажатия.
    """
    steps: list[dict] = []
    mods: dict[str, dict] = {}      # зажатые модификаторы
    open_keys: dict[str, tuple[float, list[str]]] = {}
    prev_up_t: float | None = None
    events = drop_altgr_ghosts(events)

    def emit(combo: str, down_t: float, up_t: float) -> None:
        nonlocal prev_up_t
        if steps and prev_up_t is not None:
            gap = int(round((down_t - prev_up_t) * 1000))
            steps[-1]["delay_ms"] = max(min_delay_ms, gap)
        steps.append({
            "key": combo,
            "action": "tap",
            "hold_ms": max(1, int(round((up_t - down_t) * 1000))),
            "delay_ms": tail_delay_ms,
            "repeat": 1,
            "enabled": True,
            "comment": "",
        })
        prev_up_t = up_t

    for t, name, is_down in events:
        is_mod = name in keys.MODIFIER_NAMES
        if is_down:
            if is_mod:
                mods.setdefault(name, {"t": t, "used": False})
            else:
                snapshot = list(mods)
                for m in mods.values():
                    m["used"] = True
                open_keys[name] = (t, snapshot)
        else:
            if is_mod:
                info = mods.pop(name, None)
                if info and not info["used"]:
                    emit(name, info["t"], t)
            else:
                started = open_keys.pop(name, None)
                if started:
                    down_t, snapshot = started
                    emit(keys.format_combo(snapshot, name), down_t, t)

    # клавиши, оставшиеся зажатыми на момент остановки записи
    for name, (down_t, snapshot) in open_keys.items():
        emit(keys.format_combo(snapshot, name), down_t, stop_time)
    for name, info in mods.items():
        if not info["used"]:
            emit(name, info["t"], stop_time)

    if steps:
        steps[-1]["delay_ms"] = tail_delay_ms
    return steps


class Recorder:
    """Пишет живые нажатия в список событий.

    ignore_names -- клавиши, которые не надо записывать (например, сами хоткеи
    старта/стопа записи, иначе они попадут в скрипт).
    """

    def __init__(self, on_event=None, on_error=None):
        self._on_event = on_event or (lambda name, is_down, count: None)
        self._on_error = on_error or (lambda msg: None)
        self.ignore_names: set[str] = set()
        self.record_mouse = True
        self._events: list[tuple[float, str, bool]] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._tid: int | None = None
        self._ready = threading.Event()
        self._running = False
        self._start_t = 0.0

    @property
    def is_recording(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return False
        with self._lock:
            self._events.clear()
        self._ready.clear()
        self._running = True
        self._start_t = time.perf_counter()
        self._thread = threading.Thread(target=self._run, name="recorder", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)
        return True

    def stop(self, tail_delay_ms: int = 200) -> list[dict]:
        if not self._running:
            return []
        self._running = False
        stop_t = time.perf_counter()
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread, self._tid = None, None
        with self._lock:
            events = list(self._events)
        return events_to_steps(events, stop_t, tail_delay_ms=tail_delay_ms)

    # --- внутреннее --------------------------------------------------------
    def _add(self, name: str, is_down: bool) -> None:
        if name in self.ignore_names:
            return
        with self._lock:
            self._events.append((time.perf_counter(), name, is_down))
            count = sum(1 for _t, _n, d in self._events if d)
        self._on_event(name, is_down, count)

    def _run(self) -> None:
        self._tid = kernel32.GetCurrentThreadId()

        def kb_proc(n_code, w_param, l_param):
            if n_code == 0:
                info = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                own = (info.flags & LLKHF_INJECTED) or info.dwExtraInfo == sender.INJECT_TAG
                if not own:
                    name = keys.name_from_scan(info.scanCode,
                                               bool(info.flags & LLKHF_EXTENDED))
                    # у левых/правых модификаторов скан-коды совпадают -- уточняем по VK
                    by_vk = keys.name_from_vk(info.vkCode)
                    if by_vk and by_vk in keys.MODIFIER_NAMES:
                        name = by_vk
                    self._add(name, not (info.flags & LLKHF_UP))
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        def mouse_proc(n_code, w_param, l_param):
            if n_code == 0 and self.record_mouse and w_param in _MOUSE_EVENTS:
                info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                own = (info.flags & LLMHF_INJECTED) or info.dwExtraInfo == sender.INJECT_TAG
                if not own:
                    name, is_down = _MOUSE_EVENTS[w_param]
                    self._add(name, is_down)
            return user32.CallNextHookEx(None, n_code, w_param, l_param)

        kb_cb = HOOKPROC(kb_proc)          # ссылки держим живыми до конца потока
        ms_cb = HOOKPROC(mouse_proc)
        kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kb_cb, None, 0)
        ms_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, ms_cb, None, 0)
        if not kb_hook:
            self._on_error(i18n.t("rec.hook_failed", code=ctypes.get_last_error()))
        self._ready.set()

        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                pass
        finally:
            if kb_hook:
                user32.UnhookWindowsHookEx(kb_hook)
            if ms_hook:
                user32.UnhookWindowsHookEx(ms_hook)
            self._running = False
