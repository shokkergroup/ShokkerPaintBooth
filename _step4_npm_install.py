import subprocess, os

NODE = r"C:\Program Files\nodejs\node.exe"
NPM_CLI = r"C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"
APP_DIR = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app"
LOG = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_step4_npm_log.txt"

env = os.environ.copy()
env["PATH"] = r"C:\Program Files\nodejs;" + r"C:\Windows\system32;" + env.get("PATH", "")

results = []

# First nuke node_modules to start clean
import shutil
nm = os.path.join(APP_DIR, "node_modules")
if os.path.isdir(nm):
    results.append("Removing old node_modules...")
    shutil.rmtree(nm, ignore_errors=True)
    results.append("Removed.")

# Run npm install
results.append("Running npm install...")
try:
    r = subprocess.run(
        [NODE, NPM_CLI, "install"],
        capture_output=True, text=True, timeout=600,
        cwd=APP_DIR, env=env
    )
    results.append(f"STDOUT:\n{r.stdout[-4000:]}")
    results.append(f"STDERR:\n{r.stderr[-4000:]}")
    results.append(f"Exit code: {r.returncode}")
except Exception as e:
    results.append(f"npm install failed: {e}")

# Verify key files exist
for check in [
    "node_modules/electron/cli.js",
    "node_modules/electron/dist/electron.exe",
    "node_modules/electron/install.js",
    "node_modules/electron-builder/out/cli/cli.js",
]:
    fp = os.path.join(APP_DIR, check)
    exists = os.path.exists(fp)
    results.append(f"  {check}: {'EXISTS' if exists else 'MISSING'}")

with open(LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print("Done. Check _step4_npm_log.txt")
