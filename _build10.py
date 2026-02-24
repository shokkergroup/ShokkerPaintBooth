"""Build 10: Scale + Rotation fixes"""
import subprocess, sys, os

PYTHON = r'C:\Python313\python.exe'
SERVER_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine'
ELECTRON_DIR = os.path.join(SERVER_DIR, 'electron-app')
LOG = os.path.join(SERVER_DIR, '_build10_log.txt')

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

def run(cmd, desc, cwd=None, timeout=300):
    log(f"\n=== {desc} ===")
    log(f"CMD: {' '.join(cmd)}")
    log(f"CWD: {cwd or '(default)'}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        if r.stdout:
            log(f"STDOUT (last 3000): {r.stdout[-3000:]}")
        if r.stderr:
            log(f"STDERR (last 2000): {r.stderr[-2000:]}")
        log(f"EXIT: {r.returncode}")
        return r.returncode == 0
    except Exception as e:
        log(f"ERROR: {e}")
        return False

# Step 1: PyInstaller build
log("*** BUILD 10: Scale + Rotation Fixes ***")

ok = run([
    PYTHON, '-m', 'PyInstaller',
    '--onefile',
    '--name', 'shokker-server',
    '--distpath', os.path.join(ELECTRON_DIR, 'server'),
    '--workpath', os.path.join(SERVER_DIR, '_pybuild_work'),
    '--specpath', os.path.join(SERVER_DIR, '_pybuild_work'),
    '--add-data', os.path.join(SERVER_DIR, 'shokker_engine_v2.py') + ';.',
    '--hidden-import', 'flask',
    '--hidden-import', 'flask_cors',
    '--hidden-import', 'numpy',
    '--hidden-import', 'PIL',
    '--hidden-import', 'PIL.Image',
    '--hidden-import', 'PIL.ImageFilter',
    '--clean',
    '--noconfirm',
    'server.py'
], 'PyInstaller build', cwd=SERVER_DIR)

if not ok:
    log("\n*** PYINSTALLER FAILED ***")
    with open(LOG, 'w') as f:
        f.write('\n'.join(log_lines))
    sys.exit(1)

# Step 2: Copy updated HTML to electron-app/server/
import shutil
html_src = os.path.join(SERVER_DIR, 'paint-booth-v2.html')
html_dst = os.path.join(ELECTRON_DIR, 'server', 'paint-booth-v2.html')
log(f"\n=== Copy HTML ===")
try:
    shutil.copy2(html_src, html_dst)
    log(f"Copied {html_src} -> {html_dst}")
except Exception as e:
    log(f"ERROR copying HTML: {e}")

# Step 3: Build Electron installer
ok2 = run([
    'npx', 'electron-builder', '--win', '--x64'
], 'Electron build', cwd=ELECTRON_DIR, timeout=600)

if ok2:
    log("\n*** BUILD 10 COMPLETE ***")
    setup = os.path.join(ELECTRON_DIR, 'dist', 'ShokkerPaintBooth-0.1.0-alpha-Setup.exe')
    if os.path.exists(setup):
        size_mb = os.path.getsize(setup) / (1024*1024)
        log(f"Installer: {setup} ({size_mb:.1f} MB)")
    else:
        log(f"WARNING: installer not found at {setup}")
else:
    log("\n*** ELECTRON BUILD FAILED ***")

with open(LOG, 'w') as f:
    f.write('\n'.join(log_lines))
