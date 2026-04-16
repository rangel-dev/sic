# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Entry point is the root main.py
entry_point = 'main.py'

# Assets to include
# In onefile mode, these will be extracted to sys._MEIPASS
added_files = [
    ('assets', 'assets'),
    ('README.md', '.'),
]

# Coleta TODOS os submódulos do nosso pacote `src` recursivamente.
# Isso é a única forma 100% confiável de garantir que cada arquivo .py
# em src/ vai parar dentro do .exe — independente de imports lazy,
# namespace packages, ou caprichos do analisador estático do PyInstaller.
# A causa raiz dos ModuleNotFoundError em runtime era o PyInstaller
# silenciosamente pulando módulos como src.core.update_service.
src_submodules = (
    collect_submodules('src')
    + collect_submodules('src.core')
    + collect_submodules('src.workers')
    + collect_submodules('src.ui')
    + collect_submodules('src.ui.pages')
    + collect_submodules('src.ui.components')
    + collect_submodules('src.ui.styles')
)

a = Analysis(
    [entry_point],
    # pathex precisa apontar para a raiz do projeto para que os imports
    # absolutos como `from src.core.X import Y` resolvam durante a análise.
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'pandas', 'openpyxl', 'lxml',
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    ] + src_submodules,
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

splash = Splash(
    'assets/splash_bg.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
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
    icon='assets/icons/app.ico'
)

coll = COLLECT(
    exe,
    splash.binaries,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SIC',
)

# For Mac, we still want the .app bundle wrapper
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='SIC.app',
        icon='assets/icons/app.icns',
        bundle_id='com.rangeldev.sic',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        },
    )
