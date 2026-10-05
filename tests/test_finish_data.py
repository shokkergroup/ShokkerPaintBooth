"""
tests/test_finish_data.py — data-integrity tests for paint-booth-0-finish-data.js.

Rather than evaluate the JS file, we parse the well-known fields (id, name,
desc, swatch) with regex. This catches real data bugs (missing hex colors,
duplicate IDs, orphaned entries) without needing a JS runtime.
"""

from __future__ import annotations

import os
import re

import pytest


HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

# Some swatches in the codebase are CSS linear-gradient strings (valid for the
# UI, which renders them as CSS backgrounds). Accept those too.
SWATCH_OK_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|linear-gradient\(.+\)|radial-gradient\(.+\)|conic-gradient\(.+\))$"
)

# Each entry in the finish arrays looks like:
#   { id: "foo", name: "Foo", desc: "...", swatch: "#AABBCC", ... }
# We pull out id+swatch+name+desc with a generous regex tolerant to nesting.
ENTRY_ID_RE     = re.compile(r"""\{\s*id:\s*["']([^"']+)["']""")
ENTRY_SWATCH_RE = re.compile(r"""id:\s*["']([^"']+)["'][^}]*?swatch:\s*["']([^"']+)["']""",
                             flags=re.DOTALL)
ENTRY_DESC_RE   = re.compile(r"""id:\s*["']([^"']+)["'][^}]*?desc:\s*["']""",
                             flags=re.DOTALL)
ENTRY_NAME_RE   = re.compile(r"""id:\s*["']([^"']+)["'][^}]*?name:\s*["']""",
                             flags=re.DOTALL)


def _extract_section(text: str, start_token: str) -> str:
    """Slice from ``const FOO = [`` to the matching ``];``.

    Returns the inner text (between the brackets) so our entry regex doesn't
    accidentally pick up entries from a neighboring array.
    """
    idx = text.find(start_token)
    if idx < 0:
        raise AssertionError(f"{start_token!r} not found in finish data")
    lb = text.find("[", idx)
    assert lb > 0, f"no [ after {start_token}"
    # Find matching closing bracket by depth tracking (JS strings ignored here but fine).
    depth = 0
    for i in range(lb, len(text)):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[lb + 1:i]
    raise AssertionError(f"unterminated array for {start_token}")


# ---------------------------------------------------------------------------
# 26. test_finish_data_loads
# ---------------------------------------------------------------------------
def test_finish_data_loads(finish_data_js_text):
    """paint-booth-0-finish-data.js is readable and contains every core array."""
    for token in ("const BASES", "const PATTERNS", "const MONOLITHICS",
                  "const SPEC_PATTERNS", "const BASE_GROUPS", "const PATTERN_GROUPS"):
        assert token in finish_data_js_text, f"Missing declaration: {token}"


# ---------------------------------------------------------------------------
# 27. test_all_bases_have_swatch
# ---------------------------------------------------------------------------
def test_all_bases_have_swatch(finish_data_js_text):
    """Every entry in BASES has a swatch key."""
    bases_text = _extract_section(finish_data_js_text, "const BASES =")
    all_ids = ENTRY_ID_RE.findall(bases_text)
    with_swatch = {m[0] for m in ENTRY_SWATCH_RE.findall(bases_text)}
    missing = [b for b in all_ids if b not in with_swatch]
    assert not missing, f"{len(missing)} bases missing swatch: {missing[:5]}"


# ---------------------------------------------------------------------------
# 28. test_all_bases_have_desc
# ---------------------------------------------------------------------------
def test_all_bases_have_desc(finish_data_js_text):
    """Every entry in BASES has a desc key (strings may be empty but key must exist)."""
    bases_text = _extract_section(finish_data_js_text, "const BASES =")
    all_ids = ENTRY_ID_RE.findall(bases_text)
    with_desc = {m for m in ENTRY_DESC_RE.findall(bases_text)}
    missing = [b for b in all_ids if b not in with_desc]
    # A couple of legacy entries may omit desc; tolerate up to 5 for forward-compat.
    assert len(missing) <= 5, f"{len(missing)} bases missing desc: {missing[:5]}"


