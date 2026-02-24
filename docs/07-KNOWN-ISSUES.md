# Shokker Paint Booth — Known Issues, Quirks & Dev Notes

## Bugs Fixed (Reference)

### Settings Button Not Working
**Problem:** `document.querySelector('.gear-btn')` matched the `?` shortcut help button instead of the `⚙` settings gear button — both had class `gear-btn`.
**Fix:** Added `id="settingsGearBtn"` to the settings button and switched to `getElementById('settingsGearBtn')`.
**Lesson:** Avoid relying on class selectors when multiple elements share the same class. Use IDs for unique interactive elements.

### License Gate Blocking Renders
**Problem:** Both server-side (server.py ~line 532) and client-side (doRender() in HTML) license gates were active, preventing any renders during Alpha.
**Fix:** Commented out both gates. They're fully implemented and ready to re-enable when licensing goes live.
**Server gate location:** `/render` endpoint, around line 532 in server.py
**Client gate location:** `doRender()` function, license check before ShokkerAPI.render() call

## Development Environment

### Python Path
- Hardcoded: `C:\Python313\python.exe`
- If Python is installed elsewhere, server.py will need path adjustment

### Working Directory
- All files in: `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\`
- Server must be started FROM this directory (or paths will break)
- TGA files reference absolute Windows paths

### Server Startup
- Port 5000 (hardcoded)
- No auto-restart on crash
- No daemon mode — runs in foreground terminal
- PowerShell Start-Process with redirected stdout/stderr works for background operation

### Dependencies
- Flask (pip install flask)
- NumPy (pip install numpy)
- Pillow (pip install Pillow)
- All other imports are stdlib (struct, json, os, uuid, etc.)

## Known Quirks

### HTML File Size
The frontend is a single 16,252-line file. This is intentional (no build step, no framework), but:
- Some editors may lag with syntax highlighting
- Desktop Commander search (`start_search`) returns 0 results on files this large — use PowerShell `Select-String` as workaround
- AI assistants may need to read it in chunks (recommended: 500-line increments)

### localStorage Dependency
Multiple features rely on localStorage:
- Zone templates
- Finish combos
- Finish browser favorites
- Auto-save/restore
- Tutorial completion flag
- If localStorage is cleared, all user customizations are lost
- No server-side persistence for these features (by design — keeps it simple)

### Pattern Preview Renderer (~1,500 lines)
The `renderPatternPreview()` function is massive — ~50+ Canvas-based texture generators for offline swatch display. This is intentionally client-side to avoid server round-trips for browsing finishes. If adding new finishes to the engine, a corresponding preview generator should be added to this function.

### Canvas State Complexity
The canvas viewport manages multiple overlapping concerns:
- Zoom level and pan offset
- Current tool mode (8 modes)
- Region mask painting (per-zone Uint8Array)
- Recolor mask painting
- Compare mode divider
- Decal layer positioning
- Preview split view

Mouse events route differently depending on which mode/state is active. Changes to mouse handling need to account for all these states.

### Zone Color Detection vs Region Masks
Two parallel systems determine "which pixels belong to this zone":
1. **Color detection** — Automatic, based on zone.color/colors + tolerance
2. **Region masks** — Manual, painted via canvas tools (Uint8Array)

These combine via OR logic: a pixel is "in zone" if EITHER system claims it. This means:
- A zone with color "#FF0000" AND a hand-painted mask will include both the red pixels AND the painted region
- Clearing colors doesn't clear the region mask (and vice versa)
- The "remaining" selector works against color detection only — region masks are additive on top

### Recolor Mask Encoding
When saving/loading configs, the recolor mask (Uint8Array, 2048×2048) is RLE-encoded to reduce JSON size. The encoding/decoding must match between save and load operations. Format: base64-encoded RLE where runs are (value, count) pairs.

### Render Job Cleanup
Render output files accumulate in the temp directory. The `/cleanup` endpoint exists to purge old jobs, but it's not automatic. Long sessions with many renders can consume significant disk space.

### Preview Hash System
The preview system uses a hash of zone configurations to avoid redundant previews. If the hash logic misses a change (edge case), the preview won't update. Force-refresh by toggling split view off and on.

### AbortController for Previews
Rapid zone changes can fire multiple preview requests. AbortController cancels superseded requests, but the server may still process them briefly before the abort reaches it. This is cosmetic — no data corruption, just minor wasted CPU.

## Architecture Decisions

### Why No Framework?
- Single-user local tool — no routing, no SSR, no complex state needed
- Zero build step means easy iteration
- No node_modules, no webpack, no transpiling
- Claude can read and modify the HTML directly
- Trade-off: the file is huge, but it's all in one place

### Why Flask?
- Dead simple to set up and run
- Python engine can be imported directly (no IPC needed)
- Adequate for single-user local operation
- No async needed (renders are synchronous and intentionally blocking)

### Why TGA?
- iRacing's native format — no conversion step needed
- 32-bit RGBA maps perfectly to the 4 spec channels
- Uncompressed = simple read/write (no codec dependencies)
- 2048×2048 is iRacing's standard resolution

### Why Monolithic HTML?
- Avoids multi-file coordination headaches
- Single file = single source of truth
- No import/module resolution issues
- Claude can grep/read it as one unit
- Trade-off: harder to navigate manually, but Ctrl+F works

## Future Considerations

### EXE Packaging
All 11 Alpha features are complete. Next major milestone is packaging as a standalone executable:
- PyInstaller or similar for Python bundling
- Embedded Flask server
- Auto-start browser on launch
- Need to handle: file path resolution, temp directories, asset bundling
- License system ready to re-enable for distribution

### Performance
- Large renders (10 zones, complex patterns) can take 10-30 seconds
- Preview renders are faster due to lower resolution
- Pattern preview renderer (client-side) can be slow on initial load with many swatches visible
- Lazy rendering helps but could be optimized further

### Missing from Alpha
- No user accounts / cloud sync
- No undo for canvas brush strokes (only zone property undo)
- No multi-car batch design (fleet mode renders same design, doesn't design per-car)
- No AI-assisted design suggestions (beyond the NLP chat bar)
- No direct paint file editing (beyond recolor)
- No custom finish creation UI (engine supports it, UI doesn't expose it)

## Quick Reference: Key Line Numbers in HTML

| System | Approximate Lines |
|--------|-------------------|
| CSS Variables & Styles | 1–2600 |
| HTML Structure | 2600–3900 |
| Data Arrays (BASES, PATTERNS, MONOLITHICS) | 3900–4600 |
| Group Maps & Quick Colors | 4600–4700 |
| Presets | 4700–5050 |
| State Variables | 5050–5150 |
| Undo System | 5150–5350 |
| init() & renderZones() | 5380–5900 |
| Zone Detail & Color Mgmt | 5900–7000 |
| Presets, Toast, Notifications | 7000–7200 |
| Config Save/Load | 7200–7600 |
| Canvas Setup & Handlers | 8500–9500 |
| Preview System | 9800–10100 |
| Zoom & Pan | 10100–10600 |
| Pattern Preview Renderer | 10700–12200 |
| ShokkerAPI Object | 12550–12750 |
| Fleet & Season Mode | 12800–13100 |
| doRender & showRenderResults | 13100–13650 |
| Decal System | 13900–14100 |
| Livery Templates | 14100–14400 |
| Before/After Compare | 14400–14550 |
| Finish Browser | 14550–14750 |
| Zone Templates & Combos | 15000–15300 |
| NLP Chat | 15300–15700 |
| Color Harmony | 15700–15850 |
| Keyboard Shortcuts | 15850–16000 |
| Init & Auto-Restore | 16000–16020 |
| Licensing | 16020–16120 |
| Tutorial/Onboarding | 16120–16252 |
