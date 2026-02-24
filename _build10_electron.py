"""Build 10 Step 2: Electron packaging"""
import subprocess, sys, os

ELECTRON_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app'
LOG = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_build10_electron_log.txt'
NODE = r'C:\Program Files\nodejs\node.exe'
EB_JS = os.path.join(ELECTRON_DIR, 'node_modules', 'electron-builder', 'out', 'cli', 'cli.js')

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

log("=== Electron Build 10 ===")
log(f"CWD: {ELECTRON_DIR}")
log(f"NODE: {NODE}")
log(f"EB_JS: {EB_JS}")
log(f"EB_JS exists: {os.path.exists(EB_JS)}")

# Use node directly to run electron-builder
env = os.environ.copy()
env['PATH'] = r'C:\Program Files\nodejs' + ';' + env.get('PATH', '')

try:
    r = subprocess.run(
        [NODE, EB_JS, '--win', '--x64'],
        capture_output=True, text=True, timeout=600,
        cwd=ELECTRON_DIR, env=env
    )
    if r.stdout:
        log(f"STDOUT:\n{r.stdout[-4000:]}")
    if r.stderr:
        log(f"STDERR:\n{r.stderr[-4000:]}")
    log(f"EXIT: {r.returncode}")
    if r.returncode == 0:
        log("\n*** BUILD 10 COMPLETE ***")
        setup = os.path.join(ELECTRON_DIR, 'dist', 'ShokkerPaintBooth-0.1.0-alpha-Setup.exe')
        if os.path.exists(setup):
            size_mb = os.path.getsize(setup) / (1024*1024)
            log(f"Installer: {setup} ({size_mb:.1f} MB)")
        else:
            log(f"WARNING: installer not at {setup}")
    else:
        log("\n*** ELECTRON BUILD FAILED ***")
except Exception as e:
    log(f"ERROR: {e}")

with open(LOG, 'w') as f:
    f.write('\n'.join(log_lines))
