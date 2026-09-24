"""轻量界面动效：状态点呼吸 / 一次性脉冲 / 窗口淡入淡出。

实现纪律（为"不卡顿、不影响正常运行"而定）：
* 纯 tkinter after 链：零线程、零依赖，绝不触碰引擎与热键；
* 每个动效同一时刻只有一条 after 链，每帧只改 1 个控件属性；
* 窗口不可见（隐藏/最小化）时跳过绘制、降到 5fps 空转，不浪费 CPU；
* 所有定时器都能 stop()/cancel_fade() 取消 —— on_close 必须逐一清理。
"""

import math
import tkinter as tk


def _parse(color: str) -> tuple[float, float, float]:
    """'#rrggbb' 或 '#rgb' -> (r, g, b)，各分量 0~1。"""
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        *(max(0, min(255, round(v * 255))) for v in rgb))


def _lerp(a, b, t: float):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


class Breath:
    """让一个支持颜色属性的控件（如 ttk.Label 的 foreground）做动效。

    set_static / breathe / pulse 互相切换时旧链自动作废（token 失效），
    同一时刻只有一条 after 链，不会叠加、不会泄漏。
    """

    FPS = 30

    def __init__(self, widget, key: str = "foreground"):
        self._w = widget
        self._key = key
        self._after = None
        self._token = 0

    # ------------------------------------------------------------- 对外 --
    def set_static(self, color: str) -> None:
        """停止动画，固定为单色。"""
        self._cancel()
        self._paint(_parse(color))

    def breathe(self, c1: str, c2: str, period_ms: int) -> None:
        """在两色之间循环呼吸（余弦缓动）。"""
        a, b = _parse(c1), _parse(c2)
        frames = max(2, round(period_ms * self.FPS / 1000))
        self._cancel()

        def color_at(i: int):
            phase = (i % frames) / frames
            return _lerp(a, b, (1 - math.cos(2 * math.pi * phase)) / 2)

        self._loop(color_at, frames, done=None, infinite=True)

    def pulse(self, c_from: str, c_to: str, ms: int, then=None) -> None:
        """一次性脉冲：c_from 渐变到 c_to（先快后慢），结束后回调 then。"""
        a, b = _parse(c_from), _parse(c_to)
        frames = max(1, round(ms * self.FPS / 1000))
        self._cancel()
        self._loop(lambda i: _lerp(a, b, 1 - (1 - i / frames) ** 2),
                   frames, done=then)

    def stop(self) -> None:
        """取消动画链（保持当前颜色）。on_close 时必须调用。"""
        self._cancel()

    # ------------------------------------------------------------- 内部 --
    def _cancel(self) -> None:
        self._token += 1
        if self._after is not None:
            try:
                self._w.after_cancel(self._after)
            except tk.TclError:
                pass
            self._after = None

    def _paint(self, rgb) -> None:
        try:
            if self._w.winfo_ismapped():
                self._w.config(**{self._key: _hex(rgb)})
        except tk.TclError:
            pass

    def _loop(self, color_at, frames: int, done, infinite: bool = False) -> None:
        token = self._token
        interval = 1000 // self.FPS

        def step(i: int = 0) -> None:
            if token != self._token:
                return
            try:
                if not self._w.winfo_exists():
                    self._after = None
                    return
                mapped = self._w.winfo_ismapped()
            except tk.TclError:
                self._after = None
                return
            if mapped:
                self._paint(color_at(i))
            if infinite or i + 1 < frames:
                # 不可见时降频空转（不绘制），可见时全速
                self._after = self._w.after(interval if mapped else 200,
                                            lambda: step(i + 1))
            else:
                self._after = None
                if done:
                    done()

        self._after = self._w.after(interval, step)


def fade(win, a_from: float, a_to: float, ms: int = 140,
         on_done=None, fps: int = 30) -> None:
    """把 toplevel 窗口透明度从 a_from 渐变到 a_to，结束后回调 on_done。

    系统不支持 alpha（罕见）时直接执行 on_done 兜底；重复调用会先
    取消上一次未完成的淡入淡出。after id 存在 win._fx_fade_after 上。
    """
    cancel_fade(win)
    try:
        win.attributes("-alpha", a_from)
    except tk.TclError:
        if on_done:
            on_done()
        return
    steps = max(1, round(ms * fps / 1000))
    state = {"i": 0}

    def step() -> None:
        state["i"] += 1
        t = min(1.0, state["i"] / steps)
        try:
            if not win.winfo_exists():
                win._fx_fade_after = None
                return
            win.attributes("-alpha", a_from + (a_to - a_from) * t)
        except tk.TclError:
            win._fx_fade_after = None
            return
        if t < 1.0:
            win._fx_fade_after = win.after(1000 // fps, step)
        else:
            win._fx_fade_after = None
            if on_done:
                on_done()

    win._fx_fade_after = win.after(1000 // fps, step)


def cancel_fade(win) -> None:
    """取消窗口上未完成的淡入淡出（防止隐藏途中被唤回时两条链打架）。"""
    aid = getattr(win, "_fx_fade_after", None)
    if aid:
        try:
            win.after_cancel(aid)
        except tk.TclError:
            pass
        win._fx_fade_after = None
