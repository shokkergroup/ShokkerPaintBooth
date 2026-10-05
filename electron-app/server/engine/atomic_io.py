# -*- coding: utf-8 -*-
"""engine/atomic_io.py -- crash-safe JSON persistence for user state (2026-09-05).

Codebase-health finding S3: shokker_config.json, shokker_license.json, every June-audit and
Spec-Sculpt verdict file, the user-import manifest and the thumbnail manifest were written with
a plain ``open(path, 'w')`` and read with a loader that silently returned ``{}``/defaults on a
parse error -- so an app closed mid-save (or two saves in flight) truncated the file, and the
NEXT save "healed" it by overwriting the wreck with only the newest entries. Owner verdicts and
car paths could vanish with no trace.

Three primitives, all Windows-safe:

* :func:`atomic_write_json` / :func:`atomic_write_text` -- write to a temp file in the same
  directory, fsync, then ``os.replace`` (retried on the transient ``PermissionError`` Windows
  raises while an AV scanner or watcher holds the target).
* :func:`load_json_guarded` -- returns the default when the file is missing; when the file is
  present but unparseable it is RENAMED to ``<name>.corrupt-<timestamp>`` (never overwritten),
  a WARNING is logged, and the default is returned. The wreck stays recoverable by hand.
* :func:`file_lock` -- one process-wide ``RLock`` per path, so a load -> mutate -> save sequence
  can be made exclusive (``config.THREADED`` is True: concurrent POSTs are real).

Behaviour is otherwise identical to the old writers: same paths, same JSON layout.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

_LOG = logging.getLogger("spb.atomic_io")
_LOCKS: dict = {}
_LOCKS_GUARD = threading.Lock()


def _norm(path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


@contextmanager
def file_lock(path) -> Iterator[None]:
    """Process-wide re-entrant lock keyed by normalised path."""
    key = _norm(path)
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = _LOCKS[key] = threading.RLock()
    with lock:
        yield


def _replace_with_retries(tmp: str, dst: str, attempts: int = 8, delay: float = 0.15) -> None:
    last: Optional[BaseException] = None
    for i in range(attempts):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError as ex:  # Windows: transient share violation (AV, fs.watch, Explorer)
            last = ex
            time.sleep(delay * (i + 1))
    raise last if last else OSError("os.replace failed")


def atomic_write_bytes(path, data: bytes) -> int:
    path = str(path)
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix="." + os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        _replace_with_retries(tmp, path)
        return len(data)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def atomic_write_text(path, text: str, encoding: str = "utf-8") -> int:
    return atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(path, obj: Any, indent: Optional[int] = 2, ensure_ascii: bool = False,
                      sort_keys: bool = False, separators=None) -> int:
    text = json.dumps(obj, indent=indent, ensure_ascii=ensure_ascii, sort_keys=sort_keys, separators=separators)
    return atomic_write_text(path, text)


def quarantine_corrupt(path, logger: Optional[logging.Logger] = None, what: str = "") -> Optional[str]:
    """Rename an unparseable file aside as <path>.corrupt-<ts>. Returns the new name or None."""
    path = str(path)
    log = logger or _LOG
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = f"{path}.corrupt-{stamp}"
    try:
        os.replace(path, dst)
        log.warning("[atomic_io] %s is not valid JSON -- moved aside to %s (nothing overwritten)", what or path, dst)
        return dst
    except OSError as ex:
        log.warning("[atomic_io] %s is not valid JSON and could not be moved aside (%s)", what or path, ex)
        return None


def load_json_guarded(path, default: Callable[[], Any] | Any = dict, logger: Optional[logging.Logger] = None,
                      what: str = "", encoding: str = "utf-8") -> Any:
    """Load JSON; missing file -> default; corrupt file -> quarantined + default (never silently healed)."""
    path = str(path)
    make = default if callable(default) else (lambda: default)
    if not os.path.exists(path):
        return make()
    try:
        with open(path, "r", encoding=encoding) as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        quarantine_corrupt(path, logger, what)
        return make()
    except OSError as ex:
        (logger or _LOG).warning("[atomic_io] could not read %s (%s); using default", what or path, ex)
        return make()
