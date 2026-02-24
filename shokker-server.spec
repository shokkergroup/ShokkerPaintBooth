# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('E:\\Claude Code Assistant\\12-iRacing Misc\\Shokker iRacing\\ShokkerEngine\\shokker_engine_v2.py', '.'),
        ('E:\\Claude Code Assistant\\12-iRacing Misc\\Shokker iRacing\\ShokkerEngine\\shokker_24k_expansion.py', '.'),
        ('E:\\Claude Code Assistant\\12-iRacing Misc\\Shokker iRacing\\ShokkerEngine\\shokker_paradigm_expansion.py', '.'),
    ],
    hiddenimports=['flask', 'flask_cors', 'jinja2', 'markupsafe', 'werkzeug', 'click', 'blinker', 'itsdangerous', 'PIL', 'numpy', 'shokker_24k_expansion', 'shokker_paradigm_expansion', 'scipy', 'scipy.spatial', 'scipy.ndimage'],
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
    name='shokker-server',
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
