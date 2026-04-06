# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


project_root = Path.cwd()

hiddenimports = []
hiddenimports += collect_submodules("pyttsx3.drivers")
hiddenimports += collect_submodules("comtypes")

datas = []
datas += collect_data_files("imageio_ffmpeg")
datas += collect_data_files("whisper")

env_file = project_root / ".env"
if env_file.exists():
    datas.append((str(env_file), "."))

binaries = []
binaries += collect_dynamic_libs("torch")


a = Analysis(
    ["run.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lili",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Lili",
)
