# SPB 6.2.0-alpha — Alpha Tester README

Welcome, and thank you for helping us shake out **Shokker Paint Booth 6.2.0 — "Boil the Ocean."** This build represents the biggest jump in engine quality, finish catalog depth, and workflow polish we've ever shipped in a single release. It also, because it's an **alpha**, has rough edges. This note explains what to expect, how to help, and how to bail out if anything goes sideways.

---

## What "Alpha" means here

Alpha at Shokker means:

- Core features work end-to-end on a clean machine.
- Several new features are **functionally complete but not polished** — they do the job, but the UI or naming may still shift before public release.
- Data formats (Shokks, preset files) are **stable unless we flag otherwise** in the release notes. If a format needs to break we will tell you in the announcement.
- Performance targets are met on our reference hardware but not fully audited across GPUs.
- We expect you to hit at least one bug. If you don't, we would genuinely love to know what you painted.

---

## What's New in 6.2.0

These are the headline additions since 6.1.x. The full list lives in `CHANGELOG.md`.

- **Finish Catalog Expansion** — 30+ new finishes across monolithics, candy specials, anime-style, ceramic glass, and exotic metals.
- **Custom Gradient System** — build your own base-color gradients without touching code.
- **Finish Mixer + Pattern Strength Zones** — per-zone control over how aggressively a pattern overlays a base.
- **Spec Overlay Overhaul** — 100 new spec-map patterns with proper GGX floors so highlights don't blow out.
- **Quality Audit Fixes** — hundreds of finishes retouched for parity between preview and final render.
- **Performance** — cold start and warm render both measurably faster; GPU pipeline cleaner.

---

## What's stable

You can lean on these the same as any prior release:

- Zone painting and region masking
- Loading and saving Shokks
- Base, finish, and pattern registries (3-copy sync pipeline is healthy)
- Spec R/G/B channel conventions (R=metallic, G=roughness, B=clearcoat with the inverted scale)
- Iron Rules and Live Link
- The core render pipeline and preview loop

---

## What's still moving

These features are in the build but may change before 6.2.0 public:

- **Spec picker tabs** — layout and labels may reshuffle based on your feedback.
- **Finish Mixer UI** — sliders are functional; tooltips and value snapping are still being tuned.
- **Pattern Strength Zones** — exposed but naming conventions ("strength" vs "intensity" vs "weight") are not final.
- **GPU fallback path** — aggressive; if your GPU misbehaves we're eager to see the log.

Don't build muscle memory around UI positions yet. Names and slider ranges may still change.

---

## How to report bugs

We want volume. Small weirdness is still useful. Please use this template in `#spb-qa` on Discord:

```
Build:   6.2.0-alpha
OS:      Windows 10/11, edition
GPU:     (right-click desktop -> Display settings -> Advanced)
Steps:   1. ...
         2. ...
         3. ...
Expected:
Actual:
Logs:    (attach %APPDATA%\ShokkerPaintBooth\logs\ if relevant)
```

**What makes a great bug report:**

1. Exact steps from a fresh launch.
2. A screenshot of the offending state.
3. The most recent log file.
4. Whether it reproduces on a second launch.

**What makes a mediocre bug report:** "the paint looked weird."

Mediocre reports are still welcome; we'll write back and ask. Don't let "I can't describe it" stop you from posting.

---

## Rollback instructions

If 6.2.0-alpha breaks something important for you and you need to get back to a known-good build:

1. Close SPB completely (check Task Manager for stray `python.exe` from `pyserver`).
2. Uninstall via `Add or remove programs`.
3. Delete `%APPDATA%\ShokkerPaintBooth\cache\` (leave `shokks\` alone — that's your work).
4. Install the previous 6.1.x build from the release vault link posted in `#spb-announcements`.
5. Launch. Confirm your saved Shokks still load.
6. Post in `#spb-qa` that you downgraded and why — that's the most valuable signal we can get.

If a Shokk you saved in 6.2.0-alpha refuses to load in 6.1.x, **don't panic and don't overwrite it**. Send it to us and we will recover the data.

---

## What we need from you this cycle

Ranked by value:

1. **Try weird combinations.** Chrome + candy + animated spec. Four-way pattern blends. Zones smaller than 100 pixels. Break it.
2. **Tell us which new finishes feel wrong.** "Feels wrong" is legitimate feedback; we'll dig into why.
3. **Screenshot every crash, even ones that look minor.** Stack traces age badly.
4. **Save + reload at least one real project.** Round-trip bugs are the worst kind to find late.
5. **Watch memory over long sessions.** If the app creeps past 2 GB after an hour, we want to know.

---

## What you can ignore (for now)

- Minor label typos. We have a separate polish pass queued.
- "Which shortcut changed?" questions — shortcuts are frozen for alpha.
- Draft docs in `/docs/` that still say TODO — those are intentional scaffolding and will be filled in before public release.

---

## Contact

- **Fastest:** Discord `#spb-qa`
- **Private bug / concern:** DM `@Ricky` on Discord
- **Email:** `ricky@shokkergroup.com`

Thank you for being in the room while this is still being built. You are why the public release doesn't suck.

— Ricky and the Shokker team
