"""Compatibility wrapper for baking Union Jacked JPG runtime derivatives."""

from __future__ import annotations

from bake_cultural_jpg_runtime import PACK_DIRS, bake_pack


if __name__ == "__main__":
    bake_pack("union_jacked", PACK_DIRS["union_jacked"])
