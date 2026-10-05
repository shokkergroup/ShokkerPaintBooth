"""Regression guardrail: source_layer_mask must be applied BEFORE
claimed-pixel subtraction in the zone-mask build loop.

## Why this matters

In `shokker_engine_v2.py` (around line 9594-9608), the first-pass zone
mask builder runs in priority order, accumulating a global `claimed`
mask as each zone grabs its pixels. For a LAYER-RESTRICTED zone (one
with a `source_layer_mask`) the order of two operations matters:

    A) mask = mask * source_layer_mask        # restrict to zone's layer
    B) mask = mask - claimed * 0.8            # subtract already-claimed

If the engine does A before B (the CORRECT order):
  - Zone keeps only pixels on its authored layer.
  - Then subtracts pixels a higher-priority zone already grabbed.
  - Result: zone owns the intersection of its layer AND unclaimed area.

If the engine does B before A (the WRONG order):
  - Zone subtracts claimed pixels even where `claimed` holds pixels
    from a totally different layer.
  - A high-priority zone on layer X can strip pixels off a low-priority
    zone on layer Y that happen to share a color — even though they're
    on different layers and shouldn't interact.
  - Result: layer restriction leaks; cross-layer claim theft.

The authorial comment at line 9594 explicitly documents the intent.
This test pins that source-code order so a future refactor can't
silently swap it.

## How it tests

Reads the source file and finds the two operation sites by regex.
Asserts the `mask * _source_layer_mask` assignment appears at a lower
line number than the `mask - claimed` subtraction inside the same zone
iteration.

This is a SOURCE-CODE-LEVEL test, not a behavioural one, because the
full pipeline is expensive to exercise and the invariant we care about
is structural: "don't invert these two lines by accident."
"""

import re
from pathlib import Path


def test_layer_mask_applied_before_claimed_subtraction():
    """shokker_engine_v2.py must apply `mask * _source_layer_mask`
    strictly before `mask - claimed * 0.8` inside the zone builder."""
    src_path = Path(__file__).resolve().parent.parent / "shokker_engine_v2.py"
    src = src_path.read_text(encoding="utf-8")

    # Find the layer-mask application line
    layer_mask_pat = re.compile(
        r"mask\s*=\s*\(?\s*mask\s*\*\s*_source_layer_mask\s*\)?"
    )
    # Find the claimed-subtraction line
    claimed_pat = re.compile(
        r"mask\s*=\s*np\.clip\s*\(\s*mask\s*-\s*claimed\s*\*\s*0\.8"
    )

    layer_match = layer_mask_pat.search(src)
    assert layer_match is not None, (
        "shokker_engine_v2.py no longer contains a line like "
        "`mask = (mask * _source_layer_mask)...`. The layer-mask "
        "application has been removed or renamed. This regression "
        "test needs to be updated to match the new code — confirm "
        "the new dispatch still applies layer mask before claim "
        "subtraction."
    )
    # The file contains MULTIPLE `mask = np.clip(mask - claimed * 0.8)`
    # lines (the region_mask short-circuit earlier in the same function
    # plus the color-selector main path AFTER our layer-mask apply). The
    # invariant is specifically about the claim-subtraction that comes
    # AFTER the layer-mask apply in source order — i.e. the one in the
    # same code path. Use finditer and pick the first match whose offset
    # is greater than layer_match.end().
    next_claimed = None
    for m in claimed_pat.finditer(src):
        if m.start() > layer_match.end():
            next_claimed = m
            break
    assert next_claimed is not None, (
        "shokker_engine_v2.py no longer has a `mask = np.clip(mask - "
        "claimed * 0.8, ...)` line AFTER the layer-mask apply. The "
        "claim-subtraction may have been removed or reorganized; "
        "update this test after confirming the invariant still holds."
    )
    # The layer-mask apply is at `layer_match.start()`; the immediately-
    # following claim-subtraction is at `next_claimed.start()`. The
    # layer apply must precede it (that's how finditer picked it), so
    # an inversion would manifest as NO claim-subtraction found after
    # the layer apply — i.e. next_claimed would be None, which is the
    # assert above. For good measure, also confirm the line-number gap
    # is reasonable (< 30 lines) so we know they're in the same block.
    layer_line = src[:layer_match.start()].count("\n") + 1
    claim_line = src[:next_claimed.start()].count("\n") + 1
    assert 0 < (claim_line - layer_line) < 30, (
        f"Layer-mask apply at line {layer_line} and next claim-subtract "
        f"at line {claim_line} are more than 30 lines apart. The two "
        f"operations may have been separated into different code paths; "
        f"the ordering invariant is no longer trivially checkable. "
        f"Review the zone-mask builder manually."
    )


def test_layer_mask_ordering_comment_still_present():
    """The authorial comment explaining the ordering invariant must
    still be in place. If someone removes the comment, the next dev
    may inadvertently invert the order during a refactor.
    """
    src_path = Path(__file__).resolve().parent.parent / "shokker_engine_v2.py"
    src = src_path.read_text(encoding="utf-8")
    # Match the key phrase from the comment — specifically the part that
    # names the invariant (INSIDE the chosen source layer before ... claimed).
    phrase = "INSIDE the chosen"
    # Secondary phrase
    phrase2 = "before higher-priority zones subtract claimed"
    assert phrase in src, (
        f"Authorial comment phrase `{phrase}` removed from shokker_engine_v2.py. "
        f"This comment documents why layer-mask must be applied before "
        f"claimed-pixel subtraction. Restore it or update this test."
    )
    assert phrase2 in src, (
        f"Authorial comment phrase `{phrase2}` removed from shokker_engine_v2.py. "
        f"Restore it or update this test."
    )
