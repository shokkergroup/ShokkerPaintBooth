# Spec Pattern Cookbook

This is the step-by-step recipe for adding a new **spec pattern** to SPB. A spec
pattern is a grayscale texture that modulates one channel of the four-channel
spec map (metallic, roughness, clearcoat, or alpha) — it is what gives a paint
finish visible structure like brushed-metal directionality, carbon weave, or
micro-flake. Adding a new one is the best first-contribution task in the
codebase: it touches the Python engine, the JS catalogue, and the UI picker, and
it teaches you the three-copy sync dance without requiring architectural changes.

If you have not read `docs/ONBOARDING.md` and `docs/STYLE_GUIDE.md`, do that
first. Budget about 3 hours for your first pattern end-to-end; subsequent ones
take 30 minutes.

## Step 1 — Pick a category

Spec patterns are grouped into categories that appear as tabs in the picker UI:

- **Metallic textures** — flake, brushed, anodised swirl, chrome crackle
- **Weave & fabric** — carbon, kevlar, fibreglass, linen
- **Liquid & organic** — orange-peel, marble, cellular, fluid dynamics
- **Geometric** — pinstripe, halftone, grid, hex, voronoi
- **Damage & wear** — scratch, rust spot, paint chip, UV fade
- **Effects** — noise, sparkle, dust, fingerprint

Pick a category that already has siblings — your pattern should feel at home
next to the others. If you think the category is wrong for what you're adding,
raise it on an issue first; don't invent a new category without discussion.

## Step 2 — Write the Python function

Spec patterns live in `electron-app/server/engine/spec_patterns.py` (or a
specialised module under `engine/expansions/`). Pick a location that matches the
category. Add your function below the existing patterns in that category, sorted
by complexity (simplest first).

Open the file and search for the comment banner `# --- SPEC PATTERN CATALOG ---`
to find the right neighbourhood.

## Step 3 — Signature convention

Every spec pattern function has this exact signature:

    def texture_<name>(shape: tuple[int, int],
                      seed: int,
                      sm: float = 1.0,
                      **params) -> NDArray[np.float32]:
        """One-line summary.

        Args:
            shape: (H, W) output dimensions in pixels.
            seed: Deterministic RNG seed; same seed -> same output.
            sm:   "Scale modifier" in [0.1, 10]. 1.0 = default size,
                  2.0 = pattern features 2x larger, 0.5 = half-size.
            **params: Pattern-specific knobs (document below).

        Returns:
            (H, W) float32 array in [0.0, 1.0]. 0 = darkest, 1 = brightest.
        """

- `shape` is `(height, width)` — match numpy convention, not PIL.
- `seed` must be respected: given the same `shape, seed, sm, **params`, your
  function must return the exact same pixels. Use `np.random.default_rng(seed)`;
  never `np.random.seed` (globals bite).
- `sm` scales feature size (not amplitude). A brushed pattern with `sm=2.0` has
  streaks twice as long.
- `**params` should be a small set (≤5) of knobs the user can tweak in the UI.
  Document every one below the function.

## Step 4 — Return float32 (h, w) in [0, 1]

Not uint8, not float64. The compositor in `compose.py` expects float32
single-channel in `[0, 1]`; anything else triggers a clamp + warn. Use
`np.clip(result, 0.0, 1.0).astype(np.float32, copy=False)` at the end if you're
unsure.

Do not pre-multiply channels, do not apply gamma, do not add alpha — the
compositor handles all of that. Your one job is: produce a grayscale texture.

## Step 5 — Use `_validate_spec_output()`

At the end of your function, call the validator:

    from engine.spec_patterns import _validate_spec_output
    return _validate_spec_output(result, name="texture_mypattern")

This checks dtype, shape, range, NaN/Inf, and contiguity. It is a no-op in
release builds (guarded by `SPB_DEV` env var) so there is no production cost.
Forgetting this is the single most common cause of "my pattern renders black"
bug reports.

