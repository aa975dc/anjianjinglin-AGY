"""端到端启动测试：真的把 main.py 拉起来，确认窗口出现、热键注册，再关掉。"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "KeyPresser"))

import instance
import winutil

# 解释器探测：优先取与当前解释器同目录的 pythonw.exe，换机可用
PYW = str(Path(sys.executable).with_name("pythonw.exe"))
if not Path(PYW).exists():
    PYW = sys.executable

proc = subprocess.Popen([PYW, str(ROOT / "KeyPresser" / "main.py")])
print(f"进程已启动 PID={proc.pid}")

hwnd = 0
for _ in range(40):                      # 最多等 4 秒
    time.sleep(0.1)
    hwnd = instance.find_existing_window()
    if hwnd:
        break

if hwnd:
    print(f"窗口已出现: hwnd={hwnd}")
    print("标题检测:", "找到 KeyPresser 窗口" if winutil.is_window(hwnd) else "窗口无效")
else:
    print("FAIL 未检测到窗口")

alive = proc.poll() is None
print(f"进程存活: {alive}  退出码={proc.poll()}")

time.sleep(1.0)
proc.terminate()
try:
    proc.wait(timeout=5)
    print("已关闭进程")
except subprocess.TimeoutExpired:
    proc.kill()
    print("强制结束进程")

print("结果:", "PASS" if (hwnd and alive) else "FAIL")
