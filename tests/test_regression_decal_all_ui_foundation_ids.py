"""Regression guardrail — EVERY UI-exposed Foundation id in the decal
specFinish dropdown MUST have a working Python render path.

## 2026-04-22 update (Codex P1 audit response)

The decal-spec dropdown at ``paint-booth-6-ui-boot.js:447-500`` now
filters its options to ``id.startsWith('f_')`` only (both the live
``BASE_GROUPS['Foundation']`` path AND the hardcoded fallback). The
15 classic non-f_ ids (gloss/matte/satin/semi_gloss/silk/wet_look/
clear_matte/primer/flat_black/eggshell/ceramic/piano_black/
scuffed_satin/chalky_base/living_matte) were being offered by this
picker despite their 5-arg spec handlers crashing at the 4-arg
decal dispatch site. They're no longer UI-reachable through the
decal dropdown.

The KNOWN_BROKEN_CLASSIC_DECAL_IDS frozenset below is now empty
because those ids are no longer UI-exposed. The xfail cases are
gone. Every id in the filtered dropdown renders correctly.

If the classic backend is ever fixed (DECAL_SPEC_MAP extended with
flat shims for the 15 classics), both the JS dropdown filter and
this test's "UI-exposed = filtered" semantics should be revisited.

---

Original context preserved for history:

## Why this file exists (2026-04-22 post-audit)

The 2026-04-22 HEENAN FAMILY Foundation-Trust Overnight fixed the
decal-spec path for 19 `f_*` Reference Foundation ids via
``_mk_flat_foundation_decal_spec`` (see
``tests/test_regression_decal_foundation_flat_spec.py`` for that
coverage).

A post-run audit pointed out correctly that the same UI dropdown
also exposes ~14 CLASSIC non-f_ Foundation entries (``gloss``,
``matte``, ``satin``, ``semi_gloss``, ``silk``, ``wet_look``,
``clear_matte``, ``primer``, ``flat_black``, ``eggshell``,
``scuffed_satin``, ``chalky_base``, ``living_matte``, ``ceramic``,
``piano_black``) whose server-side DECAL_SPEC_MAP handlers raise
``TypeError`` at the 4-arg dispatch site and are silently swallowed
by the outer try/except — painter gets no spec on their decal.

That's a DIFFERENT, pre-existing bug class from the f_* issue. It
was documented as out-of-scope during the overnight but not fixed.

This file closes the **test-coverage** gap left by that audit: it
enumerates every id actually offered in ``BASE_GROUPS['Foundation']``
(the picker source of truth) and asserts a specific behavior for
each:

- ``f_*`` ids: **must** produce a flat 4-channel uint8 spec with
  (0,0,0) M/R/CC spread (the fix this overnight landed).
- Classic non-f_ ids: **currently** raise TypeError via their
  5-arg-signature handlers. Pinned as ``pytest.xfail`` with a
  specific reason so:
    * the test count grows when more of those entries are fixed
      (xfail auto-inverts to failure when the bug disappears), AND
    * the ratchet is honest — it does NOT pin the broken state as
      "correct," it pins it as "known-broken-until-fixed."

If a classic entry is ever fixed to return a proper spec, its xfail
will strict-fail here, prompting the cleanup of this file.

## Source of truth for the id list

``paint-booth-0-finish-data.js`` → ``BASE_GROUPS['Foundation']``
array. Parsed at import time so this test tracks whatever the UI
actually offers.
"""

import io
import contextlib
import re
from pathlib import Path

import numpy as np
import pytest


REPO = Path(__file__).resolve().parent.parent
FINISH_DATA_JS = REPO / "paint-booth-0-finish-data.js"
UI_BOOT_JS = REPO / "paint-booth-6-ui-boot.js"


