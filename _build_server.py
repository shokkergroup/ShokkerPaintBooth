"""
Step 1: Check/install dependencies
Step 2: Run PyInstaller to compile server.py into a standalone exe
"""
import subprocess, sys, os

PYTHON = r'C:\Python313\python.exe'
SERVER_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine'
RESULTS = os.path.join(SERVER_DIR, '_build_log.txt')

log = []

def run(cmd, desc):
    log.append(f"\n=== {desc} ===")
    log.append(f"CMD: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=SERVER_DIR)
        log.append(f"STDOUT: {r.stdout[-2000:] if r.stdout else '(none)'}")
        log.append(f"STDERR: {r.stderr[-2000:] if r.stderr else '(none)'}")
        log.append(f"EXIT: {r.returncode}")
        return r.returncode == 0
    except Exception as e:
        log.append(f"ERROR: {e}")
        return False

# Step 1: Install dependencies
log.append("=== DEPENDENCY CHECK ===")
run([PYTHON, '-m', 'pip', 'install', '--upgrade', 'pip'], 'Upgrade pip')
run([PYTHON, '-m', 'pip', 'install', 'pyinstaller', 'flask', 'flask-cors', 'numpy', 'Pillow'], 'Install packages')

# Step 2: Verify pyinstaller is available
run([PYTHON, '-m', 'PyInstaller', '--version'], 'Check PyInstaller version')

# Step 3: Build server.exe with PyInstaller
# --onefile = single exe
# --add-data = bundle shokker_engine_v2.py alongside
# --hidden-import = ensure flask/cors get bundled
ok = run([
    PYTHON, '-m', 'PyInstaller',
    '--onefile',
    '--name', 'shokker-server',
    '--distpath', os.path.join(SERVER_DIR, 'electron-app', 'server'),
    '--workpath', os.path.join(SERVER_DIR, '_pybuild_work'),
    '--specpath', os.path.join(SERVER_DIR, '_pybuild_work'),
    '--add-data', f'shokker_engine_v2.py;.',
    '--hidden-import', 'flask',
    '--hidden-import', 'flask_cors',
    '--hidden-import', 'numpy',
    '--hidden-import', 'PIL',
    '--hidden-import', 'PIL.Image',
    '--hidden-import', 'PIL.ImageFilter',
    '--clean',
    '--noconfirm',
    'server.py'
], 'PyInstaller build')

if ok:
    log.append("\n*** BUILD SUCCESS ***")
    exe_path = os.path.join(SERVER_DIR, 'electron-app', 'server', 'shokker-server.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024*1024)
        log.append(f"Output: {exe_path} ({size_mb:.1f} MB)")
    else:
        log.append(f"WARNING: exe not found at {exe_path}")
else:
    log.append("\n*** BUILD FAILED ***")

with open(RESULTS, 'w') as f:
    f.write('\n'.join(log))
