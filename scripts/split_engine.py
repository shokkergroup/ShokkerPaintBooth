"""
Extract a line range from shokker_engine_v2.py into a new module and patch the main file.
Run from V5 folder. Uses line-by-line read to avoid loading the whole file.

Usage:
  python scripts/split_engine.py utils 67 186
  python scripts/split_engine.py blend 6650 6720

First run: creates engine/utils.py from lines 67-186 and adds import, removes block.
"""
import os
import sys

V5 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_PY = os.path.join(V5, "shokker_engine_v2.py")
ENGINE_DIR = os.path.join(V5, "engine")


def read_lines(path, start, end):
    """Read lines start..end (1-based inclusive). Returns list of lines."""
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if i > end:
                break
            if i >= start:
                out.append(line)
    return out


def write_module(module_name, lines, imports_needed):
    """Write engine/<module_name>.py with header and extracted code."""
    os.makedirs(ENGINE_DIR, exist_ok=True)
    out_path = os.path.join(ENGINE_DIR, f"{module_name}.py")
    header = f'''"""
Extracted from shokker_engine_v2.py for maintainability.
"""
'''
    import_line = "\n".join(imports_needed) + "\n\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(import_line)
        for line in lines:
            f.write(line)
    print(f"Wrote {out_path}")


def patch_main(insert_after_line, import_line, remove_start, remove_end):
    """Patch shokker_engine_v2.py: remove block first, then add import after line N."""
    with open(ENGINE_PY, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    # Remove block (0-based), replace with comment
    lo, hi = remove_start - 1, remove_end
    comment = f"# (TGA + noise moved to engine.utils)\n"
    new_lines = all_lines[:lo] + [comment] + all_lines[hi:]

    # Insert import after insert_after_line (1-based; unchanged by removal since block is below)
    idx = insert_after_line - 1
    if import_line not in "".join(new_lines):
        new_lines.insert(idx + 1, "\n" + import_line + "\n")

    with open(ENGINE_PY, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Patched {ENGINE_PY}: added import, removed lines {remove_start}-{remove_end}")


def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/split_engine.py <name> <start_line> <end_line>")
        print("Example: python scripts/split_engine.py utils 67 186")
        sys.exit(1)
    name = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])

    if name == "utils":
        lines = read_lines(ENGINE_PY, start, end)
        imports = ["import numpy as np", "import struct"]
        write_module("utils", lines, imports)
        patch_main(
            60,  # after "import time"
            "from engine.utils import write_tga_32bit, write_tga_24bit, get_mgrid, generate_perlin_noise_2d, perlin_multi_octave",
            start,
            end,
        )
    else:
        print("Unknown extract name. Use 'utils' for TGA+noise.")
        sys.exit(1)


if __name__ == "__main__":
    main()
