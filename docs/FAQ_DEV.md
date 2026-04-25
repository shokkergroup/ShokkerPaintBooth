# Developer FAQ

Answers to the questions new contributors actually ask. User-facing questions live in `SPB_FAQ.md` in the repo root.

---

## Q: Why does the project have 3 copies of some files?

**Short answer:** because the build pipeline is honest about where each copy is used, instead of pretending a symlink will work.

**Long answer:** SPB ships as an Electron app with a bundled Python interpreter. At runtime, the Python side is loaded from `electron-app/server/pyserver/_internal/`. At **dev** time, we run the server from `electron-app/server/` so we can iterate without repackaging. And at repo-root level we keep the canonical version that's easy to hand-edit, search, and diff.

Each copy serves a purpose:

| Copy | Consumed by |
|------|-------------|
| Repo root | Developers, tooling, scripts |
| `electron-app/server/` | `npm run dev` |
| `electron-app/server/pyserver/_internal/` | Packaged installer |

We've considered collapsing with symlinks (fails on some Windows configs), with build-time copy (makes dev iteration slower), and with a single source directory imported from all three (makes packaging more complex). The current arrangement is the least-bad compromise.

The discipline: **when you edit one, sync all three.** See `docs/CONVENTIONS.md` section 2.

---

## Q: Why is `server.py` so huge?

`server.py` is ~4,500 lines and yes, that is too many. It grew during the Gold-to-Platinum rewrite when we needed to bolt new API routes onto a working system faster than we could refactor. A chunk of it is endpoint definitions (OK), another chunk is parameter coercion and validation (should probably move to a helpers module), and a smaller-but-growing chunk is business logic that arguably belongs in the engine package.

**Is it getting smaller?** Slowly. We don't do big-bang refactors on shipping code. When you touch a route, if you can move its helpers into a module under `engine/` or `server_utils/` without changing behavior, do it and file a small PR. Don't block a feature on cleanup.

**Will we split it?** Yes, at 7.0 when the plugin architecture lands. Plugin routes need a more disciplined structure anyway, so we'll take that opportunity.

---

## Q: How do I add a new finish?

High-level sequence:

