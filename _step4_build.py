import subprocess, os, sys

NODE = r"C:\Program Files\nodejs\node.exe"
NPM_CLI = r"C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"
APP_DIR = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app"
LOG = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_step4_log.txt"

env = os.environ.copy()
env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")

results = []

# 1) Check electron version
try:
    r = subprocess.run(
        [NODE, os.path.join(APP_DIR, "node_modules", "electron", "cli.js"), "--version"],
        capture_output=True, text=True, timeout=30, cwd=APP_DIR, env=env
    )
    results.append(f"Electron version: stdout={r.stdout.strip()} stderr={r.stderr.strip()} rc={r.returncode}")
except Exception as e:
    results.append(f"Electron version check failed: {e}")

# 2) Check if electron binary is downloaded
electron_path = os.path.join(APP_DIR, "node_modules", "electron", "dist", "electron.exe")
results.append(f"Electron binary exists: {os.path.exists(electron_path)}")
if not os.path.exists(electron_path):
    # Try running the install script
    results.append("Running electron install script...")
    try:
        r = subprocess.run(
            [NODE, os.path.join(APP_DIR, "node_modules", "electron", "install.js")],
            capture_output=True, text=True, timeout=120, cwd=APP_DIR, env=env
        )
        results.append(f"Install: stdout={r.stdout.strip()[:500]} stderr={r.stderr.strip()[:500]} rc={r.returncode}")
        results.append(f"Electron binary exists after install: {os.path.exists(electron_path)}")
    except Exception as e:
        results.append(f"Install failed: {e}")

# 3) Run electron-builder
results.append("\n--- Starting electron-builder ---")
try:
    r = subprocess.run(
        [NODE, os.path.join(APP_DIR, "node_modules", "electron-builder", "out", "cli", "cli.js"),
         "--win", "--x64"],
        capture_output=True, text=True, timeout=300, cwd=APP_DIR, env=env
    )
    results.append(f"Builder stdout:\n{r.stdout[-3000:]}")
    results.append(f"Builder stderr:\n{r.stderr[-3000:]}")
    results.append(f"Builder exit code: {r.returncode}")
except Exception as e:
    results.append(f"Builder failed: {e}")

# 4) Check output
dist_dir = os.path.join(APP_DIR, "dist")
if os.path.isdir(dist_dir):
    for root, dirs, files in os.walk(dist_dir):
        for f in files:
            fp = os.path.join(root, f)
            sz = os.path.getsize(fp)
            results.append(f"  {fp} ({sz:,} bytes)")
else:
    results.append("dist/ directory not found")

with open(LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("Done. See _step4_log.txt")