## Step 6 — Register in `PATTERN_CATALOG`

At the bottom of `spec_patterns.py`, there is a `PATTERN_CATALOG` dict. Add your
entry:

    "my_pattern_id": {
        "fn": texture_my_pattern,
        "category": "metallic_textures",  # or weave_fabric, etc.
        "label": "My Pattern",
        "default_sm": 1.0,
        "default_strength": 0.8,
        "default_channel": "roughness",    # which spec channel it modulates
        "params": {
            "grain": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
            "direction": {"type": "int", "default": 0, "min": 0, "max": 360},
        },
    },

`my_pattern_id` becomes the string the UI sends back to the engine. Use
`snake_case`, prefix with the category if ambiguous (`metallic_flake_fine`).

**Now sync.** Three Python copies of this file exist; run:

    node scripts/sync-runtime-copies.js --write

## Step 7 — Add JS catalogue entry

Open `paint-booth-0-finish-data.js` and find `SPEC_PATTERNS` (note: separate from
`PATTERNS`). Add:

    { id: 'my_pattern_id', label: 'My Pattern', category: 'metallic_textures',
      thumb: 'thumbs/spec/my_pattern_id.png', new: true },

Then in `SPEC_PATTERN_GROUPS` put the id into its category group so the picker
tab shows it. Un-grouped ids are **dropped from the picker at boot**; this is
the most common "I added it but it doesn't appear" failure.

Add a thumbnail at `electron-app/assets/thumbs/spec/my_pattern_id.png` — 128×128
PNG, rendered at default parameters. If you don't have one yet, reuse a sibling
thumbnail and mark the TODO in the PR.

Sync again (three JS copies):

    node scripts/sync-runtime-copies.js --write

## Step 8 — Test at 256×256 AND 2048×2048

Write a test under `tests/spec_patterns/test_my_pattern.py`:

    import numpy as np
    from engine.spec_patterns import texture_my_pattern

    def test_my_pattern_deterministic_at_256():
        a = texture_my_pattern((256, 256), seed=42)
        b = texture_my_pattern((256, 256), seed=42)
        np.testing.assert_array_equal(a, b)

    def test_my_pattern_scales_cleanly_to_2048():
        small = texture_my_pattern((256, 256), seed=1)
        large = texture_my_pattern((2048, 2048), seed=1)
        assert small.shape == (256, 256)
        assert large.shape == (2048, 2048)
        # feature-count invariance: grain density should stay within 30%
        assert abs(small.mean() - large.mean()) < 0.05

Shape edge cases (non-square, very small `(16, 16)`, large `(4096, 4096)`) are
worth covering too. Add a golden-image comparison if the pattern is ever
user-visible at default parameters.

## Step 9 — Benchmark (under 500 ms for 2048×2048)

Add a benchmark to `tests/benchmarks/`:

    import time, numpy as np
    from engine.spec_patterns import texture_my_pattern

    def test_perf_my_pattern_2048():
        t0 = time.perf_counter()
        _ = texture_my_pattern((2048, 2048), seed=0)
        dt = time.perf_counter() - t0
        assert dt < 0.5, f"Too slow: {dt*1000:.0f} ms"

If you blow the 500 ms budget, prime suspects: pure-Python loops over pixels
(use vectorised numpy), `scipy.ndimage` at wrong dtype (cast to `float32`
upfront), or repeated RNG allocation in a loop (create one `rng` and reuse).

If the pattern is fundamentally expensive (voronoi cells, fluid simulation),
consider caching: return from a persistent LRU keyed on `(shape, seed, params)`.
See `_cached_voronoi` for the pattern.

## Step 10 — Document the parameters

In the function docstring, below `Args`, add a `Parameters` section that
describes every `**params` knob the user can set:

    Parameters:
        grain (float, 0..1, default 0.5): Density of flake points; higher =
            more visible flakes.
        direction (int, 0..360, default 0): Rotation of the grain axis in
            degrees; 0 = horizontal, 90 = vertical.

