# SPB v6.2.0 "Boil the Ocean" — Discord Announcement

> Copy-paste this directly into the `#announcements` channel. Discord markdown only (no tables, no images inline — use attachments for screenshots).

---

@everyone

# SHOKKER PAINT BOOTH v6.2.0 — "BOIL THE OCEAN" IS LIVE

We didn't pick a corner to polish. We set the whole pot on the burner.

This is the biggest single release in SPB history. **1,400+ improvements.** Every system touched. Every pipeline rebuilt. If you've been waiting for the version that is "actually ready," this is it.

---

## The Stats

- **1,400+** improvements in one sprint
- **214** spec patterns across 19+ categories
- **93** server endpoints — every one tested
- **77** passing automated tests (zero regressions shipped)
- **5** new layer effects (Drop Shadow, Outer Glow, Stroke, Color Overlay, Bevel)
- **0** breaking changes — your v6.1 save files still open

---

## Why You Should Care

**SPB is now the only livery tool that does per-channel spec pattern control with real-time car-shape preview and zone-level spec settings.** Not Photoshop. Not Paint Builder. Not GIMP. Not paint.net. One tool. This one.

If you are making iRacing liveries and you are not using SPB, you are doing twice the work for half the result. That's not hype. That's math.

---

## What's New — The Headline Features

**First-run default: Chevy Silverado 2019 PSD**
Open the app. There's a real car there. No blank canvas anxiety. Start painting in 3 seconds.

**Auto-restore last paint file**
Close the app. Reopen. Your zones, your layers, your history — all back. Exactly where you left off.

**Layer Effects — FINALLY**
Drop Shadow. Outer Glow. Stroke. Color Overlay. Bevel. All five. Per layer. Live preview. Behaves like Photoshop expects.

**Layer contribution mask bug — KILLED**
That bleed-through bug where layers leaked outside their mask during final render? Gone. Alpha is now the single source of truth. Render matches screen, pixel-for-pixel.

**214 spec patterns**
Chrome family. Metallic flake. Brushed directional. Iridescent bugs. Anime specular. Military tactical. Neon underground. Candy candy candy. Exotic metal. Ceramic glass. Carbon composite. You want it, we built it.

**GGX floor fixes**
Mirror chrome is finally mirror chrome. Six related PBR bugs squashed. Your reflections look right now.

**93 server endpoints, 77 passing tests**
We built out the API surface so third-party integrations can actually happen. Tests mean the engine doesn't regress. If something worked yesterday it works tomorrow. Full stop.

**`F5` to refresh preview**
Flush the cache. Re-render from disk. Works anywhere in the app.

**`?` for keyboard shortcut cheat sheet**
Full overlay. Searchable. Click-through-dismissible.

**`Ctrl+L` to lock zone to layer**
Pin a zone to its source layer so stray clicks can't unpin it. Sounds small. Saves hours.

---

## Killer Features With Taglines

> "**First-Run Silverado.**" — Paint in three seconds. No blank canvas. No confusion.

> "**Auto-Restore.**" — Close the app. Reopen. Pick up exactly where you left off.

> "**Five Layer Effects.**" — Shadow, Glow, Stroke, Overlay, Bevel. Per layer. Live.

> "**214 Spec Patterns.**" — Every material you've ever wanted, built-in.

> "**93 Endpoints.**" — API-first. Extensible. Testable.

> "**Per-Channel Spec Control.**" — R/G/B/A each get their own pattern. Nobody else does this.

> "**Zone-Level Overrides.**" — Different spec per zone. Different material per panel.

> "**Real-Time Car Preview.**" — See it on the car shape. Not a flat square. Not a wireframe. The car.

---

## What's Fixed (Critical)

- **Layer alpha bleed-through** — gone
- **Live Preview crash on empty zones** — gone
- **Invisible "Add Zone" button** — now glows bright green
- **GGX floor clamping** — six warnings resolved
- **Render-status 404** — poller now hits a real endpoint
- **sourceLayer not persisting** — zones remember their layer on reload
- **Paint file not auto-loading on restore** — it does now

---

## Upgrade

1. Close SPB
2. Back up your PSDs (always)
3. Run the new installer
4. Launch
5. Press `?` and see what's new

**Full release notes:** see `SPB_RELEASE_NOTES.md` in your install folder.

**Full feature catalog:** `SPB_FEATURES.md`

**Workflow recipes (12 step-by-step builds):** `SPB_WORKFLOW_EXAMPLES.md`

**Spec map deep dive:** `SPB_SPEC_MAP_GUIDE.md`

**Troubleshooting:** `SPB_TROUBLESHOOTING.md`

**Keyboard shortcuts:** `SPB_KEYBOARD_SHORTCUTS.md`

---

## Screenshots

*[Attach: welcome-screen.png — welcome screen with Silverado loaded]*

*[Attach: layer-effects.png — layer effects panel with Drop Shadow + Outer Glow active]*

*[Attach: spec-picker-tabs.png — spec pattern picker showing category tabs]*

*[Attach: zone-cards.png — zone list with muted-zone dimming and finish badges]*

*[Attach: shortcut-overlay.png — `?` keyboard shortcut overlay]*

*[Attach: chrome-mirror-comparison.png — before/after of GGX floor fix on chrome]*

---

## Call To Action

**Download:** the latest build is in your PayHip library. License holders get this free. No new license needed.

**Test:** open a project you've been stuck on. Try the new layer effects. Try locking a zone to a layer. Press `?` and discover five shortcuts you didn't know existed.

**Share:** post your first v6.2 livery in `#showcase`. Tag it `#BoilTheOcean` so we can find it.

**Report bugs:** `#bug-reports` channel. Include your log file (`SPB_TROUBLESHOOTING.md` tells you where it lives).

**Request features:** `#feature-requests`. v6.3 roadmap is being shaped now. Loud voice wins.

---

## One More Thing

This release took everything we had. Not just "a lot of work." Everything. Systems that were good became great. Systems that were rough got rebuilt. The engine is in a place now where we can start extending it in directions that were impossible six months ago.

If you've been rolling with SPB since the early Gold builds — thank you. You got us here.

If you're new — welcome. This is what's possible when a tool is built by people who actually paint cars.

**Go make something.**

— The Shokker Team

---

*SPB v6.2.0 "Boil the Ocean" — 2026-04-17. Paint hard. Ship clean.*
