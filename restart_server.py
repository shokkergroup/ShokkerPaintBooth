import subprocess, os, time, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
p = subprocess.Popen(
    [sys.executable, 'start_server.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
time.sleep(4)
print(f"Server started, PID: {p.pid}")
