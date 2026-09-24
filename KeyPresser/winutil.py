"""Работа с окнами: список, поиск, активация, проверка фокуса."""

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SW_RESTORE = 9
GW_OWNER = 4

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = (WNDENUMPROC, wintypes.LPARAM)
user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
user32.IsWindowVisible.argtypes = (wintypes.HWND,)
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))


def window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def list_windows() -> list[tuple[int, str]]:
    """Видимые окна верхнего уровня с заголовком: [(hwnd, title), ...]."""
    found: list[tuple[int, str]] = []

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, GW_OWNER):
            return True
        title = window_title(hwnd)
        if title and title not in ("Program Manager", "Default IME", "MSCTFIME UI"):
            found.append((hwnd, title))
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    found.sort(key=lambda x: x[1].lower())
    return found


def find_window(title_part: str) -> int | None:
    """Первое окно, чей заголовок содержит подстроку (без учёта регистра)."""
    needle = title_part.strip().lower()
    if not needle:
        return None
    for hwnd, title in list_windows():
        if needle in title.lower():
            return hwnd
    return None


def is_window(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd))


def foreground_hwnd() -> int:
    return user32.GetForegroundWindow()


GA_ROOT = 2


def root_hwnd(hwnd: int) -> int:
    """Настоящее окно верхнего уровня для дочернего hwnd (tkinter даёт дочерний)."""
    return user32.GetAncestor(hwnd, GA_ROOT) or hwnd


def is_foreground(hwnd: int) -> bool:
    return bool(hwnd) and user32.GetForegroundWindow() == hwnd


def activate(hwnd: int) -> bool:
    """Поднять окно на передний план. Windows разрешает это не всегда —
    трюк с AttachThreadInput покрывает большинство случаев."""
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    if user32.SetForegroundWindow(hwnd):
        return True
    fg = user32.GetForegroundWindow()
    src = user32.GetWindowThreadProcessId(fg, None)
    dst = user32.GetWindowThreadProcessId(hwnd, None)
    if src and dst:
        user32.AttachThreadInput(src, dst, True)
        try:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            user32.AttachThreadInput(src, dst, False)
    return bool(user32.GetForegroundWindow() == hwnd)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# --- диагностика: кто владеет окном и пускает ли он наш ввод ---------------

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TOKEN_INTEGRITY_LEVEL = 25

_INTEGRITY_NAMES = {0x0000: "untrusted", 0x1000: "low", 0x2000: "medium",
                    0x2100: "medium+", 0x3000: "high", 0x4000: "system"}

kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE


def window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_pid(hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def process_info(pid: int) -> tuple[str | None, int]:
    """(имя exe, код ошибки). exe=None -> процесс недоступен, err говорит почему.

    Отказ доступа (5) к процессу того же пользователя -- почти всегда признак
    того, что процесс запущен от администратора, а мы нет.
    """
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None, ctypes.get_last_error()
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wintypes.DWORD(512)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value.rsplit("\\", 1)[-1], 0
        return None, ctypes.get_last_error()
    finally:
        kernel32.CloseHandle(handle)


advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
advapi32.OpenProcessToken.argtypes = (wintypes.HANDLE, wintypes.DWORD,
                                      ctypes.POINTER(wintypes.HANDLE))
advapi32.GetTokenInformation.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
advapi32.GetSidSubAuthorityCount.argtypes = (ctypes.c_void_p,)
advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
advapi32.GetSidSubAuthority.argtypes = (ctypes.c_void_p, wintypes.DWORD)
advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)


_INTEGRITY_RANK = {"untrusted": 0, "low": 1, "medium": 2, "medium+": 3,
                   "high": 4, "system": 5}


def integrity_rank(level: str) -> int:
    """Числовой вес уровня: больше = больше прав. Неизвестный -> -1."""
    return _INTEGRITY_RANK.get(level, -1)


def _integrity_of_token(token: wintypes.HANDLE) -> str:
    size = wintypes.DWORD()
    advapi32.GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, None, 0,
                                 ctypes.byref(size))
    if not size.value:
        return "?"
    buf = ctypes.create_string_buffer(size.value)
    if not advapi32.GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, buf, size,
                                        ctypes.byref(size)):
        return "?"
    # TOKEN_MANDATORY_LABEL = SID_AND_ATTRIBUTES: первое поле -- PSID
    sid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
    count = advapi32.GetSidSubAuthorityCount(sid)
    if not count:
        return "?"
    rid = advapi32.GetSidSubAuthority(sid, count.contents.value - 1).contents.value
    return _INTEGRITY_NAMES.get(rid, f"0x{rid:x}")


def process_integrity(pid: int) -> str:
    """Уровень целостности чужого процесса ('medium' / 'high' / ...).

    Читаем его токен: это надёжнее, чем судить по доступности процесса --
    запрос PROCESS_QUERY_LIMITED_INFORMATION к процессу того же пользователя
    удаётся и для процесса с правами администратора.
    """
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return "?"
    try:
        token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            return "?"
        try:
            return _integrity_of_token(token)
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(handle)


def own_integrity_level() -> str:
    """'medium' / 'high' / 'system' -- уровень целостности своего процесса.

    Ниже, чем у окна игры -> Windows не пропустит наш ввод (SendInput -> код 5).
    """
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_QUERY,
                                     ctypes.byref(token)):
        return "?"
    try:
        size = wintypes.DWORD()
        advapi32.GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, None, 0,
                                     ctypes.byref(size))
        if not size.value:
            return "?"
        buf = ctypes.create_string_buffer(size.value)
        if not advapi32.GetTokenInformation(token, TOKEN_INTEGRITY_LEVEL, buf,
                                            size, ctypes.byref(size)):
            return "?"
        # TOKEN_MANDATORY_LABEL = SID_AND_ATTRIBUTES: первое поле -- PSID
        sid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
        count = advapi32.GetSidSubAuthorityCount(sid)
        if not count:
            return "?"
        rid = advapi32.GetSidSubAuthority(sid, count.contents.value - 1).contents.value
        return _INTEGRITY_NAMES.get(rid, f"0x{rid:x}")
    finally:
        kernel32.CloseHandle(token)
