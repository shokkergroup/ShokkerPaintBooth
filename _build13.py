"""Build 13: Debug logging for rotation pipeline"""
import subprocess, sys, os, shutil

PYTHON = r'C:\Python313\python.exe'
SERVER_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine'
ELECTRON_DIR = os.path.join(SERVER_DIR, 'electron-app')
NODE = r'C:\Program Files\nodejs\node.exe'
EB_JS = os.path.join(ELECTRON_DIR, 'node_modules', 'electron-builder', 'out', 'cli', 'cli.js')

print("*** BUILD 13: Debug rotation logging ***")

# Step 1: PyInstaller
print("=== Step 1: PyInstaller ===")
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
print(f"PyInstaller exit: {r.returncode}")
if r.returncode != 0:
    print(f"STDERR: {r.stderr[-2000:]}")
    sys.exit(1)

# Step 2: Copy HTML
print("=== Step 2: Copy HTML ===")
shutil.copy2(os.path.join(SERVER_DIR, 'paint-booth-v2.html'),
             os.path.join(ELECTRON_DIR, 'server', 'paint-booth-v2.html'))
print("HTML copied")

# Step 3: Electron
print("=== Step 3: Electron build ===")
env = os.environ.copy()
env['PATH'] = r'C:\Program Files\nodejs' + ';' + env.get('PATH', '')
r2 = subprocess.run([NODE, EB_JS, '--win', '--x64'],
    capture_output=True, text=True, timeout=600, cwd=ELECTRON_DIR, env=env)
print(f"Electron exit: {r2.returncode}")
if r2.returncode == 0:
    setup = os.path.join(ELECTRON_DIR, 'dist', 'ShokkerPaintBooth-0.1.0-alpha-Setup.exe')
    if os.path.exists(setup):
        size_mb = os.path.getsize(setup) / (1024*1024)
        print(f"\n*** BUILD 13 COMPLETE: {size_mb:.1f} MB ***")
    else:
        print("WARNING: installer not found")
else:
    print(f"ELECTRON FAILED: {r2.stderr[-1000:]}")
