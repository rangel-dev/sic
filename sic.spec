# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Entry point is the root main.py
entry_point = 'main.py'

# Assets to include
# In onefile mode, these will be extracted to sys._MEIPASS
added_files = [
    ('assets', 'assets'),
    ('README.md', '.'),
]

a = Analysis(
    [entry_point],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['pandas', 'openpyxl', 'lxml', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SIC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Set to False to hide the terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app.ico' if os.path.exists('assets/icons/app.ico') else None
)

# For Mac, we still want the .app bundle wrapper
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='SIC.app',
        icon='assets/icons/app.icns' if os.path.exists('assets/icons/app.icns') else None,
        bundle_id='com.rangeldev.sic',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        },
    )
