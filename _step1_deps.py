import subprocess, sys, os

PYTHON = sys.executable
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_step1_log.txt')

with open(log_path, 'w') as log:
    log.write(f"Python: {PYTHON}\n")
    log.write(f"Version: {sys.version}\n\n")
    
    # Install packages
    r = subprocess.run(
        [PYTHON, '-m', 'pip', 'install', 'pyinstaller', 'flask', 'flask-cors', 'numpy', 'Pillow'],
        capture_output=True, text=True, timeout=300
    )
    log.write(f"=== pip install ===\n{r.stdout}\n{r.stderr}\nExit: {r.returncode}\n")
    
    # Verify
    r2 = subprocess.run(
        [PYTHON, '-m', 'PyInstaller', '--version'],
        capture_output=True, text=True, timeout=30
    )
    log.write(f"\n=== PyInstaller version ===\n{r2.stdout}\n{r2.stderr}\nExit: {r2.returncode}\n")