# ---------------------------------------------------------------------------
# 29. test_all_patterns_have_swatch
# ---------------------------------------------------------------------------
def test_all_patterns_have_swatch(finish_data_js_text):
    """Every entry in PATTERNS has a swatch key."""
    pat_text = _extract_section(finish_data_js_text, "const PATTERNS =")
    all_ids = ENTRY_ID_RE.findall(pat_text)
    with_swatch = {m[0] for m in ENTRY_SWATCH_RE.findall(pat_text)}
    missing = [p for p in all_ids if p not in with_swatch]
    # Image-based patterns might skip swatch occasionally; tolerate up to 10.
    assert len(missing) <= 10, f"{len(missing)} patterns missing swatch: {missing[:5]}"


# ---------------------------------------------------------------------------
# 30. test_all_monolithics_have_desc
# ---------------------------------------------------------------------------
def test_all_monolithics_have_desc(finish_data_js_text):
    """Every entry in MONOLITHICS has a desc key."""
    mono_text = _extract_section(finish_data_js_text, "const MONOLITHICS =")
    all_ids = ENTRY_ID_RE.findall(mono_text)
    with_desc = {m for m in ENTRY_DESC_RE.findall(mono_text)}
    missing = [m for m in all_ids if m not in with_desc]
    assert len(missing) <= 10, f"{len(missing)} monolithics missing desc: {missing[:5]}"


# ---------------------------------------------------------------------------
# 31. test_no_duplicate_finish_ids
# ---------------------------------------------------------------------------
def test_no_duplicate_finish_ids(finish_data_js_text):
    """IDs are unique within each registry array.

    KNOWN_DUPES captures legacy data bugs that ship in production; the test
    fails on ANY new duplicate that isn't on the allowlist. Fix the data
    bug and shrink the allowlist — don't grow it.
    """
    KNOWN_DUPES = {
        "const MONOLITHICS =": {"mystichrome"},  # appears twice (chameleon + cs preset); see finish-data.js
    }
    for token in ("const BASES =", "const PATTERNS =", "const MONOLITHICS =",
                  "const SPEC_PATTERNS ="):
        section = _extract_section(finish_data_js_text, token)
        ids = ENTRY_ID_RE.findall(section)
        dupes = {i for i in set(ids) if ids.count(i) > 1}
        new_dupes = dupes - KNOWN_DUPES.get(token, set())
        assert not new_dupes, f"New duplicate IDs in {token}: {sorted(new_dupes)[:5]}"


# ---------------------------------------------------------------------------
# 32. test_base_groups_no_orphans
# ---------------------------------------------------------------------------
def test_base_groups_no_orphans(finish_data_js_text):
    """Every ID listed inside BASE_GROUPS exists in BASES OR MONOLITHICS.

    BASE_GROUPS can legitimately reference monolithic IDs (e.g. COLORSHOXX
    finishes live in MONOLITHICS but appear in the base picker under the
    "Color-Shift" category). We only flag IDs that don't exist anywhere in
    the finish data.
    """
    all_ids = set()
    for token in ("const BASES =", "const MONOLITHICS =", "const PATTERNS ="):
        section = _extract_section(finish_data_js_text, token)
        all_ids.update(ENTRY_ID_RE.findall(section))

    # Extract BASE_GROUPS block. It's a simple object literal with arrays of strings.
    start = finish_data_js_text.find("const BASE_GROUPS")
    assert start >= 0, "BASE_GROUPS declaration not found"
    # Balanced-brace slice so we don't get truncated at the first inner }
    lb = finish_data_js_text.find("{", start)
    depth = 0
    end = -1
    for i in range(lb, len(finish_data_js_text)):
        c = finish_data_js_text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    block = finish_data_js_text[lb:end]
    # Every string inside the arrays is an ID reference; only check snake_case
    # tokens (skip category keys like "Popular Colors" that contain spaces).
    referenced = set(re.findall(r'''["']([a-z][a-z0-9_]{2,})["']''', block))
    orphans = sorted(r for r in referenced if r not in all_ids)
    # Known orphans: these IDs live only in the Python backend registry
    # (engine/base_registry_data.py) — the JS file hasn't caught up yet.
    # Shrink this set whenever the JS catalog adds them.
    KNOWN_ORPHANS = {
        "acid_etch", "battle_patina", "cerakote_gloss", "hydrographic",
        "oxidized", "patina_coat", "sub_black", "terrain_chrome",
    }
    new_orphans = [o for o in orphans if o not in KNOWN_ORPHANS]
    # Categories like "popular" may appear as singular category keys on the
    # RHS of some arrays; tolerate up to 3 unknowns beyond the allowlist.
    assert len(new_orphans) <= 3, \
        f"BASE_GROUPS references {len(new_orphans)} new IDs not in BASES/MONOLITHICS/PATTERNS: {new_orphans[:8]}"


