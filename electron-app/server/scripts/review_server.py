"""SPB review server — replaces audit_server.py with a multi-page version.

Run once:  python scripts/review_server.py
Then open: http://localhost:7777/SPB_AUDIT.html              (existing audit)
           http://localhost:7777/SPB_RATE_10.html            (spec-pattern rater)
           http://localhost:7777/SPB_RATE_CANDY_PEARL.html  (Candy & Pearl base rater)
           http://localhost:7777/SPB_RATE_EXOTIC_METAL.html (Exotic Metal base rater)
           http://localhost:7777/SPEC_OVERLAY_PURGE.html     (spec-overlay purge)
           http://localhost:7777/SPB_SPEC_PATTERNS_ATLAS.html
           ...any other HTML or asset in project root

Endpoints:
  GET  /<anything>      -> serves file from project root (HTML, PNG, JSON, …)
  GET  /save            -> legacy alias: serves current SPB_AUDIT.json
  GET  /state           -> alias for /save (SPB_AUDIT.json read)
  POST /save            -> writes posted JSON body to SPB_AUDIT.json (atomic)
  GET  /rate10_state    -> returns current SPB_RATE_10.json (or {})
  POST /save_rate10     -> writes posted JSON body to SPB_RATE_10.json (atomic)
  GET  /rate_candy_pearl_state -> returns SPB_RATE_CANDY_PEARL.json (or {})
  POST /save_rate_candy_pearl  -> writes SPB_RATE_CANDY_PEARL.json (atomic)
  GET  /rate_exotic_metal_state -> returns SPB_RATE_EXOTIC_METAL.json (or {})
  POST /save_rate_exotic_metal  -> writes SPB_RATE_EXOTIC_METAL.json (atomic)
  GET  /spec_overlay_purge_state -> returns SPB_SPEC_OVERLAY_PURGE.json (or {})
  POST /save_spec_overlay_purge  -> writes SPB_SPEC_OVERLAY_PURGE.json (atomic)
  GET  /spec_overlay_definitive_audit_state -> returns SPB_SPEC_OVERLAY_DEFINITIVE_AUDIT.json (or {})
  POST /save_spec_overlay_definitive_audit  -> writes SPB_SPEC_OVERLAY_DEFINITIVE_AUDIT.json (atomic)
"""
from __future__ import annotations

import json
import mimetypes
import os
import socketserver
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    from scripts.rate_portals_config import PORTALS
except ImportError:
    PORTALS = {}

AUDIT_HTML = ROOT / "SPB_AUDIT.html"
AUDIT_JSON = ROOT / "SPB_AUDIT.json"
RATE10_JSON = ROOT / "SPB_RATE_10.json"
SPEC_OVERLAY_PURGE_JSON = ROOT / "SPB_SPEC_OVERLAY_PURGE.json"
SPEC_OVERLAY_DEFINITIVE_AUDIT_JSON = ROOT / "SPB_SPEC_OVERLAY_DEFINITIVE_AUDIT.json"
RATE_CANDY_PEARL_JSON = ROOT / "SPB_RATE_CANDY_PEARL.json"
RATE_EXOTIC_METAL_JSON = ROOT / "SPB_RATE_EXOTIC_METAL.json"
QUEUE_JSON = ROOT / "_rate10_thumbs" / "audit_queue.json"
CANDY_PEARL_QUEUE_JSON = ROOT / "_candy_pearl_thumbs" / "audit_queue.json"
EXOTIC_METAL_QUEUE_JSON = ROOT / "_exotic_metal_thumbs" / "audit_queue.json"
QUEUE_SCRIPT = ROOT / "scripts" / "generate_audit_queue.py"
CANDY_PEARL_QUEUE_SCRIPT = ROOT / "scripts" / "generate_candy_pearl_audit_queue.py"
EXOTIC_METAL_QUEUE_SCRIPT = ROOT / "scripts" / "generate_exotic_metal_audit_queue.py"
PORTAL_RATE_JSON = {slug: ROOT / cfg["rate_json"] for slug, cfg in PORTALS.items()}
PORTAL_QUEUE_SCRIPT = ROOT / "scripts" / "generate_rate_portal_queue.py"
PORT = 7777


