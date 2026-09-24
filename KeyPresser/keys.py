"""Таблица клавиш.

Ключевой момент: клавиша кодируется ФИЗИЧЕСКИМ скан-кодом (PS/2 set 1), а не
символом. Скан-код не зависит от раскладки: шаг "w" нажмёт ту же физическую
клавишу (на ней написано "ц") и при русской раскладке, и при US. Имена в
таблице -- просто ярлыки US-раскладки для позиций клавиш.

Формы записи клавиши:
    w, space, alt, ralt, f5, num7   - по имени
    sc:0x11 / sc:17                 - напрямую скан-код
    sc:e0:0x35                      - скан-код с префиксом E0 (extended)
    vk:0x41                         - напрямую virtual-key код
"""

import i18n

MAPVK_VK_TO_VSC = 0

# name -> (vk, scancode, extended)
_TABLE: dict[str, tuple[int, int, bool]] = {}


def _add(name: str, vk: int, sc: int, ext: bool = False) -> None:
    _TABLE[name] = (vk, sc, ext)


# --- ряд цифр / первый ряд -------------------------------------------------
_add("esc", 0x1B, 0x01)
for _i, _d in enumerate("1234567890"):
    _add(_d, ord(_d), 0x02 + _i)
_add("-", 0xBD, 0x0C)
_add("=", 0xBB, 0x0D)
_add("backspace", 0x08, 0x0E)
_add("tab", 0x09, 0x0F)

# --- буквенные ряды (позиции QWERTY) --------------------------------------
_ROW_Q = [("q", 0x10), ("w", 0x11), ("e", 0x12), ("r", 0x13), ("t", 0x14),
          ("y", 0x15), ("u", 0x16), ("i", 0x17), ("o", 0x18), ("p", 0x19),
          ("[", 0x1A), ("]", 0x1B)]
_ROW_A = [("a", 0x1E), ("s", 0x1F), ("d", 0x20), ("f", 0x21), ("g", 0x22),
          ("h", 0x23), ("j", 0x24), ("k", 0x25), ("l", 0x26), (";", 0x27),
          ("'", 0x28), ("`", 0x29)]
_ROW_Z = [("\\", 0x2B), ("z", 0x2C), ("x", 0x2D), ("c", 0x2E), ("v", 0x2F),
          ("b", 0x30), ("n", 0x31), ("m", 0x32), (",", 0x33), (".", 0x34),
          ("/", 0x35)]
_OEM_VK = {"[": 0xDB, "]": 0xDD, ";": 0xBA, "'": 0xDE, "`": 0xC0,
           "\\": 0xDC, ",": 0xBC, ".": 0xBE, "/": 0xBF}
for _name, _sc in _ROW_Q + _ROW_A + _ROW_Z:
    _add(_name, _OEM_VK.get(_name, ord(_name.upper())), _sc)

_add("enter", 0x0D, 0x1C)

# --- модификаторы ----------------------------------------------------------
_add("lctrl", 0xA2, 0x1D)
_add("rctrl", 0xA3, 0x1D, True)
_add("lshift", 0xA0, 0x2A)
_add("rshift", 0xA1, 0x36)
_add("lalt", 0xA4, 0x38)
_add("ralt", 0xA5, 0x38, True)
_add("ctrl", 0x11, 0x1D)          # общий = левый
_add("shift", 0x10, 0x2A)
_add("alt", 0x12, 0x38)
_add("lwin", 0x5B, 0x5B, True)
_add("rwin", 0x5C, 0x5C, True)
_add("apps", 0x5D, 0x5D, True)

_add("space", 0x20, 0x39)
_add("capslock", 0x14, 0x3A)

# --- функциональные -------------------------------------------------------
for _i in range(1, 11):
    _add(f"f{_i}", 0x6F + _i, 0x3A + _i)      # F1=0x3B ... F10=0x44
_add("f11", 0x7A, 0x57)
_add("f12", 0x7B, 0x58)
for _i in range(13, 25):
    _add(f"f{_i}", 0x6F + _i, 0x64 + (_i - 13))

_add("numlock", 0x90, 0x45)
_add("scrolllock", 0x91, 0x46)
_add("pause", 0x13, 0x45)
_add("printscreen", 0x2C, 0x37, True)