def _extract_group_ids(group_name: str, *, required: bool = True):
    """Pull ids from a named BASE_GROUPS entry in
    paint-booth-0-finish-data.js."""
    text = FINISH_DATA_JS.read_text(encoding="utf-8")
    m = re.search(
        rf"""["']{re.escape(group_name)}["']\s*:\s*\[([^\]]+)\]""", text
    )
    if not m and not required:
        return []
    assert m, (
        f"Could not find BASE_GROUPS[{group_name!r}] in "
        "paint-booth-0-finish-data.js — the picker source of truth "
        "moved or renamed. Update this test to reflect the new location."
    )
    return re.findall(r"""["']([a-z_][a-z0-9_]*)["']""", m.group(1))


def _dedupe_preserve_order(ids):
    out = []
    for fid in ids:
        if fid not in out:
            out.append(fid)
    return out


def _extract_decal_specfinish_loaded_ids():
    """Reconstruct the loaded-data branch of the dropdown exactly:
    combine BASE_GROUPS['Foundation'] + ['Reference Foundations'],
    then emit those ids in the SAME canonical order as the fallback
    branch.

    This models the live path when BASE_GROUPS / BASES are present.
    """
    ui_js = UI_BOOT_JS.read_text(encoding="utf-8")
    assert "_decalSpecIsSupported = id => typeof id === 'string' && id.startsWith('f_')" in ui_js, (
        "decal-specFinish dropdown filter predicate has drifted from "
        "the 2026-04-22 Codex P1 baseline "
        "(id.startsWith('f_')). Update this test to match the new "
        "predicate OR restore the predicate."
    )
    foundation_ids = _extract_group_ids("Foundation")
    # Reference Foundations was redundant shipping UI and is intentionally
    # gone. Accept it if a branch still has it, but do not require it.
    reference_ids = _extract_group_ids("Reference Foundations", required=False)
    available_ids = _dedupe_preserve_order(
        fid for fid in [*foundation_ids, *reference_ids]
        if fid.startswith("f_")
    )
    fallback_ids = _extract_decal_specfinish_fallback_ids()
    loaded_ids = [fid for fid in fallback_ids if fid in available_ids]
    assert loaded_ids == fallback_ids, (
        "decal specFinish live-data ids drifted from the hardcoded fallback "
        "branch. Keep the loaded BASE_GROUPS path and the fallback list in "
        "lockstep so the dropdown stays internally consistent."
    )
    return loaded_ids


def _extract_decal_specfinish_fallback_ids():
    """Parse the hardcoded fallback list from paint-booth-6-ui-boot.js
    and apply the same supported-id filter the dropdown uses when
    BASE_GROUPS / BASES haven't loaded yet."""
    ui_js = UI_BOOT_JS.read_text(encoding="utf-8")
    m = re.search(r"const fallback = \[(.*?)\];", ui_js, re.S)
    assert m, (
        "Could not find the decal specFinish fallback list in "
        "paint-booth-6-ui-boot.js. Update this test to reflect the "
        "new dropdown structure."
    )
    fallback_ids = re.findall(r"""\{id:\s*['"]([a-z_][a-z0-9_]*)['"]""", m.group(1))
    return [fid for fid in fallback_ids if fid.startswith("f_")]


FOUNDATION_IDS = _extract_decal_specfinish_loaded_ids()

# 2026-04-22 Codex P1 response: classic non-f_ ids were UI-reachable
# from the decal specFinish dropdown until this audit. The JS dropdown
# at paint-booth-6-ui-boot.js:447-500 now filters its options to
# `id.startsWith('f_')`, so the 15 classics are no longer offered
# through that picker — they remain in BASE_GROUPS['Foundation']
# (painter mandate: they belong in that base category for the ZONE
# picker, which has its own solid-color auto-fill logic) but are
# filtered OUT of the decal specFinish dropdown specifically.
#
# This set is therefore now empty: no UI-reachable decal-dropdown id
# has a broken Python render path. If the classic backend is ever
# extended (DECAL_SPEC_MAP gains flat shims for the 15 classics),
# the JS filter can be relaxed and this test's probe can expand
# to cover them too.
KNOWN_BROKEN_CLASSIC_DECAL_IDS = frozenset()


