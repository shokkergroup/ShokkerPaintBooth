"""Apply the round-5 corrective rebuild bodies to spec_patterns.py + artistic.py."""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from rebuild_bodies_tick import REBUILDS

PROJECT_ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"

SPEC_PATTERNS_PATH = os.path.join(PROJECT_ROOT, "engine", "spec_patterns.py")
ARTISTIC_PATH = os.path.join(PROJECT_ROOT, "engine", "spec_pattern_families", "artistic.py")

# Which names live in artistic.py
ARTISTIC_NAMES = {"crayon_wax_resist"}


def replace_function(src, name, new_body):
    """Replace the existing top-level `def name(...)` block with new_body.

    Finds line index of `def name(` not indented, finds end (next top-level
    def OR end-of-file). Includes any immediately-following `<name>._spb_xxx`
    attribute assignments in the deleted span. Trims one trailing blank line
    if present (we preserve the same spacing).
    """
    lines = src.split("\n")
    # Find def line
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"def " + re.escape(name) + r"\s*\(", ln) and not ln.startswith(" "):
            start = i
            break
    if start is None:
        raise RuntimeError(f"Could not find def {name}")

    # Find end — next top-level def OR top-level class OR module-level
    # statement that isn't an attribute assignment for our function.
    end = len(lines)
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln.startswith("def ") or ln.startswith("class "):
            end = j
            break
        # Top-level non-indented assignments? consume our own _spb_concept_complete
        # but stop at OTHER top-level statements that aren't comments/blanks/our-attr.
        if ln and not ln[0].isspace() and not ln.startswith("#"):
            # If it's "<name>." attribute set, swallow it
            if ln.startswith(name + "."):
                continue
            # otherwise: stop (this is the next thing)
            end = j
            break

    # Trim trailing blank lines from the *replacement region* so we keep
    # blank-line spacing consistent: collect from end-1 backward.
    block_end = end
    while block_end > start and lines[block_end - 1].strip() == "":
        block_end -= 1

    # Build replacement — new_body ends with `<name>._spb_concept_complete = True`,
    # which intentionally has NO trailing newline; split into lines:
    body_lines = new_body.rstrip("\n").split("\n")

    new_lines = lines[:start] + body_lines + lines[block_end:]
    return "\n".join(new_lines)


def apply_to_file(path, names):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    for name in names:
        body = REBUILDS[name]
        src = replace_function(src, name, body)
        print(f"  applied {name}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)


def main():
    # Apply to spec_patterns.py
    spec_names = [n for n in REBUILDS if n not in ARTISTIC_NAMES]
    print(f"Patching {SPEC_PATTERNS_PATH} ({len(spec_names)} patterns)")
    apply_to_file(SPEC_PATTERNS_PATH, spec_names)

    # Apply to artistic.py
    art_names = [n for n in REBUILDS if n in ARTISTIC_NAMES]
    print(f"Patching {ARTISTIC_PATH} ({len(art_names)} patterns)")
    apply_to_file(ARTISTIC_PATH, art_names)
    print("done")


if __name__ == "__main__":
    main()
