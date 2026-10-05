"""Run the real SPB V5 app on an explicitly isolated verification port.

This deliberately imports ``server_v5`` instead of executing its ``__main__``
block.  That avoids clean-boot process killing, the shared ``.server_port``
file, and boot-time swatch warming while still exercising the exact Flask app
and inherited production routes used by Electron.
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    raw_port = os.environ.get("SHOKKER_PORT", "").strip()
    if not raw_port:
        raise SystemExit("SHOKKER_PORT is required for isolated verification")
    port = int(raw_port)
    if port == 59876:
        raise SystemExit("isolated verification refuses the live/developer port 59876")

    os.environ["SHOKKER_NO_CLEAN"] = "1"
    os.environ["SPB_NO_LIVE_LINK"] = "1"
    os.environ["SPB_NO_BOOT_SWATCH_WARM"] = "1"
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # The bundled runtime prepends electron-app/server to sys.path.  Isolated
    # source verification must load the canonical root tree so a test cannot
    # silently exercise a stale installer mirror before the final sync gate.
    try:
        sys.path.remove(root)
    except ValueError:
        pass
    sys.path.insert(0, root)
    os.environ.setdefault(
        "SPB_ISOLATED_OUTPUT_DIR",
        os.path.join(
            root,
            "_release_evidence",
            f"manual-isolated-{os.getpid()}",
            "server-output",
        ),
    )

    import server_v5

    server_v5.app.run(
        host="127.0.0.1",
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