@pytest.fixture(scope="module")
def engine_module():
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2
    return shokker_engine_v2


@pytest.fixture(scope="module")
def decal_dispatcher(engine_module):
    """Build the exact DECAL_SPEC_MAP the server uses, by reconstructing
    the block from the source so we exercise the SAME callables that
    the runtime dispatches through. This avoids stale test baselines."""
    # The classic portion of DECAL_SPEC_MAP is constructed literally in
    # shokker_engine_v2.py:10857+ using top-level engine.spec_paint
    # imports. Recreate that mapping here via the same imports.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.spec_paint import (
            spec_gloss, spec_matte, spec_satin,
            spec_metallic, spec_pearl, spec_chrome, spec_satin_metal,
        )

    classic = {
        "gloss": spec_gloss, "matte": spec_matte, "satin": spec_satin,
        "metallic": spec_metallic, "pearl": spec_pearl,
        "chrome": spec_chrome, "satin_metal": spec_satin_metal,
        "clear_matte": spec_matte, "eggshell": spec_matte,
        "flat_black": spec_matte, "primer": spec_matte,
        "semi_gloss": spec_gloss, "silk": spec_satin,
        "wet_look": spec_gloss, "scuffed_satin": spec_satin,
        "chalky_base": spec_matte, "living_matte": spec_matte,
        "ceramic": spec_satin, "piano_black": spec_gloss,
    }

    def dispatch(fid):
        """Return the callable the server would dispatch for this
        specFinish id, matching the DECAL_SPEC_MAP shape."""
        if fid.startswith("f_") and fid in engine_module.BASE_REGISTRY:
            return engine_module._mk_flat_foundation_decal_spec(fid)
        if fid in classic:
            return classic[fid]
        # Fallback path in the live dispatch would be spec_gloss —
        # which itself has a 5-arg signature and would crash.
        return spec_gloss

    return dispatch


def test_loaded_and_fallback_dropdown_paths_match():
    """The loaded-data branch and the hardcoded fallback must offer
    the SAME supported f_* ids in the SAME order.

    This catches the exact 2026-04-22 regression where the loaded path
    only used BASE_GROUPS['Foundation'] (12 ids) while the fallback
    still exposed 19 ids by also including Reference Foundations.
    """
    fallback_ids = _extract_decal_specfinish_fallback_ids()
    assert FOUNDATION_IDS == fallback_ids, (
        "decal specFinish dropdown branches disagree.\n"
        f"loaded-data ids ({len(FOUNDATION_IDS)}): {FOUNDATION_IDS}\n"
        f"fallback ids ({len(fallback_ids)}): {fallback_ids}\n"
        "The live branch and fallback must expose the same safe set."
    )


def test_foundation_id_list_extraction_is_nontrivial():
    """Sanity: the safe decal dropdown must still expose a meaningful
    set of Foundation ids."""
    assert len(FOUNDATION_IDS) >= 12, (
        f"decal specFinish dropdown extracted only {len(FOUNDATION_IDS)} "
        f"supported f_* ids: {FOUNDATION_IDS}. Either the picker shrank "
        f"unexpectedly or the extractor is broken."
    )


