"""Build 12: Fix server.py rotation passthrough for monolithic finishes"""
import subprocess, sys, os, shutil

PYTHON = r'C:\Python313\python.exe'
SERVER_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine'
ELECTRON_DIR = os.path.join(SERVER_DIR, 'electron-app')
NODE = r'C:\Program Files\nodejs\node.exe'
EB_JS = os.path.join(ELECTRON_DIR, 'node_modules', 'electron-builder', 'out', 'cli', 'cli.js')
LOG = os.path.join(SERVER_DIR, '_build12_log.txt')

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

def save_log():
    with open(LOG, 'w') as f:
        f.write('\n'.join(log_lines))

log("*** BUILD 12: server.py rotation fix for monolithic finishes ***")

# Step 1: PyInstaller
log("=== Step 1: PyInstaller ===")
r = subprocess.run([
    PYTHON, '-m', 'PyInstaller',
    '--onefile', '--name', 'shokker-server',
    '--distpath', os.path.join(ELECTRON_DIR, 'server'),
    '--workpath', os.path.join(SERVER_DIR, '_pybuild_work'),
    '--specpath', os.path.join(SERVER_DIR, '_pybuild_work'),
    '--add-data', os.path.join(SERVER_DIR, 'shokker_engine_v2.py') + ';.',
    '--hidden-import', 'flask', '--hidden-import', 'flask_cors',
    '--hidden-import', 'numpy', '--hidden-import', 'PIL',
    '--hidden-import', 'PIL.Image', '--hidden-import', 'PIL.ImageFilter',
    '--clean', '--noconfirm', 'server.py'
], capture_output=True, text=True, timeout=300, cwd=SERVER_DIR)
log(f"PyInstaller exit: {r.returncode}")
if r.stderr: log(f"STDERR: {r.stderr[-1500:]}")
if r.returncode != 0:
    log("*** PYINSTALLER FAILED ***")
    save_log()
    sys.exit(1)

# Step 2: Copy HTML
log("=== Step 2: Copy HTML ===")
shutil.copy2(os.path.join(SERVER_DIR, 'paint-booth-v2.html'),
             os.path.join(ELECTRON_DIR, 'server', 'paint-booth-v2.html'))
log("HTML copied")

# Step 3: Electron build
log("=== Step 3: Electron build ===")
env = os.environ.copy()
env['PATH'] = r'C:\Program Files\nodejs' + ';' + env.get('PATH', '')
r2 = subprocess.run([NODE, EB_JS, '--win', '--x64'],
    capture_output=True, text=True, timeout=600, cwd=ELECTRON_DIR, env=env)
log(f"Electron exit: {r2.returncode}")
if r2.stdout: log(f"STDOUT: {r2.stdout[-2000:]}")
if r2.stderr: log(f"STDERR: {r2.stderr[-1000:]}")
if r2.returncode == 0:
    setup = os.path.join(ELECTRON_DIR, 'dist', 'ShokkerPaintBooth-0.1.0-alpha-Setup.exe')
    if os.path.exists(setup):
        size_mb = os.path.getsize(setup) / (1024*1024)
        log(f"\n*** BUILD 12 COMPLETE: {setup} ({size_mb:.1f} MB) ***")
    else:
        log("WARNING: installer not found")
else:
    log("*** ELECTRON BUILD FAILED ***")

save_log()
