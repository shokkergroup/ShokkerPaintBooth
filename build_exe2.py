"""Build EXE with PyInstaller and deploy to electron-app/server"""
import subprocess, shutil, os, time

WORK = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"
PYTHON = r"C:\Users\Ricky's PC\AppData\Local\Programs\Python\Python311\python.exe"
LOG = os.path.join(WORK, "build_log2.txt")

os.chdir(WORK)
log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

# Check PyInstaller
try:
    r = subprocess.run([PYTHON, "-m", "PyInstaller", "--version"], capture_output=True, text=True, timeout=30)
    log(f"PyInstaller version: {r.stdout.strip()} (rc={r.returncode})")
    if r.stderr.strip():
        log(f"  stderr: {r.stderr.strip()[:200]}")
except Exception as e:
    log(f"ERROR: PyInstaller not available: {e}")
    with open(LOG, "w") as f:
        f.write("\n".join(log_lines))
    raise SystemExit(1)

# Delete old dist to force full rebuild
dist_exe = os.path.join(WORK, "dist", "shokker-server.exe")
if os.path.exists(dist_exe):
    os.remove(dist_exe)
    log("Deleted old dist/shokker-server.exe")

# Build
log("Starting PyInstaller build...")
t0 = time.time()
r = subprocess.run(
    [PYTHON, "-m", "PyInstaller", "--clean", "--noconfirm", "shokker-server.spec"],
    capture_output=True, text=True, timeout=600
)
elapsed = time.time() - t0
log(f"Build completed in {elapsed:.1f}s (rc={r.returncode})")
if r.stdout.strip():
    # Just last 10 lines
    lines = r.stdout.strip().split("\n")
    for line in lines[-10:]:
        log(f"  stdout: {line}")
if r.stderr.strip():
    lines = r.stderr.strip().split("\n")
    for line in lines[-10:]:
        log(f"  stderr: {line}")

# Verify
if os.path.exists(dist_exe):
    size = os.path.getsize(dist_exe)
    log(f"EXE built: {size:,} bytes ({size/1024/1024:.1f} MB)")
    
    # Deploy
    deploy_dir = os.path.join(WORK, "electron-app", "server")
    shutil.copy2(dist_exe, os.path.join(deploy_dir, "shokker-server.exe"))
    log(f"Deployed EXE to {deploy_dir}")
    
    html_src = os.path.join(WORK, "paint-booth-v2.html")
    shutil.copy2(html_src, os.path.join(deploy_dir, "paint-booth-v2.html"))
    log(f"Deployed HTML to {deploy_dir}")
    
    # Verify deploy
    d_exe = os.path.join(deploy_dir, "shokker-server.exe")
    d_html = os.path.join(deploy_dir, "paint-booth-v2.html")
    log(f"Deploy verify: EXE={os.path.getsize(d_exe):,} HTML={os.path.getsize(d_html):,}")
    log("=== BUILD + DEPLOY SUCCESS ===")
else:
    log("=== ERROR: EXE not found after build ===")

with open(LOG, "w") as f:
    f.write("\n".join(log_lines))
