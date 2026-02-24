import subprocess, sys, os

NPM = r'C:\Program Files\nodejs\npm.cmd'
NODE_DIR = r'C:\Program Files\nodejs'
APP_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app'
log_path = os.path.join(APP_DIR, '..', '_step3_log.txt')

# Fix PATH so node is findable by child processes
env = os.environ.copy()
env['PATH'] = NODE_DIR + ';' + env.get('PATH', '')

with open(log_path, 'w') as log:
    log.write("=== npm install (with fixed PATH) ===\n")
    log.flush()
    
    r = subprocess.run(
        [NPM, 'install'],
        capture_output=True, text=True, timeout=600, cwd=APP_DIR, env=env
    )
    log.write(f"STDOUT:\n{r.stdout[-3000:]}\n\n")
    log.write(f"STDERR:\n{r.stderr[-3000:]}\n\n")
    log.write(f"Exit: {r.returncode}\n")
    
    electron_bin = os.path.join(APP_DIR, 'node_modules', '.bin', 'electron.cmd')
    builder_bin = os.path.join(APP_DIR, 'node_modules', '.bin', 'electron-builder.cmd')
    log.write(f"\nelectron bin exists: {os.path.exists(electron_bin)}\n")
    log.write(f"electron-builder bin exists: {os.path.exists(builder_bin)}\n")
