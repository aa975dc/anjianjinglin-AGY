"""设计 token 与 Canvas 控件 —— 严格对应画布 729400799430046 的设计稿。

取值来源：
* 画板 4（设计规范）：色板 / 字阶 / 圆角与间距 / 语义色；
* 画板 1/2（简洁版深浅色）与画板 3（迷你条）的实际节点值。

tkinter 没有原生圆角与半透明：卡片、按钮、药丸用 Canvas 圆角多边形绘制；
设计里的半透明白（键帽、悬停）按底色预先混成不透明色（mix）。
字体：中文 Microsoft YaHei UI，数字/代码 Consolas（对应稿内 Roboto Mono），
负数字号 = 像素尺寸，与设计稿 px 一一对应。
"""

import ctypes
import tkinter as tk
from tkinter import font as tkfont

# ---------------------------------------------------------------- 色板 --
# 画板 4 · 深色主题（默认）
DARK = {
    "bg": "#0A0A0B",        # 页面底
    "card": "#141417",      # 卡片
    "fill2": "#1C1C20",     # 次级填充
    "fill3": "#101011",     # 禁用/输入禁用底
    "border": "#27272A",    # 描边
    "text1": "#FAFAFA",     # 主文字
    "text2": "#A1A1AA",     # 次文字
    "dim": "#71717A",       # 弱文字
    "faint": "#52525B",     # 微标签
    "ghost": "#3F3F46",     # 禁用文字/日志时间
    "accent": "#7C3AED",    # 强调
    "green": "#10B981", "amber": "#F59E0B", "red": "#F43F5E",
    "input_bg": "#0A0A0B",  # 输入框底（画板 1 与页面底同色）
    "white": "#FFFFFF",
}
# 画板 2 · 浅色主题（同一套 token 换值）
LIGHT = {
    "bg": "#FAFAFA", "card": "#FFFFFF", "fill2": "#F4F4F5", "fill3": "#ECECEF",
    "border": "#E5E5E5", "text1": "#18181B", "text2": "#52525B",
    "dim": "#71717A", "faint": "#A1A1AA", "ghost": "#D4D4D8",
    "accent": "#7C3AED",
    "green": "#10B981", "amber": "#F59E0B", "red": "#F43F5E",
    "input_bg": "#FAFAFA", "white": "#FFFFFF",
}

FONT_CN = "Microsoft YaHei UI"
FONT_MONO = "Consolas"


def f_cn(px: int, bold: bool = False) -> tuple:
    return (FONT_CN, -px, "bold") if bold else (FONT_CN, -px)


def f_mono(px: int, bold: bool = False) -> tuple:
    return (FONT_MONO, -px, "bold") if bold else (FONT_MONO, -px)


def measure(font: tuple, text: str) -> int:
    return tkfont.Font(font=font).measure(text)


def mix(c1: str, c2: str, t: float) -> str:
    """c1 向 c2 混合 t∈[0,1] —— 用于把设计的半透明白预混成不透明色。"""
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#{:02x}{:02x}{:02x}".format(
        *(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def rounded(cv: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
            r: float, fill: str, outline: str | None = None,
            width: int = 1) -> int:
    """圆角矩形（平滑多边形近似，视觉与设计稿一致）。"""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, fill=fill,
                             outline=outline or "", width=width)


# ------------------------------------------------------------- 窗口外观 --
def round_window(win) -> None:
    """Win11 DWM 圆角（best-effort，Win10 自动跳过保持方角）。"""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        pref = ctypes.c_int(33)                     # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33,
                                                   ctypes.byref(pref), 4)
    except Exception:
        pass


def add_taskbar(win) -> None:
    """无边框窗口仍显示在任务栏 / Alt+Tab（best-effort）。

    关键：tkinter 的 overrideredirect(True) 在 Windows 上就是靠加
    WS_EX_TOOLWINDOW 实现的，而该样式优先级高于 WS_EX_APPWINDOW ——
    只加 APPWINDOW 不够，必须把 TOOLWINDOW 清掉，再用
    SWP_FRAMECHANGED 让系统重算框架，否则任务栏里永远不出现。
    """
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x40000
        WS_EX_TOOLWINDOW = 0x80
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                              (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
        # SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_FRAMECHANGED
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27)
    except Exception:
        pass


def minimize_window(win) -> None:
    """无边框窗口的最小化（iconify 对无边框窗等于消失，不能用）。"""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        ctypes.windll.user32.ShowWindow(hwnd, 6)    # SW_MINIMIZE
    except Exception:
        pass


