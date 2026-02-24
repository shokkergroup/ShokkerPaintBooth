# Shokker Paint Booth — UI Systems (paint-booth-v2.html)

## Overview

The entire frontend is a single 16,252-line HTML file with inline CSS and JavaScript. No frameworks, no build step, no external dependencies beyond CDN fonts. Dark theme throughout.

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER BAR                                                  │
│ [Logo] [Car Paint Path] [Browse] [Output Path] [iRacing ID] │
│ [Version Badge] [⚙ Settings] [? Shortcuts]                  │
├────────────┬──────────────────────────┬─────────────────────┤
│ LEFT       │ CENTER                   │ RIGHT               │
│ SIDEBAR    │ CANVAS VIEWPORT          │ PANEL               │
│            │                          │                     │
│ Zone Cards │ [Toolbar]                │ Finish Library      │
│ (scrollable│ [Paint/Spec Canvas]      │ (Bases/Patterns/    │
│  list)     │ [Zoom Controls]          │  Monolithics tabs)  │
│            │                          │                     │
│ [Add Zone] │                          │ OR                  │
│ [Presets]  │                          │ Recolor Panel       │
│ [Render]   │                          │ Spec Visualizer     │
│ [Chat Bar] │                          │                     │
├────────────┴──────────────────────────┴─────────────────────┤
│ MODALS (overlay when active):                                │
│ Finish Browser, Finish Compare, Preset Gallery,              │
│ Template Library, History Gallery, Tutorial, License          │
└─────────────────────────────────────────────────────────────┘
```

## CSS System

### Theme Variables (CSS Root)
```css
:root {
  --bg-dark: #1a1a2e;
  --bg-card: #16213e;
  --bg-input: #0f3460;
  --accent: #e94560;
  --accent-hover: #ff6b6b;
  --text-primary: #eee;
  --text-secondary: #aaa;
  --border: #333;
  --success: #4ecdc4;
  --warning: #f39c12;
  --danger: #e74c3c;
}
```

### Key CSS Sections (~lines 1-2600)
- Root variables and base styles
- Custom scrollbar (thin, dark)
- Header bar (fixed top, flex layout)
- Settings dropdown (gear icon toggle)
- Zone cards (draggable, with color dots)
- Swatch picker (grid of finish options)
- Canvas viewport and toolbar
- Modal overlays (full-screen with backdrop)
- Finish browser (catalog/list view toggle)
- Tooltip system
- Undo history panel
- Tutorial overlay
- Compare mode (split divider)
- Color harmony panel
- Responsive adjustments (minimal — desktop-first)

## Zone System

### Default Zones (10)
Created in `init()`:
1. Body Color 1
2. Body Color 2
3. Body Color 3
4. Body Color 4
5. Car Number
6. Custom Art 1
7. Custom Art 2
8. Sponsors/Logos
9. Dark/Carbon Areas
10. Everything Else

### Zone Object Structure
```javascript
{
  name: "Body Color 1",
  color: "#FF0000",           // Primary color selector
  colors: ["#FF0000"],        // Multi-color array
  colorMode: "quick",         // quick | picker | text | multi | special
  tolerance: 30,              // Color match tolerance (0-100)
  base: null,                 // Base ID or null
  pattern: null,              // Pattern ID or null (legacy single)
  patternStack: [],           // Up to 3 layers [{id, opacity, scale, rotation}]
  monolithic: null,           // Monolithic ID or null
  intensity: "medium",        // Preset name or "custom"
  customIntensity: {          // Only used when intensity="custom"
    spec_mult: 1.0,
    paint_mult: 0.6,
    bright_mult: 0.5
  },
  wear: 0,                    // 0-100
  muted: false,               // If true, zone is skipped during render
  regionMask: null,           // Uint8Array or null (hand-painted mask)
  linked: null                // Zone index to link to, or null
}
```

### Zone Card UI (renderZones())
Each zone card displays:
- Drag handle (☰) for reordering
- Zone number badge
- Color indicator dot (shows selected color)
- Name input (editable)
- Finish summary text (e.g., "Gloss + Carbon Fiber")
- Action buttons: Mute (🔇), Duplicate (📋), Move Up/Down (↑↓), Link (🔗), Delete (🗑)
- Color selector row: Quick colors (12 preset), text input (hex/name), picker, multi-color, special ("remaining")
- Base swatch trigger (opens right panel to base tab)
- Pattern swatch trigger (opens right panel to pattern tab)
- Pattern stack controls (add layer, per-layer opacity/scale/rotation)
- Wear slider (0-100)
- Intensity controls (preset buttons or custom sliders)

### Zone Detail Panel (renderZoneDetail())
Floating side panel with expanded controls for the selected zone. Same data as the card but with more space for sliders and previews.

### Color Modes
- **Quick** — 12 preset named colors (Red, Blue, Green, Yellow, Orange, Purple, White, Black, Gray, etc.)
- **Picker** — HTML color input (hex picker)
- **Text** — Type a hex value or color name
- **Multi** — Add multiple colors to one zone (chips display)
- **Special** — "Remaining" selector (everything not in other zones), "Everything" selector

## Canvas Viewport

### Toolbar
Located above the canvas:
- Eyedropper (pick color from paint)
- Brush (paint region mask)
- Eraser (remove from region mask)
- Rectangle (click-drag selection)
- Wand (flood fill with tolerance)
- Gradient (linear gradient mask)
- Select All (color-based global selection)
- Edge (edge detection fill)
- Zoom In/Out/Reset buttons
- Pan mode indicator

### Canvas Modes (canvasMode variable)
- `eyedropper` — Click to sample color, updates zone color
- `brush` — Paint into zone's regionMask (Uint8Array)
- `erase` — Remove from regionMask
- `rect` — Click-drag rectangle into regionMask
- `wand` — Flood fill from click point with tolerance
- `gradient` — Click-drag to create linear gradient in regionMask
- `selectall` — Global color selection into regionMask
- `edge` — Edge detection based fill

### Zoom System
- `ZOOM_STEPS` array defines discrete zoom levels
- Mouse wheel zooms toward cursor position
- `canvasZoom()` / `applyZoom()` handle transform
- Space + drag = pan
- Middle-click = pan
- Right-click = pan (when zoomed)
- 5px drag threshold prevents accidental pans

### Split View (Preview)
- Left pane: original paint
- Right pane: preview render
- Vertical divider (draggable)
- Auto-updates on zone changes (300ms debounce)
- Hash comparison skips unchanged configs
- AbortController cancels superseded preview requests

## Right Panel System

### Finish Library (panelMode = 'specmap')
Three tabs: Bases, Patterns, Monolithics

Each tab shows:
- Sub-group tabs (e.g., Classic, Metallic, Candy under Bases)
- Grid of finish swatches (CSS-generated previews via renderPatternPreview())
- Click to apply finish to selected zone
- Hover tooltip with finish name and description

### Recolor Panel (panelMode = 'recolor')
- Source color picker (what color to shift FROM)
- Target color picker (what color to shift TO)
- Tolerance slider
- Add Rule button
- Rules list with delete per-rule
- Recolor mask painting (include/exclude brush)
- Apply Recolor button

### Spec Visualizer
- PBR ball preview rendered with Blinn-Phong approximation
- Shows how current zone's spec values look on a 3D sphere
- Updates in real-time as spec values change

## Modal System

### Finish Browser
- Full-screen overlay catalog of all finishes
- CSS-generated swatch previews (no server round-trip)
- Search/filter by name
- Catalog view (grid) / List view toggle
- Favorites system (localStorage, star icon)
- Click to apply, close modal

### Finish Compare
- Side-by-side comparison of two finishes
- Swatches + spec value tables
- Helps decide between similar finishes

### Preset Gallery
- Grid of 16 pre-built presets
- Each preset configures multiple zones at once
- Click to apply, replaces current zone config
- Preview thumbnails

### Template Library
- User-saved zone configurations
- Save current zones as named template
- Load template (replaces zones)
- Delete template
- Export/Import as JSON

### History Gallery
- Grid of previous render thumbnails
- Click to view full render result
- Deploy button per history item

### Tutorial Overlay
- 8-step guided tour
- Highlights UI elements with spotlight
- Next/Skip buttons
- Auto-starts on first visit (localStorage flag)

### License Modal
- Key input field
- Activate/Deactivate buttons
- Status display
- Currently disabled for Alpha

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| 1-9 | Select zone by number |
| ↑/↓ | Navigate zones |
| Ctrl+↑/↓ | Reorder zones |
| N | Add new zone |
| D | Duplicate selected zone |
| Delete | Delete selected zone |
| R | Randomize selected zone |
| E | Toggle zone editor panel |
| / | Focus NLP chat bar |
| V | Toggle split view (preview) |
| H | Open history gallery |
| T | Open template library |
| ? | Toggle shortcut legend |
| Escape | Close any open modal |
| Ctrl+R | Trigger render |
| Ctrl+G | Generate/randomize all zones |
| Ctrl+S | Save config |
| Ctrl+Z | Undo zone change |
| Ctrl+Y | Redo zone change |

## NLP Chat Bar

Natural language zone configuration system at the bottom of the left sidebar.

### How It Works
1. User types command like: `@body gloss + carbon_fiber, aggressive, red`
2. Parser segments by comma, extracts @mention (zone name)
3. CHAT_SYNONYMS dictionary maps natural language to finish IDs (100+ mappings)
4. CHAT_COLOR_MAP maps color names to hex values
5. Parses: base, pattern, intensity, color, scale, name
6. Applies parsed config to matching zone

### @ Autocomplete
- Typing `@` triggers dropdown of zone names
- Context-aware: after zone selected, suggests bases → patterns → intensity
- Arrow keys + Enter to select
- Dropdown positioned relative to input cursor

### Example Commands
```
@body gloss + carbon, aggressive, red
@number chrome, extreme
@sponsors matte
Set body to candy blue with hex mesh, subtle
```

## Color Harmony System

- Converts colors to HSL for harmony calculations
- Generates 4 harmony types from any selected color:
  1. **Complementary** — 180° hue rotation
  2. **Analogous** — ±30° hue shifts
  3. **Triadic** — 120° intervals
  4. **Split-complementary** — 150° and 210°
- Renders mini color wheel with harmony dots
- Click any harmony color to apply to zone

## Toast Notification System

`showToast(message, type, duration)`:
- Types: success (green), error (red), warning (yellow), info (blue)
- Auto-dismiss after duration (default 3000ms)
- Stacks vertically for multiple toasts
- Used for render completion, errors, config save confirmation, etc.

## RenderNotify System

Multi-channel notification when render completes:
1. **Web Audio chime** — Short sine wave beep
2. **Tab title flash** — Alternates "✅ Render Complete!" with original title
3. **Browser notification** — Uses Notification API (if permission granted)

## Auto-Save & Restore

- Every zone change triggers `localStorage.setItem('shokker_autosave', JSON.stringify(getConfig()))`
- On page load: `autoRestore()` checks for saved config and reloads it
- Prevents data loss on accidental refresh/close

## Drag and Drop

- Drag a `.tga` paint file onto the canvas to load it
- Sets the car paint path and loads the image
- Triggers auto-preview if split view is active
