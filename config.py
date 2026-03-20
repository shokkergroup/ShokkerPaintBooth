"""
config.py - Single Source of Truth for V5 Configuration
=========================================================
ONE place to change ports, paths, debug mode, build settings.

Never hardcode ports or paths in server_v5.py, server.py, or bat files.
Everything reads from here.

HOW TO USE:
  from config import CFG
  port = CFG.PORT
  debug = CFG.DEBUG

ENVIRONMENT OVERRIDES (highest priority):
  SHOKKER_PORT=59876    → override port (e.g. for primary/secondary)
  SHOKKER_DEV=1         → enable debug mode + hot reload
  SHOKKER_LOG=DEBUG     → verbose logging
  SHOKKER_NO_CLEAN=1    → skip clean boot (do not kill port / other server); use for second instance
"""

import os
import json


class _Config:
    """V5 runtime configuration. Read-only after init."""

    # ─── SERVER ────────────────────────────────────────────────
    PORT: int = 59876          # Default: primary port (use SHOKKER_PORT=59877 for secondary/dev)
    PRIMARY_PORT: int = 59876  # Primary port (same as PORT)
    HOST: str = "0.0.0.0"

    # ─── DEBUG / DEV ───────────────────────────────────────────
    DEBUG: bool = False        # Set SHOKKER_DEV=1 to enable auto-reload
    THREADED: bool = True      # Always use threaded Flask
    VERBOSE: bool = False      # Extra log output

    # ─── PATHS ─────────────────────────────────────────────────
    ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR: str = os.path.join(ROOT_DIR, "output")
    # Pre-rendered thumbnails (from rebuild_thumbnails.py); /api/swatch serves these when present
    THUMBNAIL_DIR: str = os.path.join(ROOT_DIR, "thumbnails")
    CONFIG_FILE: str = os.path.join(ROOT_DIR, "shokker_config.json")
    LICENSE_FILE: str = os.path.join(ROOT_DIR, "shokker_license.json")
    HTML_FILE: str = os.path.join(ROOT_DIR, "paint-booth-v2.html")

    # ─── SHOKK FILE SYSTEM ────────────────────────────────────────────
    SHOKK_LIBRARY_DIR: str = os.path.join(
        os.path.expanduser("~"), "Documents", "Shokker Paint Booth", "SHOKK Library"
    )
    SHOKK_FACTORY_DIR: str = os.path.join(ROOT_DIR, "shokk_factory")

    # ─── PATTERNS FOR REVIEW ───────────────────────────────────────────
    # Candidate pattern images go here; app lists them and shows engine-rendered swatches
    # so you can approve/tweak before adding to PATTERNS and registry.
    PATTERN_FOR_REVIEW_DIR: str = os.path.join(ROOT_DIR, "assets", "patterns", "for_review")

    # ─── FEATURE FLAGS (rollback: set False to restore previous behavior) ───
    ENABLE_THIRD_BASE_OVERLAY: bool = True   # 3rd Base Overlay layer + per-layer pattern
    # ─── BUILD ─────────────────────────────────────────────────
    VERSION: str = "5.0.0"
    BUILD_TAG: str = "V5-1"
    APP_NAME: str = "Shokker Paint Booth V5"

    def __init__(self):
        self._apply_env_overrides()
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.SHOKK_LIBRARY_DIR, exist_ok=True)
        os.makedirs(self.SHOKK_FACTORY_DIR, exist_ok=True)
        os.makedirs(self.PATTERN_FOR_REVIEW_DIR, exist_ok=True)

    def _apply_env_overrides(self):
        """Environment variables override defaults - use for deployment."""
        if "SHOKKER_PORT" in os.environ:
            self.PORT = int(os.environ["SHOKKER_PORT"])
        if os.environ.get("SHOKKER_DEV", "0") == "1":
            self.DEBUG = True
            self.VERBOSE = True
            print("[Config] DEV MODE - hot reload enabled")
        if os.environ.get("SHOKKER_LOG") == "DEBUG":
            self.VERBOSE = True

    def as_dict(self) -> dict:
        return {
            "version": self.VERSION,
            "build": self.BUILD_TAG,
            "port": self.PORT,
            "debug": self.DEBUG,
            "root": self.ROOT_DIR,
        }

    def __repr__(self):
        return f"<ShokkerConfig V{self.VERSION} port={self.PORT} debug={self.DEBUG}>"


# Module-level singleton - import this everywhere
CFG = _Config()