def enable_drag(win, *widgets, zone=None) -> None:
    """让窗口可在指定控件上拖拽；zone(e) 返回 False 时忽略（如内容区）。"""
    state = {"dx": 0, "dy": 0}

    def press(e):
        state["dx"], state["dy"] = e.x, e.y

    def move(e):
        if zone and not zone(e):
            return
        win.geometry(f"+{e.x_root - state['dx']}+{e.y_root - state['dy']}")

    for w in widgets:
        w.bind("<Button-1>", press, add="+")
        w.bind("<B1-Motion>", move, add="+")


# ------------------------------------------------------------- 图标绘制 --
# 每个函数在 (x, y, s) 方框内绘制，color 为线条/填充色
def icon_play(cv, x, y, s, color):
    cv.create_polygon(x + s * 0.28, y + s * 0.15, x + s * 0.28, y + s * 0.85,
                      x + s * 0.85, y + s * 0.5, fill=color, smooth=True)


def icon_pause(cv, x, y, s, color):
    w = s * 0.18
    cv.create_rectangle(x + s * 0.24, y + s * 0.2, x + s * 0.24 + w,
                        y + s * 0.8, fill=color, width=0)
    cv.create_rectangle(x + s * 0.58, y + s * 0.2, x + s * 0.58 + w,
                        y + s * 0.8, fill=color, width=0)


def icon_stop(cv, x, y, s, color):
    cv.create_rectangle(x + s * 0.24, y + s * 0.24, x + s * 0.76, y + s * 0.76,
                        fill=color, width=0)


def icon_minus(cv, x, y, s, color):
    cv.create_line(x + s * 0.2, y + s * 0.5, x + s * 0.8, y + s * 0.5,
                   fill=color, width=1.5)


def icon_close(cv, x, y, s, color):
    cv.create_line(x + s * 0.24, y + s * 0.24, x + s * 0.76, y + s * 0.76,
                   fill=color, width=1.5)
    cv.create_line(x + s * 0.76, y + s * 0.24, x + s * 0.24, y + s * 0.76,
                   fill=color, width=1.5)


def icon_max(cv, x, y, s, color):
    cv.create_rectangle(x + s * 0.18, y + s * 0.2, x + s * 0.82, y + s * 0.8,
                        outline=color, width=1.2)
    cv.create_line(x + s * 0.18, y + s * 0.58, x + s * 0.82, y + s * 0.58,
                   fill=color, width=1.2)


def icon_chevron(cv, x, y, s, color, up=False):
    a, b = (0.3, 0.7) if not up else (0.7, 0.3)
    cv.create_line(x + s * 0.22, y + s * a, x + s * 0.5, y + s * b,
                   fill=color, width=1.5)
    cv.create_line(x + s * 0.5, y + s * b, x + s * 0.78, y + s * a,
                   fill=color, width=1.5)


ICONS = {"play": icon_play, "pause": icon_pause, "stop": icon_stop,
         "minus": icon_minus, "close": icon_close, "max": icon_max,
         "chevron": icon_chevron,
         "chevron_up": lambda cv, x, y, s, c: icon_chevron(cv, x, y, s, c,
                                                           up=True)}


