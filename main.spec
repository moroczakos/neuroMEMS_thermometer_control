# main.spec
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import sys

block_cipher = None

# Automatically collect all submodules from your packages
hidden_imports = []
for pkg in ['apps', 'controllers', 'instruments', 'models', 'views', 'utils', 'base_classes']:
    hidden_imports += collect_submodules(pkg)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('icon.png', '.'), ('input_files', 'input_files')],
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='main'
)
