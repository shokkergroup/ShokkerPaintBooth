"""Summarize generated scorecard drift without dumping the giant file.

Use this before deciding whether to ratchet, regenerate, or review
paint-booth-0-catalog-scorecard.js. It compares the working copy against a git
reference and prints bounded key counts plus small samples.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORECARD = ROOT / "paint-booth-0-catalog-scorecard.js"


def read_git_file(ref: str, rel_path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{ref}:{rel_path}"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def load_scorecard(text: str) -> dict[str, dict]:
    match = re.search(r"=\s*(\{.*\});", text, flags=re.S)
    if not match:
        raise RuntimeError("Could not locate scorecard object literal.")
    return json.loads(match.group(1))


def line_count(text: str) -> int:
    return len(text.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD", help="Git ref to compare against.")
    parser.add_argument("--sample", type=int, default=20, help="Max keys to show per bucket.")
    args = parser.parse_args()

    rel_path = SCORECARD.relative_to(ROOT).as_posix()
    current_text = SCORECARD.read_text(encoding="utf-8")
    ref_text = read_git_file(args.ref, rel_path)
    current = load_scorecard(current_text)
    baseline = load_scorecard(ref_text)

    current_keys = set(current)
    baseline_keys = set(baseline)
    added = sorted(current_keys - baseline_keys)
    removed = sorted(baseline_keys - current_keys)
    changed = sorted(key for key in current_keys & baseline_keys if current[key] != baseline[key])

    print(f"scorecard_drift_summary ref={args.ref}")
    print(f"entries: {len(baseline)} -> {len(current)} (delta {len(current) - len(baseline):+d})")
    print(f"lines: {line_count(ref_text)} -> {line_count(current_text)} (delta {line_count(current_text) - line_count(ref_text):+d})")
    print(f"added: {len(added)}")
    print(f"removed: {len(removed)}")
    print(f"changed_existing: {len(changed)}")
    if added:
        print("added_sample:")
        for key in added[: args.sample]:
            print(f"  + {key}")
    if removed:
        print("removed_sample:")
        for key in removed[: args.sample]:
            print(f"  - {key}")
    if changed:
        print("changed_sample:")
        for key in changed[: args.sample]:
            print(f"  * {key}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
