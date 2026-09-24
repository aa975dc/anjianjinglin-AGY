"""Единственный экземпляр приложения и перезапуск с правами администратора."""

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

ERROR_ALREADY_EXISTS = 183
ERROR_ACCESS_DENIED = 5
ERROR_CANCELLED = 1223
SW_SHOWNORMAL = 1

MUTEX_NAME = "KeyPresser.SingleInstance.v1"
WINDOW_TITLE = "KeyPresser"
# 简洁中文界面的标题不同，也要能被识别出来（否则第二份副本找不到已有窗口）
WINDOW_TITLES = ("KeyPresser", "自动按键工具")

# 已知的界面模式参数：提权重启时必须原样透传，否则会回到错误的界面。
KNOWN_MODES = ("simple", "mini", "full")

_handle = None


def acquire() -> bool:
    """True -- мы единственный экземпляр.

    Мьютекс, созданный повышенным процессом, обычному открыть не дадут
    (ACCESS_DENIED) -- это тоже значит "уже запущено", а не "свободно".
    """
    global _handle
    if _handle:
        return True
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    err = ctypes.get_last_error()
    if handle and err != ERROR_ALREADY_EXISTS:
        _handle = handle
        return True
    if handle:
        kernel32.CloseHandle(handle)
    return False


def release() -> None:
    """Отпустить мьютекс -- нужно перед передачей эстафеты новому процессу."""
    global _handle
    if _handle:
        kernel32.CloseHandle(_handle)
        _handle = None


def find_existing_window() -> int:
    """Окно уже запущенного экземпляра (чтобы вытащить его на передний план)."""
    import winutil
    for hwnd, title in winutil.list_windows():
        for base in WINDOW_TITLES:
            if title == base or title.startswith(base + " "):
                return hwnd
    return 0


def _mode_args() -> str:
    """透传界面模式参数（simple / mini / full），大小写不敏感。

    没有它时，从迷你版或完整版点"以管理员身份重启"会一律回到简洁版：
    完整版最惨 —— 它的脚本存在 settings.json，而简洁版读 simple.json，
    用户会以为"我的脚本全没了"。
    """
    known = {m.lower(): m for m in KNOWN_MODES}
    parts: list[str] = []
    for arg in sys.argv[1:]:
        mode = known.get(str(arg).strip().lower())
        if mode:
            parts.append(mode)
    return " ".join(parts)


def _launch_target() -> tuple[str, str]:
    """(что запускать, аргументы) для текущего способа запуска."""
    extra = _mode_args()
    if getattr(sys, "frozen", False):
        return sys.executable, extra
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")          # без консольного окна
    script = Path(sys.argv[0]).resolve()
    params = f'"{script}"'
    if extra:
        params = f"{params} {extra}"               # 保留原界面模式
    return str(pythonw if pythonw.exists() else exe), params


def relaunch_as_admin() -> tuple[bool, str]:
    """Запустить себя же через UAC. (успех, текст ошибки).

    Мьютекс отпускаем до запуска, иначе новый процесс решит, что копия уже
    работает. Если пользователь отказал в UAC -- забираем мьютекс назад.
    """
    exe, params = _launch_target()
    release()
    result = shell32.ShellExecuteW(None, "runas", exe, params or None,
                                   str(Path(exe).parent), SW_SHOWNORMAL)
    if result > 32:
        return True, ""
    acquire()                                       # остаёмся работать как были
    if result == ERROR_CANCELLED:
        return False, "UAC: отказано"
    return False, f"ShellExecute -> {result}"
