"""KeyPresser -- точка входа.

Запуск:  pythonw main.py   (без консоли)  или  python main.py
"""

import ctypes
import sys


def _enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # per-monitor DPI
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    if sys.platform != "win32":
        print("KeyPresser работает только на Windows (использует WinAPI SendInput).")
        return 2
    _enable_dpi_awareness()

    import applog
    import instance

    # 日志尽早开，后面不管哪一步出问题都能留下痕迹
    applog.setup()

    # 界面模式：
    #   无参数      -> 简洁中文界面（默认）
    #   mini        -> 迷你浮动窗口
    #   full        -> 上游完整界面（录制/诊断/配置档案等进阶功能）
    modes = {a.lower() for a in sys.argv[1:]}
    mode = "full" if "full" in modes else ("mini" if "mini" in modes else "simple")
    applog.log_startup(applog.get("main"), mode, sys.argv[1:])

    # Вторая копия запрещена: глобальные хоткеи достаются только первой, и вторая
    # молча не реагировала бы на F1. Проверяем два признака: мьютекс и уже
    # открытое окно KeyPresser (старые сборки мьютекса не ставили).
    if not instance.acquire() or instance.find_existing_window():
        import tkinter as tk
        from tkinter import messagebox

        import i18n
        import profiles
        import winutil

        applog.get("main").warning(
            "检测到已有实例在运行（互斥体=%s 已有窗口=%s），本次启动被拦下",
            not instance.acquire(), bool(instance.find_existing_window()))

        i18n.set_language(profiles.load_settings().get("language",
                                                      i18n.DEFAULT_LANGUAGE))
        hwnd = instance.find_existing_window()
        if hwnd:
            winutil.activate(hwnd)
        probe = tk.Tk()
        probe.withdraw()
        messagebox.showinfo(i18n.t("inst.title"), i18n.t("inst.blocked"))
        probe.destroy()
        applog.get("main").info("已唤起既有窗口并退出本次启动")
        return 0

    if mode == "full":
        from gui import App
        App().mainloop()
    elif mode == "mini":
        from gui_mini import MiniApp
        MiniApp().mainloop()
    else:
        from gui_simple import SimpleApp
        SimpleApp().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