# --- numpad ---------------------------------------------------------------
for _name, _vk, _sc in [("num7", 0x67, 0x47), ("num8", 0x68, 0x48), ("num9", 0x69, 0x49),
                        ("num-", 0x6D, 0x4A), ("num4", 0x64, 0x4B), ("num5", 0x65, 0x4C),
                        ("num6", 0x66, 0x4D), ("num+", 0x6B, 0x4E), ("num1", 0x61, 0x4F),
                        ("num2", 0x62, 0x50), ("num3", 0x63, 0x51), ("num0", 0x60, 0x52),
                        ("num.", 0x6E, 0x53), ("num*", 0x6A, 0x37)]:
    _add(_name, _vk, _sc)
_add("num/", 0x6F, 0x35, True)
_add("numenter", 0x0D, 0x1C, True)

# --- блок навигации (все extended) ----------------------------------------
for _name, _vk, _sc in [("home", 0x24, 0x47), ("up", 0x26, 0x48), ("pageup", 0x21, 0x49),
                        ("left", 0x25, 0x4B), ("right", 0x27, 0x4D), ("end", 0x23, 0x4F),
                        ("down", 0x28, 0x50), ("pagedown", 0x22, 0x51),
                        ("insert", 0x2D, 0x52), ("delete", 0x2E, 0x53)]:
    _add(_name, _vk, _sc, True)

MOUSE_BUTTONS = ("mouse_left", "mouse_right", "mouse_middle")
MOUSE_LABEL_KEYS = {"mouse_left": "mouse.left", "mouse_right": "mouse.right",
                    "mouse_middle": "mouse.middle"}

MODIFIER_NAMES = ("ctrl", "shift", "alt", "lctrl", "rctrl",
                  "lshift", "rshift", "lalt", "ralt", "lwin", "rwin")

ALIASES = {
    "escape": "esc", "return": "enter", "spacebar": "space", "пробел": "space",
    "control": "ctrl", "menu": "alt", "option": "alt", "altgr": "ralt",
    "del": "delete", "ins": "insert", "pgup": "pageup", "pgdn": "pagedown",
    "pgdown": "pagedown", "prior": "pageup", "next": "pagedown",
    "bs": "backspace", "caps": "capslock", "win": "lwin", "super": "lwin",
    "plus": "=", "minus": "-", "comma": ",", "period": ".", "slash": "/",
    "backslash": "\\", "grave": "`", "tilde": "`", "semicolon": ";",
    "apostrophe": "'", "bracketleft": "[", "bracketright": "]",
    "prtsc": "printscreen", "printscr": "printscreen",
    "lmb": "mouse_left", "rmb": "mouse_right", "mmb": "mouse_middle",
}

# Что написано на той же физической клавише в ЙЦУКЕН -- только для подсказок в GUI.
RU_LEGEND = {
    "q": "й", "w": "ц", "e": "у", "r": "к", "t": "е", "y": "н", "u": "г",
    "i": "ш", "o": "щ", "p": "з", "[": "х", "]": "ъ",
    "a": "ф", "s": "ы", "d": "в", "f": "а", "g": "п", "h": "р", "j": "о",
    "k": "л", "l": "д", ";": "ж", "'": "э", "`": "ё",
    "z": "я", "x": "ч", "c": "с", "v": "м", "b": "и", "n": "т", "m": "ь",
    ",": "б", ".": "ю", "/": ".",
}

# Обратные карты. tkinter на Windows кладёт в event.keycode virtual-key код, а
# низкоуровневый хук отдаёт сразу скан-код -- обе записи не зависят от раскладки.
_VK_TO_NAME: dict[int, str] = {}
for _n, (_vk, _sc, _ext) in _TABLE.items():
    if _n in ("ctrl", "shift", "alt", "pause", "numenter"):
        continue
    _VK_TO_NAME.setdefault(_vk, _n)
_VK_TO_NAME[0x10] = "lshift"
_VK_TO_NAME[0x11] = "lctrl"
_VK_TO_NAME[0x12] = "lalt"

