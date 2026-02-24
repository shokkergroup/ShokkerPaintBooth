import subprocess, os

NODE_DIR = r'C:\Program Files\nodejs'
APP_DIR = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app'
log_path = os.path.join(APP_DIR, '..', '_step3b_log.txt')

env = os.environ.copy()
env['PATH'] = NODE_DIR + ';' + env.get('PATH', '')

with open(log_path, 'w') as log:
    # Run electron's post-install manually with correct PATH
    electron_dir = os.path.join(APP_DIR, 'node_modules', 'electron')
    r = subprocess.run(
        [os.path.join(NODE_DIR, 'node.exe'), 'install.js'],
        capture_output=True, text=True, timeout=60,
        cwd=electron_dir, env=env
    )
    log.write(f"=== Electron post-install ===\n{r.stdout}\n{r.stderr}\nExit: {r.returncode}\n\n")
    
    # Verify electron version
    electron_cmd = os.path.join(APP_DIR, 'node_modules', '.bin', 'electron.cmd')
    r2 = subprocess.run(
        [electron_cmd, '--version'],
        capture_output=True, text=True, timeout=15, env=env
    )
    log.write(f"=== Electron version ===\n{r2.stdout.strip()}\n{r2.stderr.strip()}\nExit: {r2.returncode}\n\n")
    
    # Verify electron-builder version
    builder_cmd = os.path.join(APP_DIR, 'node_modules', '.bin', 'electron-builder.cmd')
    r3 = subprocess.run(
        [builder_cmd, '--version'],
        capture_output=True, text=True, timeout=15, env=env
    )
    log.write(f"=== electron-builder version ===\n{r3.stdout.strip()}\n{r3.stderr.strip()}\nExit: {r3.returncode}\n")
