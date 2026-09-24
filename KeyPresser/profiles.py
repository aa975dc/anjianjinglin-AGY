"""Профили и настройки: чтение/запись JSON, валидация шагов."""

import json
import os
import sys
from pathlib import Path

import engine
import i18n
import keys

# В собранном exe __file__ указывает во временную распаковку PyInstaller,
# поэтому профили держим рядом с самим exe.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent
PROFILE_DIR = APP_DIR / "profiles"
SETTINGS_DIR = Path(os.environ.get("APPDATA", APP_DIR)) / "KeyPresser"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_HOTKEYS = {
    "run_toggle": "f1",       # F1 -- запуск скрипта (start)
    "pause": "f2",            # F2 -- пауза/продолжить
    "stop": "f3",             # F3 -- остановка скрипта
    "record_toggle": "f9",    # запуск/остановка записи
    "minimize": "f4",         # свернуть главное окно
}

HOTKEY_LABEL_KEYS = {
    "run_toggle": "hk.run_toggle",
    "pause": "hk.pause",
    "stop": "hk.stop",
    "record_toggle": "hk.record_toggle",
    "minimize": "hk.minimize",
}

# Диапазоны значений, которые разрешено передавать в движок.
# Один источник правды: любой GUI обязан прогонять конфиг через
# validate_run_config(), иначе можно передать hold_ms=999999999 и залипнуть.
HOLD_MS_RANGE = (1, 60_000)
DELAY_MS_RANGE = (0, 3_600_000)
CYCLES_RANGE = (0, 1_000_000)
CYCLE_DELAY_MS_RANGE = (0, 3_600_000)
JITTER_PCT_RANGE = (0, 90)
START_DELAY_MS_RANGE = (0, 60_000)


def hotkey_label(action: str) -> str:
    return i18n.t(HOTKEY_LABEL_KEYS.get(action, action))


def default_step(key: str = "space") -> dict:
    return {"key": key, "action": "tap", "hold_ms": 90, "delay_ms": 500,
            "repeat": 1, "enabled": True, "comment": ""}


def default_config() -> dict:
    return {
        "version": 1,
        "language": i18n.DEFAULT_LANGUAGE,
        "steps": [],
        "mode": engine.MODE_FOREGROUND,
        "target_title": "",
        "cycles": 0,
        "cycle_delay_ms": 500,
        "jitter_pct": 0,
        "start_delay_ms": 1000,
        "hotkeys": dict(DEFAULT_HOTKEYS),
        "record_mouse": True,
        "record_tail_delay_ms": 200,
        "record_replace": True,
    }


def _as_int(value, fallback: int, low: int = 0, high: int = 3_600_000) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return fallback


def normalize_step(raw: dict) -> dict | None:
    """Привести шаг из файла к валидному виду. None -- шаг битый."""
    if not isinstance(raw, dict):
        return None
    key = str(raw.get("key", "")).strip()
    if not key:
        return None
    try:
        keys.parse_combo(key)
    except Exception:
        return None
    action = str(raw.get("action", "tap")).lower()
    if action not in ("tap", "down", "up"):
        action = "tap"
    return {
        "key": key,
        "action": action,
        "hold_ms": _as_int(raw.get("hold_ms"), 90, *HOLD_MS_RANGE),
        "delay_ms": _as_int(raw.get("delay_ms"), 100, *DELAY_MS_RANGE),
        "repeat": _as_int(raw.get("repeat"), 1, 1, 100_000),
        "enabled": bool(raw.get("enabled", True)),
        "comment": str(raw.get("comment", ""))[:120],
    }