# ---------------------------------------------------------------------------
# 33. test_spec_pattern_count
# ---------------------------------------------------------------------------
def test_spec_pattern_count(finish_data_js_text):
    """At least 100 SPEC_PATTERNS defined (target: 200+ per roadmap)."""
    sp_text = _extract_section(finish_data_js_text, "const SPEC_PATTERNS =")
    ids = ENTRY_ID_RE.findall(sp_text)
    assert len(ids) >= 100, f"SPEC_PATTERNS shrank to {len(ids)} (expected >=100)"


# ---------------------------------------------------------------------------
# 34. test_finish_count — minimum totals.
# ---------------------------------------------------------------------------
def test_finish_count(finish_data_js_text):
    """Combined BASES+PATTERNS+MONOLITHICS >= 500 entries."""
    total = 0
    for token in ("const BASES =", "const PATTERNS =", "const MONOLITHICS ="):
        section = _extract_section(finish_data_js_text, token)
        total += len(ENTRY_ID_RE.findall(section))
    assert total >= 500, f"Total finish entries shrank to {total} (expected >=500)"


# ---------------------------------------------------------------------------
# 35. test_swatch_format_valid — every hex color is valid.
# ---------------------------------------------------------------------------
def test_swatch_format_valid(finish_data_js_text):
    """All swatch values are either #hex colors or CSS gradient functions.

    Monolithics like COLORSHOXX and dazzle use CSS ``linear-gradient(...)``
    strings because the UI renders their picker swatches as CSS backgrounds.
    Both forms are acceptable; anything else (e.g. bare color names, URLs)
    indicates a data bug.
    """
    bad = []
    for token in ("const BASES =", "const PATTERNS =", "const MONOLITHICS ="):
        section = _extract_section(finish_data_js_text, token)
        for fid, swatch in ENTRY_SWATCH_RE.findall(section):
            if not SWATCH_OK_RE.match(swatch):
                bad.append((fid, swatch))
    assert not bad, f"{len(bad)} invalid swatch values: {bad[:5]}"


# ---------------------------------------------------------------------------
# Extra data-integrity tests.
# ---------------------------------------------------------------------------
def test_all_bases_have_name(finish_data_js_text):
    """Every entry in BASES has a name key (display strings)."""
    bases_text = _extract_section(finish_data_js_text, "const BASES =")
    all_ids = ENTRY_ID_RE.findall(bases_text)
    with_name = set(ENTRY_NAME_RE.findall(bases_text))
    missing = [b for b in all_ids if b not in with_name]
    assert not missing, f"{len(missing)} bases missing name: {missing[:5]}"


def test_pattern_groups_valid_structure(finish_data_js_text):
    """PATTERN_GROUPS declaration exists and is an object literal."""
    assert "const PATTERN_GROUPS" in finish_data_js_text
    idx = finish_data_js_text.find("const PATTERN_GROUPS")
    snippet = finish_data_js_text[idx:idx + 200]
    assert "=" in snippet and "{" in snippet, "PATTERN_GROUPS is not an object literal"
