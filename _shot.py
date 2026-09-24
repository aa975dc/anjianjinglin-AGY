"""启动程序并把窗口抓成 BMP，用于人工核对界面。纯标准库 + Win32 GDI。"""
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "KeyPresser"))

import instance

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32.SetProcessDPIAware()

# 解释器探测：优先取与当前解释器同目录的 pythonw.exe，换机可用
PYW = str(Path(sys.executable).with_name("pythonw.exe"))
if not Path(PYW).exists():
    PYW = sys.executable
OUT = ROOT / "ui_shot.png"


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BMIH(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BMI(ctypes.Structure):
    _fields_ = [("bmiHeader", BMIH), ("bmiColors", wintypes.DWORD * 3)]


args = sys.argv[1:]
proc = subprocess.Popen([PYW, str(ROOT / "KeyPresser" / "main.py"), *args])
print(f"已启动 PID={proc.pid} args={args}")

hwnd = 0
for _ in range(60):
    time.sleep(0.15)
    hwnd = instance.find_existing_window()
    if hwnd:
        break
if not hwnd:
    proc.terminate()
    sys.exit("FAIL 未找到窗口")

user32.SetForegroundWindow(hwnd)
time.sleep(0.8)

rect = RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w, h = rect.right - rect.left, rect.bottom - rect.top
print(f"窗口 hwnd={hwnd} 位置=({rect.left},{rect.top}) 尺寸={w}x{h}")

hdc_screen = user32.GetDC(0)
memdc = gdi32.CreateCompatibleDC(hdc_screen)
hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
gdi32.SelectObject(memdc, hbmp)

PW_RENDERFULLCONTENT = 2
ok = user32.PrintWindow(hwnd, memdc, PW_RENDERFULLCONTENT)
print(f"PrintWindow -> {ok}")

bmi = BMI()
bmi.bmiHeader.biSize = ctypes.sizeof(BMIH)
bmi.bmiHeader.biWidth = w
bmi.bmiHeader.biHeight = -h
bmi.bmiHeader.biPlanes = 1
bmi.bmiHeader.biBitCount = 32
bmi.bmiHeader.biCompression = 0

buf = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(memdc, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
raw_bgra = buf.raw

gdi32.DeleteObject(hbmp)
gdi32.DeleteDC(memdc)
user32.ReleaseDC(0, hdc_screen)


def write_png(path: Path, width: int, height: int, bgra: bytes) -> None:
    """纯标准库写 PNG（BGRA -> RGB，无滤波）。"""
    import struct
    import zlib

    stride = width * 4
    raw = bytearray()
    for y in range(height):
        line = bgra[y * stride:(y + 1) * stride]
        raw.append(0)                       # filter: none
        rgb = bytearray(width * 3)
        rgb[0::3] = line[2::4]              # R
        rgb[1::3] = line[1::4]              # G
        rgb[2::3] = line[0::4]              # B
        raw += rgb

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


write_png(OUT, w, h, raw_bgra)
print(f"已保存 {OUT} ({OUT.stat().st_size} 字节)")

time.sleep(0.3)
proc.terminate()
try:
    proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    proc.kill()
print("已关闭程序")
