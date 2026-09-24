"""Генератор версии формата yyMMddHHmm (момент сборки).

Пишет два файла:
  version.py       -- то, что читает приложение;
  version_info.txt -- ресурс версии для exe (PyInstaller --version-file).

Запуск: python make_version.py   (build.bat делает это автоматически)
"""

from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent

VERSION_PY = '''"""Версия сборки. Файл генерируется make_version.py -- руками не править."""

VERSION = "{version}"
VERSION_TUPLE = {tuple}
BUILT_AT = "{built_at}"
'''

VERSION_INFO = '''# Ресурс версии для PyInstaller. Генерируется make_version.py.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple},
    prodvers={tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('FileDescription', 'KeyPresser - key sequence sender for games'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', 'KeyPresser'),
        StringStruct('LegalCopyright', 'MIT License'),
        StringStruct('OriginalFilename', 'KeyPresser.exe'),
        StringStruct('ProductName', 'KeyPresser'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x409, 1200])])
  ]
)
'''


def make(now: datetime | None = None) -> str:
    now = now or datetime.now()
    version = now.strftime("%y%m%d%H%M")
    # в ресурс exe версия должна лечь четырьмя числами <= 65535
    parts = (int(now.strftime("%y")), now.month, now.day,
             int(now.strftime("%H%M")))
    (HERE / "version.py").write_text(
        VERSION_PY.format(version=version, tuple=parts,
                          built_at=now.strftime("%Y-%m-%d %H:%M")),
        encoding="utf-8")
    (HERE / "version_info.txt").write_text(
        VERSION_INFO.format(version=version, tuple=parts), encoding="utf-8")
    return version


if __name__ == "__main__":
    print(make())
