# Overnight Work Queue — Pick next uncompleted task, execute, mark done
# Target: 10% better EVERY HOUR. Be legendary.

## HOUR 1 (In Progress)
- [x] Phase 1: spec_paint.py legacy audit (5800 lines) — 18 fixes
- [x] Phase 2: Shokk Series complete marriage — 7 fixes
- [ ] Phase 3: Performance sweep all engine files (agent running)
- [ ] Phase 4: Fusion factory quality pass 150 finishes (agent running)

## HOUR 2: Deep Pattern Quality
- [ ] Audit ALL spec overlay patterns in engine/spec_patterns.py — check each pattern produces VISUALLY DISTINCT output, not just noise. Rate A/B/C/D. Fix any C/D patterns to be genuinely unique and interesting.
- [ ] Audit engine/pattern_expansion.py — same treatment. Find lazy/duplicate patterns and make them unique.
- [ ] Check every pattern has proper M_range and R_range values (not 0, not insanely high)

## HOUR 3: Paint Function Excellence
- [ ] Go through EVERY paint_v2/*.py file. For each paint function: does it produce a VISIBLE effect at pm=1.0? Boost any function where the effect is too subtle (pm multiplied by tiny numbers).
- [ ] Check all bounce boost (bb) values — are they appropriate for the material? Chrome should be high (0.3-0.6), matte should be low (0.05-0.1), candy/pearl in between.
- [ ] Ensure every paint function has proper docstring explaining what it does physically.

## HOUR 4: Registry & Data Integrity
- [ ] Audit engine/base_registry_data.py — check EVERY base entry has sensible M/R/CC values for its material type. A chrome base should have M>240. A matte should have M<20 and R>150. Fix any that don't match their material.
- [ ] Check for duplicate IDs anywhere in BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY
- [ ] Verify all registry patch files (engine/registry_patches/*.py) actually wire to existing functions

## HOUR 5: Error Resilience
- [ ] Add try/except safety wrappers around EVERY paint_fn and spec_fn call in compose.py and shokker_engine_v2.py so a single broken finish doesn't crash the entire render
- [ ] Add timing instrumentation to build_multi_zone — log per-zone render time so slow finishes can be identified
- [ ] Improve error messages throughout — when a render fails, the user should know WHICH finish and WHICH zone caused it

## HOUR 6: Final Polish
- [ ] Full 3-copy sync verification — MD5 check every .py and .js file across all 3 locations
- [ ] Write comprehensive OVERNIGHT_REPORT.md with: total fixes, total improvements, files changed, what to test
- [ ] Stage everything with git add (but do NOT commit)
- [ ] Clean up any temp files, __pycache__ dirs, .pyc files

## BONUS (if time permits)
- [ ] Improve multi_scale_noise in core.py — add optional cache so same seed+scale combo returns cached result
- [ ] Add a _render_time_budget system — if a zone takes >10s in preview, automatically reduce quality
- [ ] Audit the COLORSHOXX finishes for visual quality — are the 25 color-shift finishes actually producing visible dual-tone effects?
