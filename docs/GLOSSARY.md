# SPB Glossary

Definitions for terms that appear in the Shokker Paint Booth code, docs, and UI. If you hear a word in `#spb-dev` or see it in a commit message and aren't sure, it probably belongs here.

Terms are grouped by area. Within each group they're alphabetical.

---

## Paint & Finish Model

**Base.** The underlying color layer for a zone before any pattern, finish, or spec overlay is applied. Every painted zone has exactly one base. Examples: `Gloss Black`, `Candy Apple Red`, `Metallic Silver`.

**Base Group.** A named bucket of bases in the UI picker. Defined in `BASE_GROUPS` in `paint-booth-0-finish-data.js`. Purely organizational — changes nothing about rendering.

**Candy.** A transparent colored layer over a reflective base. Candies rely on the base to kick light back out through the candy coat, which is why they look different over silver than over black.

**Clearcoat.** A glossy transparent layer on top of everything. In SPB it's encoded in the B channel of the spec map, with an **inverted** scale: 0 to 15 means no clearcoat, 16 is maximum gloss, and values toward 255 mean duller clearcoat. This is unintuitive; expect to re-learn it every time you come back to the spec system.

**Finish.** The rendering recipe for a surface. A finish combines a base, optional pattern, optional spec overlay, and a paint function that knows how to actually blit pixels. `FINISH_REGISTRY` in `engine/base_registry_data.py` is the source of truth.

**Finish Mixer.** A 6.1.1 feature that lets a zone interpolate between multiple finishes by weight. Useful for fading one candy into another.

**Iron Rules.** A set of hard constraints that prevent impossible paint combinations (for example: forbidding a reflective spec overlay over a matte base where it would look wrong). Live in the UI as "you can't do that" guardrails; the name comes from the fact they're not optional.

**Live Link.** Real-time bridge between SPB and an external renderer target. Today it's one-way (SPB pushes to the target). Multiplayer Live Link is on the 7.0 roadmap.

**Monolithic.** A finish that treats the entire body as one continuous surface rather than a tiled pattern. `ARSENAL_24K`, `PARADIGM`, and several others are monolithic. Implemented under `engine/expansions/`.

**Pattern.** A repeating texture applied over the base (carbon fiber weave, flake, animal print, etc.). Patterns live in three related registries: `PATTERNS` (display names in JS), `PATTERN_GROUPS` (picker organization in JS), and `PATTERN_REGISTRY` (actual render functions in Python). If any of those three is missing an entry, the pattern misbehaves in a specific, diagnosable way.

**Pattern Strength.** A per-zone control for how heavily a pattern overlays its base. 0 means no pattern; 100 means full. Introduced in 6.1.1.

**Shokk.** A saved SPB project — the combination of zones, bases, finishes, spec settings, and region masks that together describe one paint job. "Shokks" is the plural. The file format is internal and versioned.

**Spec Map.** An RGBA image where each channel encodes a material property:

- **R = Metallic** (0 = dielectric, 255 = fully metallic)
- **G = Roughness** (0 = mirror, 255 = matte)
- **B = Clearcoat** (inverted: 0 to 15 = none, 16 = max gloss, 255 = dull)
- **A = Specular Mask** (reserved; no consumer tool uses it yet)

**Spec Overlay / Spec Pattern.** A repeating spec-map pattern applied independently of the color pattern. Enables, for example, brushed-metal directionality on top of a solid-color base. Lives in `engine/spec_patterns.py` with its own `SPEC_PATTERNS` JS registry and `SPEC_PATTERN_GROUPS` organizer.

**Zone.** A region of the car body that holds a single finish. Zones are disjoint — a pixel belongs to exactly one zone. Stored as RLE (run-length encoded) region masks in `paint-booth-3-canvas.js`.

---

## Architecture

**Electron App.** The desktop shell under `electron-app/`. Wraps the frontend HTML/JS and launches the bundled Python server.

**Engine.** The Python rendering code, rooted at `shokker_engine_v2.py` and the `engine/` package. This is where paint physics lives.

**Finish Registry.** `FINISH_REGISTRY` dictionary in `base_registry_data.py`. Maps finish IDs to the paint and spec functions that draw them. The single most important data structure in the project.

**GPU Pipeline.** The GPU-accelerated path in `engine/gpu.py`. Fallbacks to CPU when no GPU is available. CPU is slow but correct; GPU is fast but occasionally quirky on unusual drivers.

**Pattern Registry.** Python-side `PATTERN_REGISTRY` in `engine/patterns.py`. If a pattern ID isn't here, the renderer silently draws nothing for it. This is the #1 cause of "the picker shows my pattern but it doesn't render" bugs.

**pyserver.** The bundled Python interpreter that ships inside the installer under `electron-app/server/pyserver/_internal/`. Lets us run Python on a customer's machine without asking them to install Python.

**Render Preview.** The low-res render the UI shows while you're tweaking. Currently driven by a polling loop against the Python server. 6.3.1 plans to replace the polling with SSE.

**Server.** `server.py` — Flask API server that sits between Electron frontend and the engine. About 4,500 lines; contains routing, queuing, and some business logic that should probably move but hasn't yet.

---

## Workflow & Process

**Alpha / Beta / Public.** Release stages. Alpha: internal testers, rough edges, data formats may shift with warning. Beta: wider testers, UI frozen, data formats locked. Public: paying customers, quality bar at shipping level.

**Boil the Ocean.** Codename for release 6.2.0 — the big catalog and engine upgrade cycle. Named after the saying "don't try to boil the ocean," which is exactly what this release does on purpose.

**Codename.** Each minor release has a name. Used internally and in announcements to make versions memorable.

**Gold-to-Platinum.** The current long-running rework track this repo represents. "Gold" was the last stable major family before the rewrite; "Platinum" is what we're becoming.

**Golden Image.** A reference render for a finish, stored in `tests/golden/`, used for regression testing. If a change shifts a golden image, the test fails and a human reviews the diff.

**Heartbeat.** Session summary written by a dev or QA agent and stored in `memory/heartbeats_history.md`. Captures what happened in a given block of work.

**Release Captain.** The person running a given release. Owns the `LAUNCH_CHECKLIST.md` walkthrough, makes the go/no-go call, owns rollback if things break.

**Three-Copy Sync.** The discipline of keeping the root, `electron-app/server/`, and `electron-app/server/pyserver/_internal/` copies of shared files in lockstep. See `CONVENTIONS.md`.

**Moat.** The product attributes we believe are uniquely SPB and shouldn't be given up. Current list: pattern-per-channel control, real-time car-shape preview, zone-level spec settings. See `MEMORY.md`.

---

## Testing & QA

**Smoke Test.** Minimum set of clicks that proves the build runs at all. See `WINDOWS_SANDBOX_TEST_GUIDE.md` for the current list.

**Regression.** A bug where a previously working behavior breaks. Regressions are the worst kind of bug and the highest-priority class of fix.

**Sandbox.** Windows Sandbox — a throwaway VM used for clean-machine install testing. `WINDOWS_SANDBOX_TEST_GUIDE.md` is the full guide.

**WARN-GGX-NNN.** A naming convention for a family of engine warnings around the GGX specular model. 001 through 006 were fixed in 6.2.0.

---

*If you add a term here, link it from its first appearance in the code or docs.*
