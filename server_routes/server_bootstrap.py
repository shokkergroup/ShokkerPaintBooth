"""Local server startup helpers for the SPB Flask app."""

import os
import socket
import socketserver
import traceback
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer


class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = False


def collect_missing_optional_dependencies(dependencies=None):
    missing = []
    deps = dependencies or (
        ("psd_tools", "PSD import will be disabled"),
        ("psutil", "memory stats fall back to gc"),
    )
    for dep, hint in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append((dep, hint))
    return missing


def write_port_file(server_dir, port):
    path = os.path.join(server_dir, ".server_port")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(str(port))
    return path


def _can_bind_port(host, port):
    """Return whether this process can bind host:port right now.

    Mirrors server_v5._spb_can_bind_port so the legacy bootstrap can pick a
    bindable port before committing it to .server_port.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(port)))
        return True
    except OSError:
        return False


def _pick_runtime_port(host, preferred, fallback):
    """Pick the first bindable port (preferred, then fallback).

    Returns the chosen port or None if neither is bindable (caller still tries
    to bind directly so a real OSError surfaces). The bind probe closes its
    socket immediately, so a small TOCTOU window remains; the actual bind in
    _bind_and_serve is the source of truth and the port file is only written
    after that bind succeeds.
    """
    for port in (preferred, fallback):
        if port is not None and _can_bind_port(host, port):
            return port
    return None


def print_startup_banner(
    *,
    spb_version,
    engine_version,
    build_id,
    gpu,
    bases,
    patterns,
    monos,
    config,
    port,
    missing_deps,
    printer=print,
):
    combos = bases * patterns
    has_expansion = bases > 60
    gpu_label = f"{gpu.get('icon', '?')} {gpu.get('name', 'CPU')}"
    if gpu.get("vram_mb"):
        gpu_label += f" ({gpu.get('vram_mb')} MB)"

    printer("=" * 60)
    printer(f"  SHOKKER PAINT BOOTH - {spb_version}")
    printer(f"  Engine: {engine_version}  |  Build: {build_id}")
    printer(f"  GPU: {gpu_label}  |  Accelerated: {gpu.get('accelerated', False)}")
    if has_expansion:
        printer(f"  24K Arsenal LOADED - {bases} bases / {patterns} patterns / {monos} monolithics")
    else:
        printer(f"  WARNING: 24K Arsenal NOT loaded - only {bases} bases / {patterns} patterns")
    printer(f"  {combos}+ finish combinations ready")
    printer(f"  iRacing ID: {config.get('iracing_id', 'not set')}")
    if config.get("live_link_enabled") and config.get("active_car"):
        car_path = config.get("car_paths", {}).get(config["active_car"], "???")
        printer(f"  Live Link: {config['active_car']} => {car_path}")
    else:
        printer("  Live Link: not configured")
    if missing_deps:
        printer("  Optional deps missing:")
        for dep, hint in missing_deps:
            printer(f"    - {dep}: {hint}")
    printer(f"  Listening on http://localhost:{port}")
    printer(f"  Open this URL in your browser:  http://localhost:{port}/")
    printer("=" * 60)


def make_quiet_handler(logger):
    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            logger.info(format % args)

    return QuietHandler


def _bind_and_serve(app, host, port, handler_class, server_factory, logger, *, server_dir=None):
    # Constructing the server binds the socket; if this raises OSError the port
    # file is NOT (re)written, so a launcher never sees a port we failed to bind.
    server = server_factory((host, port), handler_class)
    server.set_app(app)
    if server_dir is not None:
        try:
            write_port_file(server_dir, port)
            logger.info(f"Wrote .server_port = {port} after successful bind")
        except Exception as exc:
            logger.warning(f"Could not write .server_port after bind: {exc}")
    logger.info(f"Server bound to port {port} - serving")
    server.serve_forever()


def run_local_server(
    *,
    app,
    server_dir,
    load_config,
    engine,
    gpu_info,
    finish_catalog_cache,
    logger,
    auto_cleanup_old_jobs,
    output_folder,
    spb_version,
    engine_version,
    build_id,
    port=59876,
    fallback_port=59877,
    host="127.0.0.1",
    server_factory=ThreadedWSGIServer,
    printer=print,
):
    auto_cleanup_old_jobs(output_folder, max_age_hours=24, logger=logger)
    config = load_config()
    bases = len(engine.BASE_REGISTRY)
    patterns = len(engine.PATTERN_REGISTRY)
    monos = len(engine.MONOLITHIC_REGISTRY)

    # Pick a bindable port up front so the banner advertises the port we will
    # actually try first. The .server_port file is deliberately NOT written here
    # (a pre-bind write can point a launcher at a port we then fail to bind);
    # it is written inside _bind_and_serve only after the bind succeeds.
    bindable = _pick_runtime_port(host, port, fallback_port)
    banner_port = bindable if bindable is not None else port
    missing_deps = collect_missing_optional_dependencies()
    print_startup_banner(
        spb_version=spb_version,
        engine_version=engine_version,
        build_id=build_id,
        gpu=gpu_info(),
        bases=bases,
        patterns=patterns,
        monos=monos,
        config=config,
        port=banner_port,
        missing_deps=missing_deps,
        printer=printer,
    )

    try:
        finish_data_payload = finish_catalog_cache["prewarm"]()
        logger.info(f"Pre-warmed finish-data cache: {finish_data_payload['counts']['total']} entries")
    except Exception as exc:
        logger.warning(f"Pre-warm failed (non-fatal): {exc}")

    handler_class = make_quiet_handler(logger)
    # Order the bind attempts so the pre-checked bindable port goes first; the
    # port file is (re)written inside _bind_and_serve only after each bind
    # succeeds, so a fallback rewrites .server_port to the real, live port.
    attempt_ports = []
    if bindable is not None:
        attempt_ports.append(bindable)
    for candidate in (port, fallback_port):
        if candidate is not None and candidate not in attempt_ports:
            attempt_ports.append(candidate)

    last_exc = None
    for idx, attempt_port in enumerate(attempt_ports):
        try:
            _bind_and_serve(
                app, host, attempt_port, handler_class, server_factory, logger,
                server_dir=server_dir,
            )
            return
        except OSError as exc:
            last_exc = exc
            logger.error(f"Port {attempt_port} unavailable: {exc}")
            if idx + 1 < len(attempt_ports):
                logger.info(f"Trying fallback port {attempt_ports[idx + 1]}")
            continue
        except Exception as exc:
            logger.error(f"Server startup failed on port {attempt_port}: {exc}")
            logger.error(traceback.format_exc())
            return
    logger.error(f"All candidate ports failed ({attempt_ports}); last error: {last_exc}")
