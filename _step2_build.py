import subprocess, sys, os

PYTHON = sys.executable
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(SERVER_DIR, '_step2_log.txt')

# Create output dirs
electron_server = os.path.join(SERVER_DIR, 'electron-app', 'server')
pybuild_work = os.path.join(SERVER_DIR, '_pybuild_work')
os.makedirs(electron_server, exist_ok=True)
os.makedirs(pybuild_work, exist_ok=True)

with open(log_path, 'w') as log:
    log.write("Starting PyInstaller build...\n")
    log.flush()
    
    r = subprocess.run([
        PYTHON, '-m', 'PyInstaller',
        '--onefile',
        '--name', 'shokker-server',
        '--distpath', electron_server,
        '--workpath', pybuild_work,
        '--specpath', pybuild_work,
        '--add-data', os.path.join(SERVER_DIR, 'shokker_engine_v2.py') + os.pathsep + '.',
        '--hidden-import', 'flask',
        '--hidden-import', 'flask_cors',
        '--hidden-import', 'numpy',
        '--hidden-import', 'PIL',
        '--hidden-import', 'PIL.Image',
        '--hidden-import', 'PIL.ImageFilter',
        '--clean',
        '--noconfirm',
        'server.py'
    ], capture_output=True, text=True, timeout=600, cwd=SERVER_DIR)
    
    log.write(f"STDOUT (last 3000 chars):\n{r.stdout[-3000:]}\n\n")
    log.write(f"STDERR (last 3000 chars):\n{r.stderr[-3000:]}\n\n")
    log.write(f"Exit code: {r.returncode}\n")
    
    exe_path = os.path.join(electron_server, 'shokker-server.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024*1024)
        log.write(f"\nSUCCESS: {exe_path} ({size_mb:.1f} MB)\n")
    else:
        log.write(f"\nFAILED: exe not found at {exe_path}\n")
