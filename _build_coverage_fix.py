"""Build: Coverage fix deployment — self-logging"""
import subprocess, sys, os, shutil

LOG = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_build_coverage_fix_log.txt'
PYTHON = r'C:\Python313\python.exe'
SERVER_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine'
ELECTRON_SERVER = os.path.join(SERVER_DIR, 'electron-app', 'server')
DIST_RESOURCES = os.path.join(SERVER_DIR, 'dist', 'ShokkerPaintBooth-win32-x64', 'resources')

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')

# Clear log
with open(LOG, 'w', encoding='utf-8') as f:
    f.write('')

log("*** BUILD: Coverage Fix Deployment ***")
log(f"Working dir: {SERVER_DIR}")
log(f"Python: {PYTHON}")

# Step 1: PyInstaller
log("\n=== Step 1: PyInstaller ===")
try:
    r = subprocess.run([
        PYTHON, '-m', 'PyInstaller',
        '--onefile', '--name', 'shokker-server',
        '--distpath', ELECTRON_SERVER,
        '--workpath', os.path.join(SERVER_DIR, '_pybuild_work'),        '--specpath', os.path.join(SERVER_DIR, '_pybuild_work'),
        '--add-data', os.path.join(SERVER_DIR, 'shokker_engine_v2.py') + ';.',
        '--add-data', os.path.join(SERVER_DIR, 'shokker_24k_expansion.py') + ';.',
        '--add-data', os.path.join(SERVER_DIR, 'shokker_paradigm_expansion.py') + ';.',
        '--hidden-import', 'flask', '--hidden-import', 'flask_cors',
        '--hidden-import', 'numpy', '--hidden-import', 'PIL',
        '--hidden-import', 'PIL.Image', '--hidden-import', 'PIL.ImageFilter',
        '--hidden-import', 'shokker_24k_expansion',
        '--hidden-import', 'shokker_paradigm_expansion',
        '--hidden-import', 'scipy', '--hidden-import', 'scipy.spatial',
        '--hidden-import', 'scipy.ndimage',
        '--hidden-import', 'jinja2', '--hidden-import', 'markupsafe',
        '--hidden-import', 'werkzeug', '--hidden-import', 'click',
        '--hidden-import', 'blinker', '--hidden-import', 'itsdangerous',
        '--clean', '--noconfirm', 'server.py'
    ], capture_output=True, text=True, timeout=300, cwd=SERVER_DIR)
    log(f"PyInstaller exit code: {r.returncode}")
    if r.stdout:
        log(f"STDOUT (last 1500):\n{r.stdout[-1500:]}")
    if r.stderr:
        log(f"STDERR (last 1500):\n{r.stderr[-1500:]}")
    if r.returncode != 0:
        log("BUILD FAILED at PyInstaller step")
        sys.exit(1)
except Exception as e:
    log(f"EXCEPTION: {e}")
    sys.exit(1)
# Verify exe was created
exe_path = os.path.join(ELECTRON_SERVER, 'shokker-server.exe')
if os.path.exists(exe_path):
    size_mb = os.path.getsize(exe_path) / (1024*1024)
    log(f"EXE built: {exe_path} ({size_mb:.1f} MB)")
else:
    log("ERROR: shokker-server.exe was NOT created!")
    sys.exit(1)

# Step 2: Copy to dist
log("\n=== Step 2: Deploy to dist ===")
dest = os.path.join(DIST_RESOURCES, 'shokker-server.exe')
shutil.copy2(exe_path, dest)
dest_size = os.path.getsize(dest) / (1024*1024)
log(f"Copied to: {dest} ({dest_size:.1f} MB)")

log("\n*** BUILD COMPLETE ***")