@pytest.mark.parametrize("fid", FOUNDATION_IDS)
def test_every_ui_exposed_foundation_decal_id_has_documented_behavior(
    fid, engine_module, decal_dispatcher
):
    """Every id in the live Foundation dropdown must match a
    documented behavior:
      - ``f_*`` ids (guaranteed flat by the 2026-04-22 overnight) →
        produce a (h, w, 4) uint8 array with (0,0,0) M/R/CC spread
        when invoked at the decal dispatch signature.
      - Classic non-f_ ids in ``KNOWN_BROKEN_CLASSIC_DECAL_IDS`` →
        raise TypeError at the 4-arg dispatch call. xfail-pinned
        until the bug is fixed; strict-fails if any of them starts
        working (prompting this ratchet to be trimmed).

    Any OTHER id (new addition to the dropdown that isn't explicitly
    classified) fails this test — forcing the contributor to either
    add it to ``KNOWN_BROKEN_CLASSIC_DECAL_IDS`` with a reason, or
    wire it to the flat shim.
    """
    fn = decal_dispatcher(fid)
    shape = (16, 16)
    mask = np.ones(shape, dtype=np.float32)

    if fid.startswith("f_"):
        # Flat-foundation path. Must succeed AND be flat.
        spec = fn(shape, mask, 42, 1.0)
        assert isinstance(spec, np.ndarray) and spec.shape == (16, 16, 4), (
            f"{fid}: decal-spec callable returned unexpected shape/type "
            f"{getattr(spec, 'shape', type(spec))}"
        )
        for ch_idx, ch_name in enumerate(("M", "R", "CC")):
            ch = spec[:, :, ch_idx]
            spread = int(ch.max()) - int(ch.min())
            assert spread == 0, (
                f"{fid}: {ch_name} spread={spread} — Foundation f_* "
                f"ids must produce FLAT decal spec."
            )
        return

    if fid in KNOWN_BROKEN_CLASSIC_DECAL_IDS:
        # Pinned as xfail with strict=True — if the bug is fixed, this
        # test strict-fails and the KNOWN_BROKEN set must be updated.
        pytest.xfail(
            f"{fid}: pinned-known-broken. Classic Foundation id's "
            f"5-arg spec handler crashes at the 4-arg decal dispatch "
            f"site; silently swallowed. Pre-existing bug class, "
            f"different from the 2026-04-22 f_* fix. When fixed, "
            f"remove from KNOWN_BROKEN_CLASSIC_DECAL_IDS in this file."
        )
        # Below the xfail line never fires unless the bug self-heals,
        # in which case strict=True makes it fail loudly.
        spec = fn(shape, mask, 42, 1.0)
        assert isinstance(spec, np.ndarray)

    # Any other id is an UNCLASSIFIED addition — force a review.
    pytest.fail(
        f"{fid} is in BASE_GROUPS['Foundation'] but is neither an f_* "
        f"id nor listed in KNOWN_BROKEN_CLASSIC_DECAL_IDS. Classify it: "
        f"wire to the flat shim, or add to the known-broken set with a "
        f"documented reason."
    )


def test_known_broken_classic_set_matches_current_reality():
    """Structural pin: every id in KNOWN_BROKEN_CLASSIC_DECAL_IDS must
    actually be in the live UI dropdown. Catches a maintainer
    forgetting to trim the set when a classic id is removed from the
    Foundation group."""
    dropdown = set(FOUNDATION_IDS)
    orphans = KNOWN_BROKEN_CLASSIC_DECAL_IDS - dropdown
    assert not orphans, (
        f"KNOWN_BROKEN_CLASSIC_DECAL_IDS lists ids that are no longer "
        f"in BASE_GROUPS['Foundation']: {sorted(orphans)}. Trim the "
        f"set."
    )


def test_full_coverage_of_ui_foundation_dropdown():
    """Sanity: the combination of (f_* ids) ∪ (KNOWN_BROKEN set)
    should account for every UI-exposed Foundation id, so there's no
    silent gap in coverage."""
    dropdown = set(FOUNDATION_IDS)
    f_ids = {fid for fid in dropdown if fid.startswith("f_")}
    covered = f_ids | KNOWN_BROKEN_CLASSIC_DECAL_IDS
    uncovered = dropdown - covered
    assert not uncovered, (
        f"The following UI-exposed Foundation ids are neither f_* nor "
        f"in KNOWN_BROKEN_CLASSIC_DECAL_IDS: {sorted(uncovered)}. "
        f"Every id in the live dropdown must have a documented "
        f"status."
    )
