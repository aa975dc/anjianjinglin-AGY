"""Движок воспроизведения последовательности в отдельном потоке."""

import random
import threading
import time
from dataclasses import dataclass, field

import i18n
import keys
import sender
import winutil

MODE_FOREGROUND = "foreground"   # только если окно игры активно
MODE_ACTIVATE = "activate"       # сначала активировать окно, потом жать
MODE_POST = "post"               # PostMessage в окно, в фоне

TICK = 0.01                      # шаг прерываемого сна -> стоп срабатывает <20 мс


@dataclass
class RunConfig:
    steps: list[dict] = field(default_factory=list)
    mode: str = MODE_FOREGROUND
    target_title: str = ""
    target_hwnd: int = 0
    cycles: int = 0                  # 0 = бесконечно
    cycle_delay_ms: int = 500
    jitter_pct: int = 0
    start_delay_ms: int = 1000


class Engine:
    """on_log(str), on_state(str), on_step(idx|None), on_finish() -- зовутся из рабочего потока."""

    def __init__(self, on_log=None, on_state=None, on_step=None, on_finish=None,
                 on_error=None):
        self._log = on_log or (lambda m: None)
        self._state = on_state or (lambda s: None)
        self._on_step = on_step or (lambda i: None)
        self._on_finish = on_finish or (lambda: None)
        self._on_error = on_error or (lambda m: None)   # отказ отправки -> в GUI
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self._held: list[str] = []
        self._held_lock = threading.Lock()
        self._cfg: RunConfig | None = None

    # --- управление --------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def is_paused(self) -> bool:
        return self.is_running and not self._resume.is_set()

    def start(self, cfg: RunConfig) -> bool:
        if self.is_running:
            return False
        active = [s for s in cfg.steps if s.get("enabled", True)]
        if not active:
            self._log(i18n.t("eng.no_steps"))
            return False
        for s in active:                       # проверяем всё до старта
            try:
                keys.parse_combo(s["key"])
            except Exception as exc:
                self._log(i18n.t("eng.step_bad", key=s.get("key"), err=exc))
                return False
        # игры опрашивают клавиатуру раз в кадр -- слишком короткий тап теряется
        shortest = min((int(s.get("hold_ms", 90)) for s in active), default=90)
        if shortest < 50:
            self._log(i18n.t("eng.hold_hint", ms=shortest))
        self._cfg = cfg
        self._stop.clear()
        self._resume.set()
        self._thread = threading.Thread(target=self._run, name="engine", daemon=True)
        self._thread.start()
        return True

    def stop(self, join: bool = False) -> None:
        self._stop.set()
        self._resume.set()
        if join and self._thread:
            self._thread.join(timeout=2.0)

    def toggle_pause(self) -> bool:
        """True -> встали на паузу, False -> продолжили."""
        if not self.is_running:
            return False
        if self._resume.is_set():
            self._resume.clear()
            self._state(i18n.t("status.paused"))
            self._log(i18n.t("eng.paused"))
            return True
        self._resume.set()
        self._state(i18n.t("status.running"))
        self._log(i18n.t("eng.resumed"))
        return False

    def force_release(self) -> list[str]:
        """Аварийно отпустить все зажатые клавиши, даже если поток ещё жив.

        Вызывается из GUI-потока, когда engine.stop(join=True) не успел
        завершить рабочий поток (он мог зависнуть в системном вызове). Работает
        по списку self._held и не зависит от того, жив ли поток.
        """
        names = self._held_snapshot_reversed()
        if names:
            sender.release_all(names)
            self._log(i18n.t("eng.force_release", names=", ".join(names)))
        with self._held_lock:
            self._held.clear()
        return names

    # --- учёт зажатых клавиш (потокобезопасно) ----------------------------
    def _held_add(self, names) -> None:
        with self._held_lock:
            for name in names:
                if name not in self._held:
                    self._held.append(name)

    def _held_discard(self, names) -> None:
        with self._held_lock:
            for name in names:
                if name in self._held:
                    self._held.remove(name)

    def _held_snapshot_reversed(self) -> list[str]:
        with self._held_lock:
            return list(reversed(self._held))

    # --- внутреннее -------------------------------------------------------
    def _sleep(self, seconds: float) -> bool:
        """Прерываемый сон. False -> нас попросили остановиться."""
        end = time.perf_counter() + seconds
        while True:
            if self._stop.is_set():
                return False
            left = end - time.perf_counter()
            if left <= 0:
                return True
            time.sleep(min(TICK, left))

    def _wait_resume(self) -> bool:
        while not self._resume.is_set():
            if self._stop.is_set():
                return False
            time.sleep(TICK)
        return not self._stop.is_set()

    def _jitter(self, ms: float) -> float:
        pct = (self._cfg.jitter_pct if self._cfg else 0) / 100.0
        if pct <= 0 or ms <= 0:
            return ms
        return max(0.0, ms * (1.0 + random.uniform(-pct, pct)))

    def _resolve_target(self) -> int:
        cfg = self._cfg
        if cfg.target_hwnd and winutil.is_window(cfg.target_hwnd):
            return cfg.target_hwnd
        hwnd = winutil.find_window(cfg.target_title) if cfg.target_title else 0
        if hwnd:
            cfg.target_hwnd = hwnd
        return hwnd or 0

    def _ensure_ready(self, hwnd: int) -> bool:
        """Дождаться, что можно жать: окно активно (или активировать его)."""
        cfg = self._cfg
        if cfg.mode == MODE_POST:
            return bool(hwnd)
        if not hwnd:
            return True                      # цель не задана -- жмём в активное окно
        if cfg.mode == MODE_ACTIVATE and not winutil.is_foreground(hwnd):
            winutil.activate(hwnd)
            if not self._sleep(0.15):
                return False
        if winutil.is_foreground(hwnd):
            return True
        self._state(i18n.t("status.waiting"))
        self._log(i18n.t("eng.window_inactive"))
        while not winutil.is_foreground(hwnd):
            if not self._sleep(0.2):
                return False
            if not winutil.is_window(hwnd):
                self._log(i18n.t("eng.window_closed"))
                return False
        self._state(i18n.t("status.running"))
        self._log(i18n.t("eng.window_active"))
        return True

    def _tap_interruptible(self, mods: list[str], main: str, hold_ms: int) -> None:
        """Аналог sender.tap(), но удержание прерывается событием _stop.

        sender.tap() держит паузу обычным time.sleep() и не замечает _stop --
        из-за этого F3 во время удержания не срабатывал (ждал hold_ms), а при
        аварийном завершении клавиша оставалась зажатой в системе. Здесь
        ожидание идёт кусочками через self._sleep (шаг TICK = 10 мс).

        Гарантии те же, что у sender.tap(): что бы ни случилось (нормальное
        завершение, _stop, исключение) -- нажатые клавиши отпускаются в
        finally. Дополнительно каждая успешно нажатая клавиша регистрируется в
        self._held (ровно в момент key_down, а не заранее), чтобы _run()/
        force_release() могли отпустить её при аварии, но при этом НЕ слать
        key_up по клавише, которую нажать не успели.
        """
        pressed: list[str] = []               # 精确镜像 self._held
        try:
            for m in mods:
                sender.key_down(m)
                pressed.append(m)
                self._held_add([m])           # 按下一个才登记一个
                if not self._sleep(sender.MOD_GAP_S):
                    return
            sender.key_down(main)
            pressed.append(main)
            self._held_add([main])
            self._sleep(max(hold_ms, 1) / 1000.0)
        finally:
            for name in reversed(pressed):    # 逆序松开实际按下的键
                try:
                    sender.key_up(name)
                except Exception:
                    pass
            self._held_discard(pressed)

    def _fire(self, step: dict, hwnd: int) -> None:
        mods, main = keys.parse_combo(step["key"])
        hold = int(self._jitter(step.get("hold_ms", 40)))
        action = step.get("action", "tap")
        if self._cfg.mode == MODE_POST:
            sender.post_tap(hwnd, mods, main, hold)
            return
        if action == "down":
            sender.hold_down(mods, main)
            self._held_add([*mods, main])
        elif action == "up":
            sender.release(mods, main)
            self._held_discard([*mods, main])
        else:
            self._tap_interruptible(mods, main, hold)

    def _run(self) -> None:
        cfg = self._cfg
        with self._held_lock:
            self._held = []
        try:
            hwnd = self._resolve_target()
            if cfg.target_title and not hwnd:
                self._log(i18n.t("eng.window_not_found", title=cfg.target_title))
                return
            if cfg.mode == MODE_POST and not hwnd:
                self._log(i18n.t("eng.post_needs_window"))
                return

            if cfg.start_delay_ms > 0:
                self._state(i18n.t("status.starting"))
                left = cfg.start_delay_ms
                while left > 0:
                    self._log(i18n.t("eng.countdown", sec=f"{left/1000:.1f}"))
                    if not self._sleep(min(0.5, left / 1000)):
                        return
                    left -= 500
            self._state(i18n.t("status.running"))
            self._log(i18n.t("eng.started"))

            cycle = 0
            active = [(i, s) for i, s in enumerate(cfg.steps) if s.get("enabled", True)]
            while not self._stop.is_set():
                cycle += 1
                if cfg.cycles:
                    self._log(i18n.t("eng.cycle", i=cycle, n=cfg.cycles))
                for idx, step in active:
                    for rep in range(max(1, int(step.get("repeat", 1)))):
                        if self._stop.is_set() or not self._wait_resume():
                            return
                        if not self._ensure_ready(hwnd):
                            return
                        self._on_step(idx)
                        try:
                            self._fire(step, hwnd)
                        except Exception as exc:
                            self._log(i18n.t("eng.step_failed", n=idx + 1, key=step["key"], err=exc))
                            self._on_error(str(exc))
                            return
                        delay = self._jitter(step.get("delay_ms", 100))
                        if delay and not self._sleep(delay / 1000.0):
                            return
                self._on_step(None)
                if cfg.cycles and cycle >= cfg.cycles:
                    self._log(i18n.t("eng.done", n=cycle))
                    return
                if cfg.cycle_delay_ms and not self._sleep(
                        self._jitter(cfg.cycle_delay_ms) / 1000.0):
                    return
        finally:
            names = self._held_snapshot_reversed()
            if names:
                sender.release_all(names)
                with self._held_lock:
                    self._held.clear()
            self._on_step(None)
            self._state(i18n.t("status.stopped"))
            self._log(i18n.t("eng.stopped"))
            self._on_finish()