# ------------------------------------------------------------- 控件 --
class RButton(tk.Canvas):
    """圆角按钮：底色圆角矩形 + 可选图标 + 文字 + 可选键帽，悬停/禁用态。

    backdrop = 按钮所在卡片的底色（Canvas 无法透明，用它填自家底）。
    """

    def __init__(self, master, command=None, *, backdrop: str, text: str = "",
                 font: tuple | None = None, fg: str = "#FFFFFF",
                 bg: str = "#141417", border: str | None = None,
                 radius: int = 8, height: int = 36, icon: str | None = None,
                 icon_size: int = 14, keycap: str | None = None,
                 keycap_bg: str | None = None, keycap_fg: str | None = None,
                 pad: tuple = (14, 11), gap: int = 7, hover: str | None = None,
                 disabled: dict | None = None):
        self._base = dict(text=text, font=font or f_cn(13), fg=fg, bg=bg,
                          border=border, icon=icon, keycap=keycap,
                          keycap_bg=keycap_bg, keycap_fg=keycap_fg)
        self._hover, self._disabled = hover, (disabled or {})
        self._command, self._enabled = command, True
        self._pad, self._gap = pad, gap
        self._radius, self._h = radius, height
        self._icon_size = icon_size
        self._backdrop = backdrop
        self._keycap_w = (measure(f_mono(10, True), keycap) + 12) if keycap else 0
        super().__init__(master, width=1, height=height, highlightthickness=0,
                         bg=backdrop)
        self._apply(self._base)
        self.bind("<Enter>", lambda e: self._paint(hover=True))
        self.bind("<Leave>", lambda e: self._paint())
        self.bind("<Button-1>", self._click)

    # -- 尺寸 -----------------------------------------------------------
    def _width(self, cfg) -> int:
        w = self._pad[0]
        if cfg["icon"]:
            w += self._icon_size + self._gap
        w += measure(cfg["font"], cfg["text"])
        if cfg["keycap"]:
            w += self._gap + self._keycap_w
        return round(w + self._pad[1])

    def _apply(self, cfg) -> None:
        """应用一组"正常态"颜色（悬停/禁用在此基础上派生）。"""
        self._cfg = dict(cfg)
        self.config(width=self._width(cfg))
        self._paint()

    # -- 状态 -----------------------------------------------------------
    def _click(self, _e):
        if self._enabled and self._command:
            self._command()

    def _paint(self, hover: bool = False) -> None:
        c = self._cfg
        self.delete("all")
        h = self._h
        if not self._enabled:
            d = self._disabled
            rounded(self, 1, 1, self._width(c) - 1, h - 1, self._radius,
                    fill=d.get("bg", c["bg"]), outline=d.get("border"),
                    width=1)
            fg = d.get("fg", c["fg"])
            icon_c, kbg, kfg = fg, d.get("bg", c["bg"]), fg
        else:
            bg = self._hover if (hover and self._hover) else c["bg"]
            rounded(self, 1, 1, self._width(c) - 1, h - 1, self._radius,
                    fill=bg, outline=c["border"], width=1)
            fg = c["fg"]
            icon_c = fg
            kbg, kfg = c["keycap_bg"], c["keycap_fg"]
        x = self._pad[0]
        if c["icon"]:
            ICONS[c["icon"]](self, x, (h - self._icon_size) / 2,
                             self._icon_size, icon_c)
            x += self._icon_size + self._gap
        if c["text"]:
            self.create_text(x, h / 2, text=c["text"], font=c["font"],
                             fill=fg, anchor="w")
        if c["keycap"]:
            kx = self._width(c) - self._pad[1] - self._keycap_w
            rounded(self, kx, (h - 20) / 2, kx + self._keycap_w,
                    (h + 20) / 2, 4, fill=kbg or "")
            self.create_text(kx + self._keycap_w / 2, h / 2, text=c["keycap"],
                             font=f_mono(10, True), fill=kfg)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._paint()

    def px_width(self) -> int:
        return int(self["width"])

    def set_text(self, text: str) -> None:
        cfg = dict(self._cfg, text=text)
        self._apply(cfg)

    def set_icon(self, icon: str | None) -> None:
        cfg = dict(self._cfg, icon=icon)
        self._apply(cfg)

    def set_state(self, *, bg: str | None = None, fg: str | None = None,
                  border: str | None = ..., icon: str | None = None) -> None:
        cfg = dict(self._cfg)
        if bg is not None:
            cfg["bg"] = bg
        if fg is not None:
            cfg["fg"] = fg
        if border is not ...:
            cfg["border"] = border
        if icon is not None:
            cfg["icon"] = icon
        self._apply(cfg)


class RPill(tk.Canvas):
    """顶栏状态药丸：色点 + 状态文字（圆角 13 胶囊）。"""

    def __init__(self, master, *, backdrop: str, bg: str, border: str,
                 fg: str, text: str, dot: str, font: tuple | None = None):
        self._font = font or f_cn(12)
        self._style = dict(backdrop=backdrop, bg=bg, border=border, fg=fg)
        self._text, self._dot = text, dot
        super().__init__(master, height=26, highlightthickness=0,
                         bg=backdrop)
        self._paint()

    def _width(self) -> int:
        return round(10 + 8 + 6 + measure(self._font, self._text) + 11)

    def _paint(self) -> None:
        s = self._style
        self.delete("all")
        w = self._width()
        self.config(width=w)
        rounded(self, 1, 1, w - 1, 25, 13, fill=s["bg"], outline=s["border"],
                width=1)
        self.create_oval(10, 9, 18, 17, fill=self._dot, width=0)
        self.create_text(24, 13, text=self._text, font=self._font,
                         fill=s["fg"], anchor="w")

    def set(self, text: str | None = None, dot: str | None = None) -> None:
        if text is not None and text != self._text:
            self._text = text
            self._paint()
        if dot is not None:
            self._dot = dot
            self._paint()

    def px_width(self) -> int:
        return int(self["width"])
