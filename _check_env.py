import subprocess, sys, os

results = []
results.append(f"Python: {sys.version}")
results.append(f"Python path: {sys.executable}")

try:
    r = subprocess.run(['C:/Program Files/nodejs/node.exe', '-v'], capture_output=True, text=True, timeout=10)
    results.append(f"Node: {r.stdout.strip() or r.stderr.strip() or 'no output'}")
except Exception as e:
    results.append(f"Node error: {e}")

try:
    r = subprocess.run(['C:/Program Files/nodejs/npm.cmd', '--version'], capture_output=True, text=True, timeout=10)
    results.append(f"npm: {r.stdout.strip() or r.stderr.strip() or 'no output'}")
except Exception as e:
    results.append(f"npm error: {e}")

try:
    r = subprocess.run(['C:/Program Files/nodejs/npx.cmd', '--version'], capture_output=True, text=True, timeout=10)
    results.append(f"npx: {r.stdout.strip() or r.stderr.strip() or 'no output'}")
except Exception as e:
    results.append(f"npx error: {e}")

out_path = r'E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\_env_results.txt'
with open(out_path, 'w') as f:
    f.write('\n'.join(results))