This text is scraped into the in-app parameter tooltip at build time, so keep it
concise (one line per param).

## Common pitfalls

- **Returning uint8 in 0..255.** Guaranteed-black output. Use float32 0..1.
- **Forgetting to seed the RNG.** Each render produces a different pattern,
  breaking preview caching and annoying users.
- **Using `time.time()` inside the function.** Never; the function must be
  pure. All entropy flows through `seed`.
- **Unvalidated `sm`.** Users can send `sm=0.0` which divides by zero. Clamp to
  `max(0.01, sm)` before using.
- **Large feature sizes that wrap the image.** If your pattern tiles, handle
  tile boundaries explicitly; see `_seamless_wrap` helper.
- **Ignoring `shape[0] != shape[1]`.** Test at 512×2048 — aspect-ratio bugs
  love to hide there.
- **Thumbnail mismatch.** The thumb is baked at default params; if a user
  tweaks params and the preview looks nothing like the thumb, add a note in the
  UI ("thumb shows default").
- **Editing the wrong copy.** Always edit the root copy; sync propagates.

## Template function with annotations

    # =========================================================================
    # texture_my_pattern — replace `my_pattern` with a descriptive name
    # category: metallic_textures | weave_fabric | liquid_organic | geometric |
    #           damage_wear | effects
    # =========================================================================
    def texture_my_pattern(
        shape: tuple[int, int],
        seed: int,
        sm: float = 1.0,
        *,
        grain: float = 0.5,
        direction: float = 0.0,
    ) -> np.ndarray:
        """Short one-line description of what this looks like.

        Args:
            shape: (H, W) output dimensions.
            seed: Deterministic RNG seed.
            sm: Feature scale multiplier; clamp to [0.01, 10].

        Parameters:
            grain (float, 0..1): Flake density; 0 = smooth, 1 = maximum grain.
            direction (float, 0..360): Rotation in degrees of the dominant axis.

        Returns:
            (H, W) float32 in [0, 1].
        """
        import numpy as np
        from .spec_patterns import _validate_spec_output

        H, W = shape
        sm = max(0.01, float(sm))
        rng = np.random.default_rng(seed)

        # --- your algorithm here ---
        # Example: isotropic noise as a placeholder
        result = rng.random(size=(H, W), dtype=np.float32)
        result = np.clip(result, 0.0, 1.0)

        return _validate_spec_output(result, name="texture_my_pattern")

## How to debug

- **Isolate.** Call the function directly from a Python REPL with a known seed
  and small shape, save the result via `PIL.Image.fromarray((r*255).astype(np.uint8))`,
  and open the PNG. That eliminates the compositor and UI as variables.
- **Trace through the compositor.** Set `SPB_DEV=1` and watch the console:
  `_engine_rot_debug()` logs every pattern invocation with its parameters.
- **Render at multiple seeds.** If your pattern looks identical across seeds,
  you forgot to thread `seed` through to the RNG. If it flickers between
  renders at the same seed, you have a hidden global random source.
- **Check the validator output.** If the validator logs a warning
  (non-contiguous, out-of-range), fix it; the compositor does silent clamps
  that hide bugs.
- **Use the pattern previewer.** `python -m engine.tools.pattern_preview
  my_pattern_id --sm 1.5 --seed 7` opens a grid of nine variants side-by-side.

## How to add variants

Several base patterns ship in "fine / medium / coarse" sets. The convention is
three separate catalogue entries sharing a suffix:

    texture_flake_fine    -> default_sm=0.5
    texture_flake_medium  -> default_sm=1.0
    texture_flake_coarse  -> default_sm=2.0

Implement once, then register three catalogue entries differing only in
`default_sm`. If variants need qualitatively different parameters (e.g. hex vs
honeycomb vs offset-hex), they are separate functions, not variants.

Done? Run tests, sync copies, open a PR. Your pattern will show up in the
picker on the next app launch. Welcome to the spec overlay club.
