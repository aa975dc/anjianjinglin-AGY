"""Отправка нажатий в Windows.

Два режима:
  * SendInput со СКАН-КОДАМИ -- идёт через системную очередь ввода, поэтому его
    видят DirectInput/RawInput-игры. Скан-код = физическая клавиша, так что
    активная раскладка (в т.ч. русская) на результат не влияет. Требует,
    чтобы окно игры было активным.
  * PostMessage -- прямо в окно, работает в фоне, но многие игры его
    игнорируют (они читают ввод не через оконные сообщения).
"""

import ctypes
import time
from ctypes import wintypes

import i18n
import keys

user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF = {
    "mouse_left": (0x0002, 0x0004),
    "mouse_right": (0x0008, 0x0010),
    "mouse_middle": (0x0020, 0x0040),
}

WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
WM_SYSKEYDOWN, WM_SYSKEYUP = 0x0104, 0x0105
WM_MOUSE_MSG = {
    "mouse_left": (0x0201, 0x0202),
    "mouse_right": (0x0204, 0x0205),
    "mouse_middle": (0x0207, 0x0208),
}

# Метка на своём вводе: низкоуровневый хук записи по ней отличает наши
# собственные нажатия от живых нажатий пользователя.
INJECT_TAG = 0x4B505252     # 'KPRR'

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _INPUTunion(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTunion)]


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype = wintypes.UINT

MOD_GAP_S = 0.012       # пауза между модификатором и клавишей: игры её любят


def _send(*inputs: INPUT) -> None:
    arr = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        err = ctypes.get_last_error()
        raise OSError(i18n.t("send.rejected", code=err))


def _key_input(name: str, up: bool) -> INPUT:
    vk, sc, ext = keys.code_of(name)
    flags = KEYEVENTF_KEYUP if up else 0
    if ext:
        flags |= KEYEVENTF_EXTENDEDKEY
    if sc:
        flags |= KEYEVENTF_SCANCODE
        ki = KEYBDINPUT(wVk=0, wScan=sc, dwFlags=flags, dwExtraInfo=INJECT_TAG)
    else:
        # Скан-кода нет (сырой vk:) -- пробуем получить его у системы, иначе VK.
        sc2 = user32.MapVirtualKeyW(vk, keys.MAPVK_VK_TO_VSC)
        if sc2:
            flags |= KEYEVENTF_SCANCODE
            ki = KEYBDINPUT(wVk=0, wScan=sc2, dwFlags=flags, dwExtraInfo=INJECT_TAG)
        else:
            ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, dwExtraInfo=INJECT_TAG)
    return INPUT(type=INPUT_KEYBOARD, ki=ki)


def _mouse_input(name: str, up: bool) -> INPUT:
    down_flag, up_flag = MOUSEEVENTF[name]
    return INPUT(type=INPUT_MOUSE,
                 mi=MOUSEINPUT(dwFlags=up_flag if up else down_flag,
                               dwExtraInfo=INJECT_TAG))


# --- публичный API ---------------------------------------------------------

def key_down(name: str) -> None:
    name = keys.normalize(name)
    _send(_mouse_input(name, False) if name in MOUSEEVENTF else _key_input(name, False))


def key_up(name: str) -> None:
    name = keys.normalize(name)
    _send(_mouse_input(name, True) if name in MOUSEEVENTF else _key_input(name, True))


def hold_down(mods: list[str], main: str) -> None:
    for m in mods:
        key_down(m)
        time.sleep(MOD_GAP_S)
    key_down(main)


def release(mods: list[str], main: str) -> None:
    try:
        key_up(main)
    finally:
        for m in reversed(mods):
            try:
                key_up(m)
            except OSError:
                pass


def tap(mods: list[str], main: str, hold_ms: int = 40) -> None:
    """Модификаторы вниз -> клавиша вниз -> удержание -> всё вверх."""
    pressed: list[str] = []
    try:
        for m in mods:
            key_down(m)
            pressed.append(m)
            time.sleep(MOD_GAP_S)
        key_down(main)
        pressed.append(main)
        time.sleep(max(hold_ms, 1) / 1000.0)
    finally:
        for name in reversed(pressed):
            try:
                key_up(name)
            except Exception:
                pass


def release_all(names) -> None:
    """Аварийно отпустить всё, что могло остаться зажатым."""
    for name in names:
        try:
            key_up(name)
        except Exception:
            pass


# --- режим PostMessage (фон) ----------------------------------------------

def _lparam(sc: int, ext: bool, up: bool) -> int:
    lp = 1 | ((sc & 0xFF) << 16)
    if ext:
        lp |= 1 << 24
    if up:
        lp |= (1 << 30) | (1 << 31)
    return lp


def post_tap(hwnd: int, mods: list[str], main: str, hold_ms: int = 40) -> None:
    main = keys.normalize(main)
    if main in WM_MOUSE_MSG:
        down, up = WM_MOUSE_MSG[main]
        user32.PostMessageW(hwnd, down, 1, 0)
        time.sleep(max(hold_ms, 1) / 1000.0)
        user32.PostMessageW(hwnd, up, 0, 0)
        return

    alt_held = any(keys.normalize(m) in ("alt", "lalt", "ralt") for m in mods)
    combo = [*mods, main]
    for name in combo:
        vk, sc, ext = keys.code_of(name)
        if not vk:
            vk = user32.MapVirtualKeyW(sc, 1)   # MAPVK_VSC_TO_VK
        user32.PostMessageW(hwnd, WM_SYSKEYDOWN if alt_held else WM_KEYDOWN,
                            vk, _lparam(sc, ext, False))
    time.sleep(max(hold_ms, 1) / 1000.0)
    for name in reversed(combo):
        vk, sc, ext = keys.code_of(name)
        if not vk:
            vk = user32.MapVirtualKeyW(sc, 1)
        user32.PostMessageW(hwnd, WM_SYSKEYUP if alt_held else WM_KEYUP,
                            vk, _lparam(sc, ext, True))
