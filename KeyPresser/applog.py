"""文件日志：把运行过程写进磁盘，方便事后排查问题。

日志位置：%APPDATA%\\KeyPresser\\logs\\keypresser.log
单个文件上限 1 MB，保留 5 份轮转，UTF-8 编码（中文不乱码）。

除了正常记录，还会接管两处异常出口，保证"崩了但什么都没留下"不会发生：
  * sys.excepthook          —— 主线程未捕获异常
  * Tk.report_callback_exception —— tkinter 事件回调里的异常
    （这类异常默认只打印到 stderr，GUI 程序没有控制台，等于被吞掉）
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "KeyPresser" / "logs"
LOG_FILE = LOG_DIR / "keypresser.log"
LOGGER_NAME = "keypresser"

MAX_BYTES = 1_000_000
BACKUPS = 5

_configured = False


def setup(level: int = logging.DEBUG) -> Path:
    """初始化日志。可重复调用，只有第一次真正生效。返回日志文件路径。"""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return LOG_FILE

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8")
    except Exception:
        # 磁盘不可写时退化成"什么都不写"，绝不能让日志把程序拖垮
        logger.addHandler(logging.NullHandler())
        _configured = True
        return LOG_FILE

    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)-5s] %(name)-12s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"))
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    _configured = True

    _install_exception_hooks(logger)
    return LOG_FILE


def get(name: str) -> logging.Logger:
    """取一个子 logger，name 会显示在日志里用于区分模块。

    顺带保证日志已初始化，这样任何模块都能安全地用：
    即使调用方忘了先 setup()，也不会出现"日志什么都没写"的情况。
    """
    setup()
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def _install_exception_hooks(logger: logging.Logger) -> None:
    def excepthook(exc_type, exc_value, exc_tb):
        logger.critical("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = excepthook

    # tkinter 延迟导入：在没有 tkinter 的解释器上（例如托管 Python 3.13），
    # 模块级 import 会让 applog 本身都导不进来，恰恰在"最需要日志"时没有日志。
    try:
        import tkinter
    except ImportError as exc:
        logger.warning("未找到 tkinter，跳过 Tk 回调异常接管（不影响主线程异常记录）: %s",
                       exc)
        return

    def tk_callback_exception(self, exc, val, tb):      # noqa: N802 (Tk 命名)
        logger.critical("Tk 回调异常", exc_info=(exc, val, tb))

    tkinter.Tk.report_callback_exception = tk_callback_exception


def log_startup(logger: logging.Logger, mode: str, argv: list[str]) -> None:
    """把排查问题时最先要看的环境信息一次性写清楚。"""
    import platform

    try:
        import version
        ver = f"{version.VERSION} ({version.BUILT_AT})"
    except Exception:
        ver = "未知"

    logger.info("=" * 60)
    logger.info("启动 界面模式=%s  参数=%s", mode, argv)
    logger.info("程序版本=%s", ver)
    logger.info("Python=%s  架构=%s", sys.version.split()[0], platform.machine())
    logger.info("系统=%s", platform.platform())
    logger.info("工作目录=%s", os.getcwd())
    logger.info("日志文件=%s", LOG_FILE)


def open_log_folder(logger: logging.Logger | None = None) -> str:
    """在资源管理器里打开日志目录。返回目录路径（失败时也返回，供提示用）。"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        if logger:
            logger.warning("创建日志目录失败: %s", exc)
        return str(LOG_DIR)
    try:
        os.startfile(str(LOG_DIR))          # noqa: S606 (Windows 专用)
    except Exception as exc:
        if logger:
            logger.warning("打开日志目录失败: %s", exc)
    return str(LOG_DIR)
