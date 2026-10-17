"""Big picker hover previews, fetched once instead of shipped.

[11.0.2 slim download 2026-10-16, Claude] Owner: "Keep everything offline
except the big hover previews, about 7 GB." The 1024x512 faithful masters
(3.36 GB, used only by the enlarged hover preview) no longer ship in the
installer. The grid cards (<key>_256/_128/_48.png) still ship, so browsing is
fully offline. A master is fetched from the public R2 bucket the first time
that finish is hovered and kept in the user's profile, so app updates never
wipe it. Offline, the hover shows the grid card enlarged instead.
"""
import os
import re
import threading
import time
import urllib.error
import urllib.request

_DEFAULT_BASE = 'https://pub-9969ab01838a4d69bb55822f42553904.r2.dev/picker-previews/faithful_split_v1/'
_NAME = re.compile(r'[0-9a-f]{64}\.png')
_MAX_BYTES = 8 * 1024 * 1024
_TIMEOUT_S = 6
_COOLDOWN_S = 60
_state = {'offline_until': 0.0}
_state_lock = threading.Lock()


def base_url():
    return os.environ.get('SPB_PREVIEW_CDN') or _DEFAULT_BASE


def download_dir():
    return os.environ.get('SPB_PREVIEW_CACHE_DIR') or os.path.join(
        os.environ.get('APPDATA', os.path.expanduser('~')), 'ShokkerPaintBooth', 'picker_previews')


def fetch_master(name):
    """Return the master PNG bytes for <key>.png, or None (offline, missing, switched off)."""
    if os.environ.get('SPB_PREVIEW_CDN_OFF') == '1' or not _NAME.fullmatch(name or ''):
        return None
    with _state_lock:
        if time.monotonic() < _state['offline_until']:
            return None   # one failed connection: do not make every hover wait for a timeout
    request = urllib.request.Request(base_url() + name, headers={'User-Agent': 'ShokkerPaintBooth'})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
            data = response.read(_MAX_BYTES + 1)
        return data if 0 < len(data) <= _MAX_BYTES else None
    except urllib.error.HTTPError:
        return None       # the bucket answered: no cool-down for one missing object
    except Exception:
        with _state_lock:
            _state['offline_until'] = time.monotonic() + _COOLDOWN_S
        return None
