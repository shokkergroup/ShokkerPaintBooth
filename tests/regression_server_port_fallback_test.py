from pathlib import Path


def test_server_v5_keeps_launcher_pinned_origin_stable():
    src = Path("server_v5.py").read_text(encoding="utf-8", errors="ignore")

    assert "def _spb_pick_runtime_port" in src
    assert "def _spb_can_bind_port" in src
    assert "60876" in src
    assert ".server_port" in src
    assert "allow_fallback=not _env_pinned_port" in src
    assert "allow_fallback=(not _env_pinned_port) or _os_reserved" not in src


def test_electron_pins_stable_origin_while_file_mode_can_still_discover_server():
    main_src = Path("electron-app/main.js").read_text(encoding="utf-8", errors="ignore")
    api_src = Path("paint-booth-5-api-render.js").read_text(encoding="utf-8", errors="ignore")

    assert "const STABLE_SERVER_PORT = 59876" in main_src
    assert "ensureStableServerPortAvailable" in main_src
    assert "tryOrder" not in main_src
    assert "60876" not in main_src
    assert "60876" in api_src
    assert "fallbackPorts" in api_src