def regenerate_queue() -> None:
    """Run the queue generator as a subprocess so its stdout/stderr remapping
    doesn't poison this server's streams. Cheap (<1s)."""
    import subprocess
    try:
        subprocess.run(
            [sys.executable, str(QUEUE_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            timeout=15,
            check=False,
        )
    except Exception as e:
        print(f"[queue] regenerate failed: {e!r}")


def regenerate_candy_pearl_queue() -> None:
    import subprocess
    try:
        subprocess.run(
            [sys.executable, str(CANDY_PEARL_QUEUE_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            timeout=15,
            check=False,
        )
    except Exception as e:
        print(f"[candy-pearl queue] regenerate failed: {e!r}")


def regenerate_exotic_metal_queue() -> None:
    import subprocess
    try:
        subprocess.run(
            [sys.executable, str(EXOTIC_METAL_QUEUE_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            timeout=15,
            check=False,
        )
    except Exception as e:
        print(f"[exotic-metal queue] regenerate failed: {e!r}")


def regenerate_portal_queue(slug: str) -> None:
    import subprocess
    try:
        subprocess.run(
            [sys.executable, str(PORTAL_QUEUE_SCRIPT), slug],
            cwd=str(ROOT),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception as e:
        print(f"[portal {slug} queue] regenerate failed: {e!r}")

mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/html; charset=utf-8", ".html")


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _safe_resolve(rel: str) -> Path | None:
    """Resolve a request path under ROOT, refusing path traversal.

    Strips any query string / fragment before file lookup so cache-buster URLs
    like /foo.png?v=12345 resolve to foo.png on disk.
    """
    # Drop query string and fragment
    rel = rel.split("?", 1)[0].split("#", 1)[0]
    rel = urllib.parse.unquote(rel.lstrip("/"))
    if not rel:
        rel = "index.html"
    target = (ROOT / rel).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return target


class ReviewHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        msg = fmt % args
        if any(k in msg for k in ("POST /save", "GET /state", "/save_rate10", "/rate10_state", "/spec_overlay_purge", "/spec_overlay_definitive")):
            print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    # ---------- GET ----------
    def do_GET(self):
        # State endpoints (read-only JSON)
        if self.path in ("/state", "/save"):
            self._serve_bytes(
                AUDIT_JSON.read_bytes() if AUDIT_JSON.exists() else b"{}",
                "application/json",
            )
            return
        if self.path == "/rate10_state":
            self._serve_bytes(
                RATE10_JSON.read_bytes() if RATE10_JSON.exists() else b"{}",
                "application/json",
            )
            return
        if self.path == "/spec_overlay_purge_state":
            self._serve_bytes(
                SPEC_OVERLAY_PURGE_JSON.read_bytes() if SPEC_OVERLAY_PURGE_JSON.exists() else b"{}",
                "application/json",
            )
            return
        if self.path == "/spec_overlay_definitive_audit_state":
            self._serve_bytes(
                SPEC_OVERLAY_DEFINITIVE_AUDIT_JSON.read_bytes() if SPEC_OVERLAY_DEFINITIVE_AUDIT_JSON.exists() else b"{}",
                "application/json",
            )
            return
        if self.path == "/rate_candy_pearl_state":
            self._serve_bytes(
                RATE_CANDY_PEARL_JSON.read_bytes() if RATE_CANDY_PEARL_JSON.exists() else b"{}",
                "application/json",
            )
            return
        if self.path == "/rate_exotic_metal_state":
            self._serve_bytes(
                RATE_EXOTIC_METAL_JSON.read_bytes() if RATE_EXOTIC_METAL_JSON.exists() else b"{}",
                "application/json",
            )
            return
        for slug, rate_path in PORTAL_RATE_JSON.items():
            if self.path == f"/rate_{slug}_state":
                self._serve_bytes(
                    rate_path.read_bytes() if rate_path.exists() else b"{}",
                    "application/json",
                )
                return
        for slug, cfg in PORTALS.items():
            qpath = f"/{cfg['thumb_dir']}/audit_queue.json"
            if self.path.startswith(qpath):
                if not cfg.get("bakeoff_mode"):
                    regenerate_portal_queue(slug)
                out = ROOT / cfg["thumb_dir"] / "audit_queue.json"
                self._serve_bytes(
                    out.read_bytes() if out.exists() else b'{"bases":[]}',
                    "application/json",
                )
                return
        # Live queue: regenerate from rating + loop state before serving.
        if self.path.startswith("/_rate10_thumbs/audit_queue.json"):
            regenerate_queue()
            self._serve_bytes(
                QUEUE_JSON.read_bytes() if QUEUE_JSON.exists() else b'{"patterns":[]}',
                "application/json",
            )
            return
        if self.path.startswith("/_candy_pearl_thumbs/audit_queue.json"):
            regenerate_candy_pearl_queue()
            self._serve_bytes(
                CANDY_PEARL_QUEUE_JSON.read_bytes() if CANDY_PEARL_QUEUE_JSON.exists() else b'{"bases":[]}',
                "application/json",
            )
            return
        if self.path.startswith("/_exotic_metal_thumbs/audit_queue.json"):
            regenerate_exotic_metal_queue()
            self._serve_bytes(
                EXOTIC_METAL_QUEUE_JSON.read_bytes() if EXOTIC_METAL_QUEUE_JSON.exists() else b'{"bases":[]}',
                "application/json",
            )
            return
        if self.path == "/":
            # Tiny landing page
            html = (
                "<html><body style='font-family:sans-serif;background:#111;color:#eee;padding:30px'>"
                "<h2>SPB Review Server</h2>"
                "<ul>"
                "<li><a href='/SPEC_OVERLAY_DEFINITIVE_AUDIT.html'>SPEC_OVERLAY_DEFINITIVE_AUDIT.html</a> &mdash; 50 definitive replacement spec overlays</li>"
                "<li><a href='/SPEC_OVERLAY_PURGE.html'>SPEC_OVERLAY_PURGE.html</a> &mdash; full spec-overlay purge</li>"
                "<li><a href='/SPB_RATE_10.html'>SPB_RATE_10.html</a> &mdash; spec-pattern living queue</li>"
                "<li><a href='/SPB_RATE_CANDY_PEARL.html'>SPB_RATE_CANDY_PEARL.html</a> &mdash; Candy &amp; Pearl bases</li>"
                "<li><a href='/SPB_RATE_EXOTIC_METAL.html'>SPB_RATE_EXOTIC_METAL.html</a> &mdash; Exotic Metal bases</li>"
                "<li><a href='/SPB_RATE_PORTALS_INDEX.html'>SPB_RATE_PORTALS_INDEX.html</a> &mdash; Overnight portals index</li>"
                "<li><a href='/SPB_AUDIT.html'>SPB_AUDIT.html</a> &mdash; pattern audit (existing)</li>"
                "<li><a href='/SPB_SPEC_PATTERNS_ATLAS.html'>SPB_SPEC_PATTERNS_ATLAS.html</a></li>"
                "<li><a href='/paint-booth-v2.html'>paint-booth-v2.html</a></li>"
                "</ul></body></html>"
            ).encode()
            self._serve_bytes(html, "text/html; charset=utf-8")
            return

        # Static file under project root
        target = _safe_resolve(self.path)
        if target is None or not target.exists() or not target.is_file():
            self.send_error(404, f"not found: {self.path}")
            return
        ctype, _ = mimetypes.guess_type(str(target))
        ctype = ctype or "application/octet-stream"
        data = target.read_bytes()
        self._serve_bytes(data, ctype)

    def _serve_bytes(self, data: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---------- POST ----------
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            data = json.loads(raw or b"{}")
        except Exception as e:
            self.send_error(400, f"bad json: {e}")
            return

        if self.path == "/save":
            payload = json.dumps(data, indent=2).encode("utf-8")
            _atomic_write(AUDIT_JSON, payload)
            n_entries = len((data or {}).get("entries", {}))
            body = f"saved {n_entries} entries -> SPB_AUDIT.json".encode()
            self._serve_bytes(body, "text/plain")
            return

        if self.path == "/save_rate10":
            payload = json.dumps(data, indent=2).encode("utf-8")
            _atomic_write(RATE10_JSON, payload)
            n_entries = len((data or {}).get("ratings", {}))
            body = f"saved {n_entries} ratings -> SPB_RATE_10.json".encode()
            self._serve_bytes(body, "text/plain")
            return

        if self.path == "/save_spec_overlay_purge":
            payload = json.dumps(data, indent=2).encode("utf-8")
            _atomic_write(SPEC_OVERLAY_PURGE_JSON, payload)
            n_entries = len((data or {}).get("decisions", {}))
            body = f"saved {n_entries} purge decisions -> SPB_SPEC_OVERLAY_PURGE.json".encode()
            self._serve_bytes(body, "text/plain")
            return

        if self.path == "/save_spec_overlay_definitive_audit":
            payload = json.dumps(data, indent=2).encode("utf-8")
            _atomic_write(SPEC_OVERLAY_DEFINITIVE_AUDIT_JSON, payload)
            n_entries = len((data or {}).get("decisions", {}))
            body = f"saved {n_entries} definitive decisions -> SPB_SPEC_OVERLAY_DEFINITIVE_AUDIT.json".encode()
            self._serve_bytes(body, "text/plain")
            return

        if self.path == "/save_rate_candy_pearl":
            payload = json.dumps(data, indent=2).encode("utf-8")
            _atomic_write(RATE_CANDY_PEARL_JSON, payload)
            n_entries = len((data or {}).get("ratings", {}))
            body = f"saved {n_entries} ratings -> SPB_RATE_CANDY_PEARL.json".encode()
            self._serve_bytes(body, "text/plain")
            return

        if self.path == "/save_rate_exotic_metal":
            payload = json.dumps(data, indent=2).encode("utf-8")
            _atomic_write(RATE_EXOTIC_METAL_JSON, payload)
            n_entries = len((data or {}).get("ratings", {}))
            body = f"saved {n_entries} ratings -> SPB_RATE_EXOTIC_METAL.json".encode()
            self._serve_bytes(body, "text/plain")
            return

        for slug, rate_path in PORTAL_RATE_JSON.items():
            if self.path == f"/save_rate_{slug}":
                payload = json.dumps(data, indent=2).encode("utf-8")
                _atomic_write(rate_path, payload)
                n_entries = len((data or {}).get("ratings", {}))
                body = f"saved {n_entries} ratings -> {rate_path.name}".encode()
                self._serve_bytes(body, "text/plain")
                return

        self.send_error(404, f"unknown POST endpoint: {self.path}")


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    print(f"SPB review server on http://localhost:{PORT}/")
    print(f"  project root: {ROOT}")
    print(f"  Ctrl+C to stop.")
    print()
    with ReusableTCPServer(("127.0.0.1", PORT), ReviewHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nshutting down.")


if __name__ == "__main__":
    sys.exit(main() or 0)
