# Shokker Paint Booth — Diagnostic Toolkit

Workstream 17 (#321–#340) of the Heenan Family Overnight Sprint.

This file lists every opt-in diagnostic hook added to SPB, what it shows,
and how to enable it. All hooks are silent by default — no perf cost when
not enabled. Designed for two audiences:

1. **Painters reporting bugs** — copy-paste output into a bug report
2. **Developers tracing tricky flows** — confirm timing / sequencing

## How To Enable

Open the Electron devtools console (Ctrl+Shift+I) and set the relevant
flag(s) to `true`. They all live on `window` and persist for the session
(reload to clear). Set back to `false` (or reload) to disable.

## Available Hooks

### Layer system

| Flag | What it logs | Tag |
|---|---|---|
| `window._SPB_DEBUG_PREVIEW` | Every `triggerPreviewRender()` call with a parsed caller frame | `[preview-trace]` |
| `window._SPB_DEBUG_TRANSFORM` | Free Transform commit + cancel: rotation, scale, center, restored bbox | `[SPB][transform]` |
| `window._SPB_DEBUG_MERGE` | Merge-down + flatten-all: layer count, layers, effects flags | `[SPB][merge]` |
| `window._SPB_DEBUG_EFFECTS` | Each `updateLayerEffect` call: effect.prop = value, layer name, session-undo flag | `[SPB][effects]` |
| `window._SPB_DEBUG_SOURCE_LAYER` | Each render payload's source-layer block: layerId, mask bytes, RGB bytes, bbox | `[SPB][source_layer]` |

### One-shot inspector helpers (call from console)

| Call | Returns | Notes |
|---|---|---|
| `dumpLayerState()` | Full layer-stack snapshot (id, name, visible, opacity, blendMode, locked, bbox, effectsEnabled, imgKind) plus undo/redo depths | Logs to console AND returns the object so you can copy or `JSON.stringify` it |
| `dumpZonePayload(zoneIndex)` | Zone summary (sourceLayer, sourceLayerExists, masks, etc.) | Use to confirm what the zone WILL send to the engine |
| `getActiveTargetSummary()` | `'composite'` or `'layer:<name>'` (with `(locked)` / `(hidden)` tags) | Tells you where the next op will land |

### Auto-warnings (always on, throttled)

| Trigger | What you see | Throttle |
|---|---|---|
| Painting on a hidden layer | Toast: *"<layer> is hidden — toggle visibility to see your strokes"* | Once per layer per stroke session |
| Painting on a locked layer | Toast: *"<layer> is locked — unlock to paint on it"* | Once per layer per stroke session |
| Zone with dangling sourceLayer | `console.warn` at every preview render the zone is part of | Per-render-call |

## Usage Examples

**Before reporting a bug**:
```js
// In devtools console
copy(JSON.stringify(dumpLayerState(), null, 2))
// Paste into the bug report.
```

**Tracing a "preview is stale" complaint**:
```js
window._SPB_DEBUG_PREVIEW = true
// Repro the user's action. Check console for [preview-trace] frames.
// If you see the call, the preview pipeline ran. If not, the trigger never fired.
```

**Tracing a "merge dropped my drop shadow" complaint**:
```js
window._SPB_DEBUG_MERGE = true
// Hit Merge Down. Console shows whether upper.effects + lower.effects existed.
// Cross-check the rendered result.
```

**Tracing a "Free Transform Ctrl+Z doesn't work" complaint**:
```js
window._SPB_DEBUG_TRANSFORM = true
// Repro: transform commit, then Ctrl+Z.
// You should see commit log first, then NO cancel log
// (Ctrl+Z doesn't go through cancelLayerTransform — it goes through
// undoLayerEdit). The undo path is well-tested in tests/test_layer_system.py.
```

## Tests Cover

| Hook | Test |
|---|---|
| `_SPB_DEBUG_PREVIEW` | `test_trigger_preview_render_has_debug_trace_hook` |
| `_SPB_DEBUG_TRANSFORM` | `test_commit_layer_transform_has_debug_logging` + cancel variant |
| `_SPB_DEBUG_MERGE` | `test_merge_layer_down_has_debug_logging` + flatten variant |
| `_SPB_DEBUG_EFFECTS` | `test_update_layer_effect_has_debug_logging_hook` |
| `_SPB_DEBUG_SOURCE_LAYER` | (no test — Flair's diagnostic is opt-in only) |
| `dumpLayerState` | `test_dump_layer_state_diagnostic_present` |
| `dumpZonePayload` | `test_dump_zone_payload_diagnostic_present` |
| `getActiveTargetSummary` | `test_active_target_summary_helper_exists` |

## Backlog Tasks Closed By This Doc

- #333 (docs for using diagnostics)

## Backlog Tasks Implemented Elsewhere

- #321 dumpLayerState — paint-booth-3-canvas.js
- #322 dumpZonePayload — paint-booth-3-canvas.js
- #323 preview invalidation debug flag (#216 / `_SPB_DEBUG_PREVIEW`)
- #324 effect-session debug logging (`_SPB_DEBUG_EFFECTS`)
- #325 source-layer payload debug logging (Flair via #159 / `_SPB_DEBUG_SOURCE_LAYER`)
- #326 merge/flatten debug logging (`_SPB_DEBUG_MERGE`)
- #327 transform commit/cancel logging (`_SPB_DEBUG_TRANSFORM`)