_SC_TO_NAME: dict[tuple[int, bool], str] = {}
for _n, (_vk, _sc, _ext) in _TABLE.items():
    if _n in ("ctrl", "shift", "alt", "pause", "numenter"):
        continue
    _SC_TO_NAME.setdefault((_sc, _ext), _n)


def normalize(name: str) -> str:
    n = name.strip().lower()
    return ALIASES.get(n, n)


def _parse_raw(spec: str) -> tuple[int, int, bool] | None:
    """'sc:0x11', 'sc:e0:0x35', 'vk:0x41' -> (vk, sc, ext) или None."""
    s = spec.strip().lower().replace(" ", "")
    if not (s.startswith("sc:") or s.startswith("vk:")):
        return None
    kind, _, rest = s.partition(":")
    ext = False
    if rest.startswith("e0:"):
        ext, rest = True, rest[3:]
    try:
        val = int(rest, 16) if rest.startswith("0x") else int(rest, 10)
    except ValueError:
        raise ValueError(i18n.t("keys.bad_code", spec=spec))
    if not 1 <= val <= 0xFF:
        raise ValueError(i18n.t("keys.range"))
    if kind == "vk":
        known = _VK_TO_NAME.get(val)
        if known:
            return _TABLE[known]
        return (val, 0, ext)      # sc=0 -> sender отправит по VK
    return (0, val, ext)


def is_known(name: str) -> bool:
    n = normalize(name)
    if n in _TABLE or n in MOUSE_BUTTONS:
        return True
    try:
        return _parse_raw(n) is not None
    except ValueError:
        return False


def code_of(name: str) -> tuple[int, int, bool]:
    """Имя или сырой код -> (vk, scancode, extended)."""
    n = normalize(name)
    if n in _TABLE:
        return _TABLE[n]
    raw = _parse_raw(n)
    if raw:
        return raw
    raise KeyError(i18n.t("keys.unknown", name=name))


def vk_of(name: str) -> int:
    return code_of(name)[0]


def scan_of(name: str) -> tuple[int, bool]:
    _vk, sc, ext = code_of(name)
    return sc, ext


def describe(name: str) -> str:
    """'w' -> 'w [sc 11 / ц]' -- что реально уйдёт в игру."""
    n = normalize(name)
    if n in MOUSE_BUTTONS:
        return i18n.t(MOUSE_LABEL_KEYS[n])
    try:
        vk, sc, ext = code_of(n)
    except KeyError:
        return f"{name} [?]"
    code = f"sc {sc:02X}{'e' if ext else ''}" if sc else f"vk {vk:02X}"
    ru = RU_LEGEND.get(n)
    return f"{n} [{code}{' / ' + ru if ru else ''}]"


def name_from_vk(vk: int) -> str | None:
    return _VK_TO_NAME.get(vk)


def name_from_scan(sc: int, ext: bool) -> str:
    """Скан-код из низкоуровневого хука -> имя (или сырая запись sc:...)."""
    name = _SC_TO_NAME.get((sc, ext))
    if name:
        return name
    return f"sc:e0:0x{sc:02x}" if ext else f"sc:0x{sc:02x}"


def parse_combo(spec: str) -> tuple[list[str], str]:
    """'ctrl+alt+space' -> (['ctrl','alt'], 'space')."""
    raw = spec.strip()
    if not raw:
        raise ValueError(i18n.t("keys.empty"))
    if raw in ("+", "="):
        return [], "="
    parts = [p for p in raw.replace(" ", "").split("+") if p]
    if not parts:
        raise ValueError(i18n.t("keys.empty"))
    *mods, main = [normalize(p) for p in parts]
    for m in mods:
        if m not in MODIFIER_NAMES:
            raise ValueError(i18n.t("keys.not_modifier", name=m))
    if not is_known(main):
        raise ValueError(i18n.t("keys.unknown", name=main))
    return mods, main


def format_combo(mods: list[str], main: str) -> str:
    return "+".join([*mods, main])


def describe_combo(spec: str) -> str:
    try:
        mods, main = parse_combo(spec)
    except Exception:
        return spec
    return " + ".join([*mods, describe(main)])


def all_key_names() -> list[str]:
    return sorted(_TABLE) + list(MOUSE_BUTTONS)
