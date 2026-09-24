"""Генератор icon.ico (без сторонних библиотек).

Рисует «клавишу» с буквой K в четырёх размерах и пишет multi-size ICO.
Запуск: python make_icon.py
"""

import struct
from pathlib import Path

BG = (0x1F, 0x6F, 0xEB)       # синий, RGB
BG_DARK = (0x14, 0x4C, 0xA6)  # тень нижней грани "клавиши"
FG = (0xFF, 0xFF, 0xFF)       # буква
SIZES = (16, 24, 32, 48)


def _rounded(x: int, y: int, n: int, radius: float) -> bool:
    """Точка внутри скруглённого квадрата n x n?"""
    cx = min(max(x, radius), n - 1 - radius)
    cy = min(max(y, radius), n - 1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2 + 0.5


def _segment(x: int, y: int, x0: float, y0: float, x1: float, y1: float,
             width: float) -> bool:
    """Точка ближе, чем width/2, к отрезку (x0,y0)-(x1,y1)?"""
    dx, dy = x1 - x0, y1 - y0
    length2 = dx * dx + dy * dy
    tt = 0.0 if length2 == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / length2))
    px, py = x0 + tt * dx, y0 + tt * dy
    return (x - px) ** 2 + (y - py) ** 2 <= (width / 2) ** 2


def render(n: int) -> bytes:
    """32bpp BGRA, снизу вверх (как требует ICO)."""
    s = n / 32.0                     # масштаб от эталонных 32 px
    stroke = max(1.6, 3.0 * s)
    rows = []
    for y in range(n - 1, -1, -1):
        row = bytearray()
        for x in range(n):
            inside = _rounded(x, y, n, 6 * s)
            letter = (
                _segment(x, y, 11 * s, 7 * s, 11 * s, 24 * s, stroke) or
                _segment(x, y, 12 * s, 16 * s, 21 * s, 7.5 * s, stroke) or
                _segment(x, y, 12 * s, 16 * s, 21 * s, 24 * s, stroke)
            )
            if not inside:
                row += b"\x00\x00\x00\x00"
            elif letter:
                row += bytes((FG[2], FG[1], FG[0], 0xFF))
            else:
                c = BG_DARK if y > n - 1 - 3 * s else BG
                row += bytes((c[2], c[1], c[0], 0xFF))
        rows.append(bytes(row))
    return b"".join(rows)


def ico(sizes=SIZES) -> bytes:
    images = []
    for n in sizes:
        pixels = render(n)
        mask_row = ((n + 31) // 32) * 4          # 1bpp, выравнивание по 4 байта
        header = struct.pack("<IiiHHIIiiII", 40, n, n * 2, 1, 32, 0,
                             len(pixels) + mask_row * n, 0, 0, 0, 0)
        images.append((n, header + pixels + b"\x00" * (mask_row * n)))

    out = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    for n, blob in images:
        out += struct.pack("<BBBBHHII", n if n < 256 else 0, n if n < 256 else 0,
                           0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    return out + b"".join(blob for _n, blob in images)


if __name__ == "__main__":
    path = Path(__file__).with_name("icon.ico")
    path.write_bytes(ico())
    print(f"{path} — {path.stat().st_size} байт, размеры: {SIZES}")