1. **Design the recipe.** What's the base? What paint function renders it? What spec map? If a pattern, which pattern?
2. **Implement the paint function** in the appropriate `engine/paint_v2/*.py` file (or a new one if it's a whole new family).
3. **Add the entry to `FINISH_REGISTRY`** in all three copies of `engine/base_registry_data.py`.
4. **Add it to the UI picker** via `paint-booth-0-finish-data.js` (three copies): add to `BASES` or the right finish array, then to the relevant `*_GROUPS`.
5. **Add a golden-image test** under `tests/golden/<finish_id>.png`.
6. **Smoke it in dev**, then smoke it in a packaged build from Sandbox.
7. Commit touching all three copies in a single commit. The PR description should say what family, what inspired it, and what looks different from the nearest existing finish.

Common pitfalls: forgetting the `_internal` copy (finish works in dev, missing in installer) and forgetting the group entry (finish renders but doesn't appear in the picker).

---

## Q: How do I add a new pattern?

Patterns have their own three-registry dance:

1. `PATTERNS` — display metadata in JS (all three copies).
2. `PATTERN_GROUPS` — picker organization in JS (all three copies). Un-grouped IDs are dropped at boot.
3. `PATTERN_REGISTRY` — render function in Python (all three copies). Missing IDs render nothing, silently.
4. Implement the texture function with signature `def texture_NAME(shape, mask, seed, sm):`.

See `TROUBLESHOOTING_DEV.md` section 1 for the specific symptoms if you miss one.

---

## Q: Why three pattern registries?

Historical. The JS side wanted display info (label, swatch) separate from selection info (which picker tab). The Python side needs the actual render function. Splitting `PATTERNS` and `PATTERN_GROUPS` made the picker UI work cleaner, but nobody's gone back to unify them. 6.3.0 targets a unified finish picker that will eat this complexity.

---

## Q: What is the spec map, really?

An RGBA texture where each channel means something different to the renderer. See `docs/GLOSSARY.md` entry for "Spec Map" and `docs/CHEATSHEET.md` for the quick preset table.

The part that trips people up: the **B channel's scale is inverted**. 0-15 means no clearcoat, 16 is max gloss, and values approaching 255 mean duller. If chrome looks matte, you set B wrong.

---

## Q: Why don't we use a framework on the frontend?

The three `paint-booth-*.js` files are plain vanilla JS with manual DOM manipulation. This is deliberate:

- No build step for the frontend keeps the dev loop fast.
- No framework means no breaking-change treadmill.
- The app's interaction model is dominated by a render preview and a small number of panels. A framework's trade-offs don't pay for themselves here.

We'll revisit if the panel count or interaction complexity grows. Not a 6.3.x or 7.0 concern.

---

## Q: What's the deal with `shokker_engine_v2.py` being 8,000+ lines?

Same story as `server.py`. Big, grew organically, hard to justify a rewrite on a shipping engine. A few rules we follow:

- New engine code goes into `engine/` submodules unless it's unambiguously editing existing behavior in `v2`.
- Don't introduce classes into the hot path in `v2`. Functions + dataclasses.
- The `_engine_rot_debug()` hook at ~line 84 is permanent — don't remove it, it's how we dump engine state when customers send us logs.

---

## Q: Where does "Boil the Ocean" come from?

It's the codename for 6.2.0. The phrase usually means "don't try to do everything at once." We used it ironically because that's exactly what 6.2.0 did — catalog expansion, engine overhaul, new finish categories, quality audit, performance pass, all in one release. Next cycle is intentionally narrower.

---

## Q: Why is Ricky's PC path weird in logs?

The host machine's user folder is `C:\Users\Ricky's PC\` — note the apostrophe. Several tools don't quote paths properly and choke on it. If you see shell commands failing with weird quoting errors in Ricky's env, that's usually the cause. See `TROUBLESHOOTING_DEV.md` section 7.

---

## Q: Why Windows-only?

Our paying customers are overwhelmingly on Windows. Cross-platform isn't a zero-cost feature — we'd need to test the GPU pipeline, Electron packaging, and installer on macOS and Linux separately. That cost hasn't been worth it yet. Not ruled out for 7.x.

---

## Q: Can I work from source or do I have to install?

Work from source whenever you can. `npm run dev` in `electron-app/` is the fastest loop. Only install a packaged build when you're validating the installer path or reproducing a customer-reported bug that doesn't repro in dev. See `docs/BUILD.md` for details.

---

## Q: How do I propose a feature?

1. Check `SPB_ROADMAP.md` — is it already on the list?
2. Check `OPEN_ISSUES.md` — is it already requested?
3. If neither: open a thread in `#spb-feedback` on Discord with the problem you're trying to solve, not the feature you want. We'll turn it into an issue if it lands.

Please describe problems first, solutions second. "Painters can't tell at a glance which zones share a finish" is a problem. "Add a zone-grouping indicator" is a solution. The first one invites discussion; the second one bypasses it.

---

## Q: What's the quickest way to find who owns a file?

`git log --oneline -- path/to/file | head -20` will show you the last 20 commits touching it. The most frequent author is usually the de facto owner. For engine files, that's often Ricky. For frontend, same.

---

## Q: I found a bug. Do I fix it or report it?

- **Obvious, one-line, no behavior change:** fix it, one-line commit, link it in the PR.
- **Touches shared state or changes behavior:** report first, discuss, then fix.
- **In engine math:** always report first. Engine changes need reviewers.

When in doubt, ask in `#spb-dev` before committing.

---

*Add Q&A here as new questions come in. Good FAQs grow from real confusion, not speculation.*
