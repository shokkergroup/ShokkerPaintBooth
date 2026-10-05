"""Build the Spec Sculpt spec index (offline). Renders every base+monolithic spec
small and writes engine/spec_sculpt/spec_index.json for pick_diverse() at runtime.

Run after the finish registry changes:
  python scripts/build_spec_index.py [--size 64]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.spec_sculpt.spec_index import build_spec_index  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=64)
    args = ap.parse_args()
    build_spec_index(size=args.size)


if __name__ == "__main__":
    main()
