# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Entry point is the root main.py
entry_point = 'main.py'

# Assets to include (Styles, etc are already inside src relative imports, 
# but we might have external assets in assets/ folder)
added_files = [
    ('assets', 'assets'),
    ('README.md', '.'),
]

# Collecting requirements automatically isn't clean with PyInstaller, 
# better to let hidden imports handle it if needed.
hidden_imports = [
    'src',
    'src.core',
    'src.ui',
    'src.ui.pages',
    'src.ui.components',
    'src.ui.styles',
    'src.workers',
    'src.main_app',
    'pandas',
    'openpyxl',
    'lxml',
    'requests'
]

a = Analysis(
    [entry_point],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
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
    [],
    exclude_binaries=True,
    name='SIC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Set to True for debugging if needed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app.ico' if os.path.exists('assets/icons/app.ico') else None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SIC'
)

# Mac App Bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='SIC.app',
        icon='assets/icons/app.icns' if os.path.exists('assets/icons/app.icns') else None,
        bundle_id='com.rangeldev.sic',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False'
        }
    )
