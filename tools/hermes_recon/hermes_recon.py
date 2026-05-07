#!/usr/bin/env python3
"""Read-only SPB recon loop powered by OpenRouter.

The runner intentionally does not edit app source. It gathers a compact
snapshot of the project, asks the configured model for finish/pattern/spec
improvement ideas, and writes Markdown briefings to codex_recon_inbox.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_PATH = SCRIPT_DIR / "state.json"
PID_PATH = SCRIPT_DIR / "hermes_recon.pid"
LOG_PATH = SCRIPT_DIR / "hermes_recon.log"
MISSION_PATH = PROJECT_ROOT / "HERMES_RECON_MISSION.md"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


DEFAULT_CONFIG = {
    "model": "deepseek/deepseek-v4-flash",
    "interval_minutes": 15,
    "output_dir": "codex_recon_inbox",
    "max_input_chars": 55000,
    "max_output_tokens": 3600,
    "temperature": 0.72,
    "focus_rotation": [
        "finish_quality",
        "spec_map_depth",
        "pattern_library",
        "color_systems",
        "ui_finish_workflow",
        "render_performance",
        "catalog_consistency",
        "export_polish",
    ],
}


FOCUS_FILES = {
    "finish_quality": [
        "engine/paint_v2/paint_technique.py",
        "engine/paint_v2/candy_special.py",
        "engine/paint_v2/structural_color.py",
        "engine/spec_paint.py",
        "paint-booth-0-finish-data.js",
    ],
    "spec_map_depth": [
        "engine/spec_paint.py",
        "engine/paint_v2/metallic_flake.py",
        "engine/paint_v2/metallic_standard.py",
        "engine/paint_v2/paradigm_scifi.py",
        "RESEARCH_REFERENCE.md",
    ],
    "pattern_library": [
        "engine/pattern_expansion.py",
        "engine/spec_patterns.py",
        "paint-booth-4-pattern-renderer.js",
        "paint-booth-layer-flow.js",
        "shokker_engine_v2.py",
    ],
    "color_systems": [
        "SPB_COLOR_THEORY.md",
        "SPB_COLOR_COMBINATIONS.md",
        "SPB_RECIPE_PAIRINGS.md",
        "palettes",
        "custom_finishes.json",
    ],
    "ui_finish_workflow": [
        "paint-booth-v2.html",
        "paint-booth-v2.css",
        "paint-booth-6-ui-boot.js",
        "paint-booth-2-state-zones.js",
        ".claude/USER_PREFERENCES.md",
    ],
    "render_performance": [
        ".claude/PERF_PATTERNS.md",
        "benchmark_finishes.py",
        "engine/render.py",
        "engine/compose.py",
        "server.py",
    ],
    "catalog_consistency": [
        "paint-booth-0-finish-data.js",
        "paint-booth-0-finish-metadata.js",
        "engine/registry.py",
        "engine/expansions",
        "tests",
    ],
    "export_polish": [
        "server.py",
        "server_v5.py",
        "scripts/optimize_spec_for_trading_paints.py",
        "scripts/diagnose_iracing_spec_package.py",
        "SPB_IRACING_INTEGRATION.md",
    ],
}


BASELINE_FILES = [
    ".claude/SPB_SOURCE_OF_TRUTH.md",
    ".claude/RULES.md",
    ".claude/USER_PREFERENCES.md",
    "RESEARCH_REFERENCE.md",
    "SHOKKER_BIBLE.md",
    "SPB_DESIGN_PRINCIPLES.md",
]


def log(message: str) -> None:
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        config.update(loaded)
    return config


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"runs": 0}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return {"runs": 0}


def save_state(state: dict) -> None:
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def parse_simple_yaml_scalar(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            value = stripped.split(":", 1)[1].strip().strip("'\"")
            if value:
                return value
    return None


def get_openrouter_key() -> str:
    env_key = os.environ.get("OPENROUTER_API_KEY")
    if env_key:
        return env_key

    hermes_home = Path.home() / ".hermes"
    for env_path in [
        SCRIPT_DIR / ".env",
        hermes_home / ".env",
        hermes_home / "hermes-agent" / ".env",
    ]:
        env_values = read_env_file(env_path)
        if env_values.get("OPENROUTER_API_KEY"):
            return env_values["OPENROUTER_API_KEY"]

    cli_key = parse_simple_yaml_scalar(hermes_home / "hermes-agent" / "cli-config.yaml", "api_key")
    if cli_key:
        return cli_key

    raise RuntimeError(
        "No OpenRouter key found. Put OPENROUTER_API_KEY in tools/hermes_recon/.env "
        "or configure Hermes with an OpenRouter key."
    )


def git_status_summary() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return f"git status unavailable: {exc}"
    lines = result.stdout.splitlines()
    if not lines:
        return "clean"
    return "\n".join(lines[:120]) + ("\n...truncated..." if len(lines) > 120 else "")


def list_tree(path: Path, max_items: int = 80) -> str:
    if not path.exists():
        return "(missing)"
    if path.is_file():
        return path.name
    items: list[str] = []
    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name in {"node_modules", "__pycache__", ".git", "dist", "pyserver"}:
            continue
        marker = "/" if child.is_dir() else ""
        items.append(f"{child.name}{marker}")
        if len(items) >= max_items:
            items.append("...truncated...")
            break
    return "\n".join(items)


def read_snippet(relative: str, max_chars: int = 5000) -> str:
    path = PROJECT_ROOT / relative
    if not path.exists():
        return f"## {relative}\n(missing)\n"
    if path.is_dir():
        return f"## {relative}/\n{list_tree(path)}\n"
    text = path.read_text(encoding="utf-8", errors="ignore")
    if len(text) <= max_chars:
        snippet = text
    else:
        half = max_chars // 2
        snippet = text[:half] + "\n\n...[middle truncated]...\n\n" + text[-half:]
    return f"## {relative}\n```text\n{snippet}\n```\n"


def prior_recon_summary(output_dir: Path) -> str:
    if not output_dir.exists():
        return "(no prior recon briefs yet)"
    files = sorted(output_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [path for path in files if path.name.lower() not in {"readme.md", "index.md"}]
    if not files:
        return "(no prior recon briefs yet)"

    summaries: list[str] = []
    for path in files[:8]:
        first_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:12]
        title = next((line for line in first_lines if line.startswith("#")), path.stem)
        summaries.append(f"- {path.name}: {title.lstrip('#').strip()}")
    return "\n".join(summaries)


def mission_text() -> str:
    if not MISSION_PATH.exists():
        return "(no custom mission file found)"
    text = MISSION_PATH.read_text(encoding="utf-8", errors="ignore").strip()
    return text or "(mission file is empty)"


def choose_focus(config: dict, state: dict, explicit_focus: str | None) -> str:
    if explicit_focus:
        return explicit_focus
    rotation = config.get("focus_rotation") or DEFAULT_CONFIG["focus_rotation"]
    index = int(state.get("runs", 0)) % len(rotation)
    return str(rotation[index])


def build_snapshot(config: dict, focus: str) -> str:
    output_dir = PROJECT_ROOT / str(config["output_dir"])
    max_input_chars = int(config["max_input_chars"])

    sections = [
        "# Project Snapshot",
        f"Timestamp: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Project root: {PROJECT_ROOT}",
        f"Current focus: {focus}",
        "",
        "## Git Status",
        git_status_summary(),
        "",
        "## Top-Level Inventory",
        list_tree(PROJECT_ROOT, max_items=120),
        "",
        "## Prior Recon Briefs To Avoid Repeating",
        prior_recon_summary(output_dir),
        "",
        "## Ricky's Current Mission For HERMES",
        mission_text(),
        "",
        "## Baseline Project Knowledge",
    ]

    for relative in BASELINE_FILES:
        sections.append(read_snippet(relative, max_chars=3500))

    sections.append("## Focus Evidence")
    focus_files = FOCUS_FILES.get(focus, [])
    for relative in focus_files:
        sections.append(read_snippet(relative, max_chars=6500))

    snapshot = "\n\n".join(sections)
    if len(snapshot) > max_input_chars:
        snapshot = snapshot[:max_input_chars] + "\n\n...[snapshot truncated at configured limit]...\n"
    return snapshot


def system_prompt() -> str:
    return textwrap.dedent(
        """
        You are HERMES Recon for Shokker Paint Booth Gold to Platinum.

        Your only job is read-only reconnaissance. Do not ask to edit files.
        Do not claim you changed code. Produce useful, specific improvement
        briefings that Codex can later use to make changes.

        Think like a senior automotive finish designer plus a graphics/rendering
        engineer. Look for ways to improve every finish across the board:
        paint functions, spec maps, roughness/metallic/clearcoat behavior,
        pattern distinctiveness, color palette quality, UI workflow, renderer
        performance, iRacing export polish, and catalog consistency.

        Avoid generic ideas. Tie every recommendation to concrete files,
        observed patterns, likely implementation steps, verification checks,
        and risks. Prefer ideas that improve many finishes at once.
        """
    ).strip()


def user_prompt(snapshot: str, focus: str) -> str:
    return textwrap.dedent(
        f"""
        Create one Markdown recon brief for Codex.

        Focus this cycle on: {focus}

        Required format:

        # HERMES Recon Brief - {focus}
        ## Fast Read
        A concise 3-5 bullet summary.

        ## Improvement Ideas
        Give 3-6 ideas. For each idea include:
        - Codex task
        - Why it matters
        - Evidence from the snapshot
        - Files likely involved
        - Implementation sketch
        - Verification plan
        - Risk / watch-outs

        ## Weird But Promising
        One unusual idea that might create a distinctive SPB advantage.

        ## Codex Pickup Queue
        A short prioritized checklist Codex can act on later.

        ## Do Not Repeat Next Cycle
        Bullet list of this brief's core themes so future recon can avoid repeats.

        Project snapshot:

        {snapshot}
        """
    ).strip()


def call_openrouter(api_key: str, config: dict, focus: str, snapshot: str) -> str:
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(snapshot, focus)},
        ],
        "temperature": float(config["temperature"]),
        "max_tokens": int(config["max_output_tokens"]),
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://shokkergroup.com",
            "X-Title": "SPB HERMES Recon",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {error_body[:1200]}") from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter returned no choices: {body}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError(f"OpenRouter returned an empty message: {body}")
    return content


def ascii_markdown(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00d7": "x",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2192": "->",
        "\u2011": "-",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode("ascii", errors="ignore").decode("ascii")


def write_brief(config: dict, focus: str, content: str) -> Path:
    output_dir = PROJECT_ROOT / str(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_focus = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in focus)
    path = output_dir / f"{stamp}-{safe_focus}.md"
    header = textwrap.dedent(
        f"""
        <!--
        Generated by HERMES Recon.
        Model: {config["model"]}
        Time: {dt.datetime.now().isoformat(timespec="seconds")}
        This file is an idea brief only. Codex should verify before editing.
        -->

        """
    ).lstrip()
    path.write_text(header + ascii_markdown(content).strip() + "\n", encoding="utf-8")
    update_index(output_dir, path, focus, config["model"])
    return path


def update_index(output_dir: Path, latest: Path, focus: str, model: str) -> None:
    index_path = output_dir / "INDEX.md"
    entry = f"- {dt.datetime.now().isoformat(timespec='seconds')} - `{focus}` - `{model}` - [{latest.name}]({latest.name})\n"
    if index_path.exists():
        existing = index_path.read_text(encoding="utf-8", errors="ignore")
    else:
        existing = "# HERMES Recon Index\n\nNewest briefs are listed first.\n\n"
    lines = existing.splitlines(keepends=True)
    header = lines[:3] if len(lines) >= 3 else ["# HERMES Recon Index\n", "\n", "Newest briefs are listed first.\n", "\n"]
    old_entries = [line for line in lines if line.startswith("- ")]
    index_path.write_text("".join(header) + "\n" + entry + "".join(old_entries[:80]), encoding="utf-8")


def run_once(config: dict, explicit_focus: str | None = None, dry_run: bool = False) -> Path | None:
    state = load_state()
    focus = choose_focus(config, state, explicit_focus)
    snapshot = build_snapshot(config, focus)

    if dry_run:
        preview_path = SCRIPT_DIR / "last_snapshot_preview.txt"
        preview_path.write_text(snapshot, encoding="utf-8")
        print(f"Dry run OK. Snapshot preview written to {preview_path}")
        print(f"Model would be: {config['model']}")
        print(f"Focus would be: {focus}")
        return None

    api_key = get_openrouter_key()
    log(f"starting recon run focus={focus} model={config['model']}")
    content = call_openrouter(api_key, config, focus, snapshot)
    path = write_brief(config, focus, content)
    state["runs"] = int(state.get("runs", 0)) + 1
    state["last_focus"] = focus
    state["last_output"] = str(path)
    state["last_run"] = dt.datetime.now().isoformat(timespec="seconds")
    save_state(state)
    log(f"completed recon run output={path}")
    print(f"Wrote {path}")
    return path


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid() -> int | None:
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def write_pid() -> None:
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")


def stop_loop() -> None:
    pid = read_pid()
    if not pid:
        print("HERMES Recon is not running.")
        return
    if not process_is_running(pid):
        PID_PATH.unlink(missing_ok=True)
        print("Stale PID removed. HERMES Recon was not running.")
        return
    os.kill(pid, signal.SIGTERM)
    PID_PATH.unlink(missing_ok=True)
    print(f"Stopped HERMES Recon process {pid}.")


def show_status() -> None:
    pid = read_pid()
    config = load_config()
    state = load_state()
    if pid and process_is_running(pid):
        running = f"running as PID {pid}"
    else:
        running = "not running"
    print(f"HERMES Recon is {running}.")
    print(f"Model: {config['model']}")
    print(f"Interval: {config['interval_minutes']} minutes")
    print(f"Output: {PROJECT_ROOT / str(config['output_dir'])}")
    if state.get("last_run"):
        print(f"Last run: {state['last_run']}")
        print(f"Last output: {state.get('last_output', '(unknown)')}")


def run_loop(config: dict, explicit_focus: str | None = None) -> None:
    old_pid = read_pid()
    if old_pid and process_is_running(old_pid):
        print(f"HERMES Recon is already running as PID {old_pid}.")
        return
    write_pid()
    interval_seconds = max(60, int(float(config["interval_minutes"]) * 60))
    log(f"loop started pid={os.getpid()} interval_seconds={interval_seconds}")

    def handle_stop(signum, frame):  # type: ignore[no-untyped-def]
        log(f"loop stopping signal={signum}")
        PID_PATH.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    while True:
        try:
            run_once(config, explicit_focus=explicit_focus)
        except Exception as exc:
            log(f"run failed: {exc}")
            print(f"HERMES Recon run failed: {exc}", file=sys.stderr)
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="SPB HERMES Recon runner")
    parser.add_argument("--once", action="store_true", help="Run one recon cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run forever at the configured interval")
    parser.add_argument("--stop", action="store_true", help="Stop the background loop")
    parser.add_argument("--status", action="store_true", help="Show current loop status")
    parser.add_argument("--dry-run", action="store_true", help="Build the prompt snapshot without calling OpenRouter")
    parser.add_argument("--focus", help="Override the configured focus rotation for this run")
    args = parser.parse_args()

    config = load_config()
    if args.stop:
        stop_loop()
        return 0
    if args.status:
        show_status()
        return 0
    if args.loop:
        run_loop(config, explicit_focus=args.focus)
        return 0
    if args.once or args.dry_run:
        run_once(config, explicit_focus=args.focus, dry_run=args.dry_run)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
