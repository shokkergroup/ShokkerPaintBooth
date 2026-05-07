from pathlib import Path


def test_server_v5_has_windows_reserved_port_fallback():
    src = Path("server_v5.py").read_text(encoding="utf-8", errors="ignore")

    assert "def _spb_pick_runtime_port" in src
    assert "def _spb_can_bind_port" in src
    assert "60876" in src
    assert ".server_port" in src
    assert "allow_fallback=not _env_pinned_port" in src


def test_electron_and_file_mode_scan_stable_spb_fallback_port():
    main_src = Path("electron-app/main.js").read_text(encoding="utf-8", errors="ignore")
    api_src = Path("paint-booth-5-api-render.js").read_text(encoding="utf-8", errors="ignore")

    assert "60876" in main_src
    assert "60876" in api_src
    assert "fallbackPorts" in api_src