def normalize_config(raw: dict) -> dict:
    cfg = default_config()
    if not isinstance(raw, dict):
        return cfg
    lang = str(raw.get("language", i18n.DEFAULT_LANGUAGE))
    cfg["language"] = lang if lang in i18n.LANGUAGES else i18n.DEFAULT_LANGUAGE
    cfg["steps"] = [s for s in (normalize_step(x) for x in raw.get("steps", [])) if s]
    mode = str(raw.get("mode", cfg["mode"]))
    if mode in (engine.MODE_FOREGROUND, engine.MODE_ACTIVATE, engine.MODE_POST):
        cfg["mode"] = mode
    cfg["target_title"] = str(raw.get("target_title", ""))[:200]
    cfg["cycles"] = _as_int(raw.get("cycles"), 0, 0, 1_000_000)
    cfg["cycle_delay_ms"] = _as_int(raw.get("cycle_delay_ms"), 500, 0)
    cfg["jitter_pct"] = _as_int(raw.get("jitter_pct"), 0, 0, 90)
    cfg["start_delay_ms"] = _as_int(raw.get("start_delay_ms"), 1000, 0, 60_000)
    hk = raw.get("hotkeys", {})
    if isinstance(hk, dict):
        for action, default in DEFAULT_HOTKEYS.items():
            combo = str(hk.get(action, default)).strip()
            if combo:
                try:
                    keys.parse_combo(combo)
                    cfg["hotkeys"][action] = combo
                except Exception:
                    pass
            else:
                cfg["hotkeys"][action] = ""
    cfg["record_mouse"] = bool(raw.get("record_mouse", True))
    cfg["record_tail_delay_ms"] = _as_int(raw.get("record_tail_delay_ms"), 200, 0)
    cfg["record_replace"] = bool(raw.get("record_replace", True))
    return cfg


def validate_run_config(cfg: engine.RunConfig) -> tuple[engine.RunConfig, list[str]]:
    """Привести RunConfig к безопасным диапазонам перед запуском движка.

    Возвращает (исправленный конфиг, список описаний правок). Пустой список
    -> правок не было.

    Зачем: GUI-слои не должны каждый сам помнить про ограничения -- иначе один
    из них однажды снова пропустит hold_ms напрямую в sender.tap() и залипнет
    нажатой клавишей. Здесь единственный источник правды.
    """
    notes: list[str] = []

    def clamp(field: str, value, low: int, high: int) -> int:
        try:
            iv = int(value)
        except (TypeError, ValueError):
            notes.append(f"{field}={value!r} → {low}")
            return low
        if iv < low:
            notes.append(f"{field}={iv} → {low}")
            return low
        if iv > high:
            notes.append(f"{field}={iv} → {high}")
            return high
        return iv

    steps: list[dict] = []
    for i, raw in enumerate(cfg.steps):
        step = dict(raw)
        step["hold_ms"] = clamp(f"steps[{i}].hold_ms", raw.get("hold_ms", 90),
                                *HOLD_MS_RANGE)
        step["delay_ms"] = clamp(f"steps[{i}].delay_ms", raw.get("delay_ms", 100),
                                 *DELAY_MS_RANGE)
        steps.append(step)

    result = engine.RunConfig(
        steps=steps,
        mode=cfg.mode,
        target_title=cfg.target_title,
        target_hwnd=cfg.target_hwnd,
        cycles=clamp("cycles", cfg.cycles, *CYCLES_RANGE),
        cycle_delay_ms=clamp("cycle_delay_ms", cfg.cycle_delay_ms,
                             *CYCLE_DELAY_MS_RANGE),
        jitter_pct=clamp("jitter_pct", cfg.jitter_pct, *JITTER_PCT_RANGE),
        start_delay_ms=clamp("start_delay_ms", cfg.start_delay_ms,
                             *START_DELAY_MS_RANGE),
    )
    return result, notes


def load(path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return normalize_config(json.load(fh))


def save(path, cfg: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    try:
        return load(SETTINGS_FILE)
    except Exception:
        return default_config()


def save_settings(cfg: dict) -> None:
    try:
        save(SETTINGS_FILE, cfg)
    except Exception:
        pass


def list_profiles() -> list[Path]:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(PROFILE_DIR.glob("*.json"))
