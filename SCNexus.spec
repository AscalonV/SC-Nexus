# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SC Nexus
# Build: pyinstaller SCNexus.spec

from pathlib import Path

ROOT = Path(SPEC).parent  # e.g. E:\Documents\Star Conflict\Programs\SC Nexus

block_cipher = None

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Ship the entire src package so all sub-modules are importable
        (str(ROOT / 'src'), 'src'),
        # Persist user data directory (defaults only; runtime writes go here)
        (str(ROOT / 'user_data'), 'user_data'),
        # Combat-assistant sounds
        (str(ROOT / 'src' / 'modules' / 'combat_assistant' / 'sounds'), 'src/modules/combat_assistant/sounds'),
        # Combat-assistant bitmap assets (bomb icons, etc.)
        (str(ROOT / 'src' / 'modules' / 'combat_assistant' / 'assets'), 'src/modules/combat_assistant/assets'),
        # Combat-assistant overlay config templates (QSS, presets …)
        (str(ROOT / 'src' / 'modules' / 'combat_assistant' / 'config'), 'src/modules/combat_assistant/config'),
    ],
    hiddenimports=[
        # PySide6 modules that are imported at runtime
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtMultimedia',
        # pydantic
        'pydantic',
        'pydantic.v1',
        # image processing
        'cv2',
        'mss',
        'PIL',
        'PIL.Image',
        'numpy',
        # audio
        'winsound',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SCNexus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon — place SCNexus.ico in the project root and uncomment:
    # icon=str(ROOT / 'SCNexus.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SCNexus',
)
