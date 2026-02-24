import subprocess, os, shutil

NODE = r"C:\Program Files\nodejs\node.exe"
NPM_CLI = r"C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"
APP_DIR = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app"
LOG = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_step4b_log.txt"

env = os.environ.copy()
env["PATH"] = r"C:\Program Files\nodejs;" + r"C:\Windows\system32;" + env.get("PATH", "")

results = []

# Clean slate
nm = os.path.join(APP_DIR, "node_modules")
lock = os.path.join(APP_DIR, "package-lock.json")
if os.path.isdir(nm):
    shutil.rmtree(nm, ignore_errors=True)
    results.append("Deleted node_modules")
if os.path.exists(lock):
    os.remove(lock)
    results.append("Deleted package-lock.json")

results.append(f"node_modules exists after delete: {os.path.isdir(nm)}")

# npm install with --include=dev
results.append("Running: npm install --include=dev --loglevel=verbose")
r = subprocess.run(
    [NODE, NPM_CLI, "install", "--include=dev", "--loglevel=verbose"],
    capture_output=True, text=True, timeout=600,
    cwd=APP_DIR, env=env
)
results.append(f"Exit: {r.returncode}")
results.append(f"STDOUT (last 5000):\n{r.stdout[-5000:]}")
results.append(f"STDERR (last 5000):\n{r.stderr[-5000:]}")

# Check files
for p in [
    "node_modules/electron/cli.js",
    "node_modules/electron/dist/electron.exe",
    "node_modules/electron-builder/out/cli/cli.js",
]:
    fp = os.path.join(APP_DIR, p)
    results.append(f"  {p}: {'EXISTS' if os.path.exists(fp) else 'MISSING'}")

with open(LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
