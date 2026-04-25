# SPB Session Key Router

**Owner:** Flair (Win #1 of TWENTY WINS shift, 2026-04-19)
**Files:** `paint-booth-3-canvas.js`, `paint-booth-2-state-zones.js`,
`paint-booth-6-ui-boot.js`, `paint-booth-layer-flow.js`

## Why this exists

SPB has 32 separate `document.addEventListener('keydown', ...)` listeners
across 4 JS files. Pre-Twenty-Wins they were a "listener-order roulette":
whichever one was registered first won the race, regardless of which
edit mode the painter was actually in. That meant Free Transform Esc
sometimes lost to a generic Esc handler, Ctrl+Z occasionally cancelled
a transform AND popped the undo stack, and tool hotkeys could fire
inside an active modal.

This doc defines the precedence model the listeners now honor. Every
document-level keydown listener bails on `e.defaultPrevented` so that a
higher-precedence handler can claim the event by calling `e.preventDefault()`.

## Precedence model (highest priority first)

1. **Form input focus** (INPUT, TEXTAREA, SELECT, contentEditable).
   - Every document listener checks the active element's tag and
     bails. The native form input handler gets the keystroke.
   - Form-element handlers (rename input, hex input, text-tool input)
     handle Enter/Esc themselves and call `e.preventDefault()` +
     `e.stopPropagation()`.

2. **Capture-phase modal handlers.**
   - Lightbox / preview overlay / FX dialog use
     `addEventListener('keydown', handler, true)` to claim the event
     in the capture phase before any document listener sees it.
   - These call `e.preventDefault()` to halt the bubble.

3. **Free Transform session** (`canvas.js:7046`).
   - Owns Esc (cancel), Enter (commit), Ctrl+Z (cancel session) when
     `freeTransformState` is non-null.
   - Calls `e.preventDefault()` AND `e.stopImmediatePropagation()` so
     no other listener fires for that keystroke.

4. **Master shortcut handler** (`state-zones.js:513`).
   - Owns Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z, Ctrl+D, Ctrl+A, Ctrl+Shift+I,
     Ctrl+C, Ctrl+X, Ctrl+V, Ctrl+J, Ctrl+E, Ctrl+Shift+E, Ctrl+Shift+N,
     Backspace fill, Delete selection, Enter (placement finish).
   - Routes through `cancelActiveTransformSession()` /
     `cancelSelectionMove()` / `_cancelActivePlacementDrag()` first,
     so a pending edit mode wins before generic undo/select/etc.
   - Calls `e.preventDefault()` on every recognised shortcut.

5. **Specific edit-mode listeners.**
   - Pen tool Enter/Esc (`canvas.js:9884`).
   - Lasso Backspace (`canvas.js:15762`).
   - Active stroke Esc cancel (`canvas.js:15774`).
   - Each bails on `defaultPrevented` and matches a specific tool +
     key combo.

6. **Generic tool / app shortcuts.**
   - Tool hotkeys T/U/S/N/C/M (`canvas.js:8297`).
   - F-double-tap fit (`canvas.js:15190`).
   - Selection grow/shrink Ctrl++/- (`canvas.js:15289`).
   - Arrow-key region nudge (`canvas.js:15694`).
   - Overlay opacity ,/. (`canvas.js:15895`).
   - FG/BG default Shift+D (`canvas.js:15960`).
   - UI scale Ctrl+=/- (`state-zones.js:113`).
   - Before/after toggle B (`state-zones.js:3581`).
   - Swatch picker Esc (`state-zones.js:4592`).
   - Zone reorder Ctrl+Up/Down (`state-zones.js:10315`).
   - New zone N (`state-zones.js:10862`).
   - F1 cheat sheet (`ui-boot.js:3781`).
   - Ctrl+Shift+R reload paint (`ui-boot.js:4284`).
   - Ctrl+L lock zone to layer (`layer-flow.js:1101`).

7. **Window blur safety net** (`canvas.js:15014`).
   - Resets held-Alt eraser flag, isDrawing flag, and grab cursor when
     the window loses focus mid-stroke.

## The contract

**Every document-level keydown listener MUST start with:**

```js
if (e.defaultPrevented) return;
```

**A handler that wants to OWN a keystroke MUST call:**

```js
e.preventDefault();
// And, if it must hide the event from later listeners entirely:
e.stopImmediatePropagation();
```

**A form-input handler MUST call:**

```js
e.preventDefault();
e.stopPropagation();
```

…inside an INPUT/TEXTAREA/SELECT element's own keydown handler so the
event doesn't reach document-level listeners that would compete with
the input's text editing.

## What was wrong before

Pre-Twenty-Wins, of the 32 keydown listeners across the 4 files:

- 5 honored `defaultPrevented` (the master handler at state-zones.js:513,
  the Free Transform handler at canvas.js:7046, the input-scoped
  handlers, and a couple of newer additions).
- 27 did NOT bail on `defaultPrevented`. They relied on either
  `e.ctrlKey` short-circuits or "this key isn't the one I care about"
  to avoid colliding — but any keystroke that overlapped multiple
  listeners would fire all of them.

After Win #1, every document-level keydown listener bails on
`defaultPrevented` as its first line. Form-scoped handlers (text-tool
input, hex input, rename input) keep their own behavior unchanged
because they're scoped to a single element and are guarded by the
document listeners' tagName-check.

## Tests

Regression tests live in `tests/test_layer_system.py`:

- `test_session_router_every_global_keydown_bails_on_default_prevented`
  — ratchet: structurally verifies every `document.addEventListener('keydown', …)`
  in the 4 main JS files contains `if (e.defaultPrevented) return;` within
  the first 5 lines of the handler body.
- `test_free_transform_handler_uses_stop_immediate_propagation` —
  proves Free Transform's Esc/Enter/Ctrl+Z handler halts dispatch
  entirely so generic Esc/Ctrl+Z handlers can't fire alongside.
- `test_master_shortcut_handler_routes_to_transform_first` — proves the
  master Ctrl+Z handler tries `cancelActiveTransformSession` before
  generic undo, so transform owns Ctrl+Z when active.

## What this does NOT do

This is a precedence FIX, not a refactor. The 32 listeners are still
32 listeners. A deeper refactor (single dispatcher with handler
registration) would be a multi-shift project; this win unlocks the
trust without paying that cost.

## Future improvement (deferred)

A deferred follow-up: extract the `defaultPrevented + tag check` pair
into a shared `_spbKeyShouldRoute(e)` helper so listeners read:

```js
if (!_spbKeyShouldRoute(e)) return;
```

That will let us add new precedence rules in one place. Current shift's
discipline: bail-out only.
