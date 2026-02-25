# -*- mode: python ; coding: utf-8 -*-
# Shokker Paint Booth AG — Build 30 spec file
# Uses local paths (no E:\ references)

import os
SRC = os.path.abspath('.')

a = Analysis(
    ['server.py'],
    pathex=[SRC],
    binaries=[],
    datas=[
        (os.path.join(SRC, 'shokker_engine_v2.py'), '.'),
        (os.path.join(SRC, 'shokker_24k_expansion.py'), '.'),
        (os.path.join(SRC, 'shokker_paradigm_expansion.py'), '.'),
        (os.path.join(SRC, 'shokker_color_monolithics.py'), '.'),
        (os.path.join(SRC, 'paint-booth-v2.html'), '.'),
    ],
    hiddenimports=[
        'flask', 'flask_cors', 'jinja2', 'markupsafe', 'werkzeug',
        'click', 'blinker', 'itsdangerous',
        'PIL', 'PIL.Image', 'PIL.ImageFilter',
        'numpy',
        'scipy', 'scipy.spatial', 'scipy.ndimage',
        'shokker_24k_expansion', 'shokker_paradigm_expansion', 'shokker_color_monolithics',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='shokker-paint-booth-ag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
