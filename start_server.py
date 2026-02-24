"""Start the Shokker server with stdout/stderr redirected to a log file."""
import sys, os, socket

# Use script's own directory (portable — works on ANY machine)
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SERVER_DIR)

# Redirect stdout/stderr to a log file so print() calls don't crash
log_path = os.path.join(SERVER_DIR, 'server_log.txt')
log_file = open(log_path, 'w', buffering=1)  # line-buffered
sys.stdout = log_file
sys.stderr = log_file


def find_free_port(start=5000, end=5010):
    """Find first available port in range."""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start  # Fallback to default, let Flask report the error


port = find_free_port()

# Write chosen port to a file so the BAT/UI can discover it
port_file = os.path.join(SERVER_DIR, '.server_port')
with open(port_file, 'w') as f:
    f.write(str(port))

from server import app
app.run(debug=False, port=port, threaded=True)
