# -*- mode: python ; coding: utf-8 -*-
"""Dong goi "Ghep anh thong minh" (Datpro09) thanh 2 file .exe doc lap:

    dist\\GhepAnh.exe  - giao dien do hoa (nhay dup de chay)
    dist\\ghep.exe     - dong lenh: ghep anh / show

Cach build:  nhay dup build_exe.bat (tu ky so sau khi build)
      hoac:  python -m PyInstaller GhepAnh.spec --noconfirm --clean
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Toan bo module cua du an + file template .pptx mac dinh cua python-pptx
hidden = collect_submodules("smart_collage")
datas = collect_data_files("pptx")

COMMON = dict(
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# ---------------------------------------------------- GhepAnh.exe (giao dien)
a_gui = Analysis(["packaging/run_gui.py"], **COMMON)
pyz_gui = PYZ(a_gui.pure)
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    a_gui.binaries,
    a_gui.datas,
    [],
    name="GhepAnh",
    version="packaging/version_gui.txt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # khong hien cua so den khi chay giao dien
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ------------------------------------------------------- ghep.exe (dong lenh)
a_cli = Analysis(["packaging/run_cli.py"], **COMMON)
pyz_cli = PYZ(a_cli.pure)
exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    a_cli.binaries,
    a_cli.datas,
    [],
    name="ghep",
    version="packaging/version_cli.txt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # can console de in tien do / tham so dong lenh
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
