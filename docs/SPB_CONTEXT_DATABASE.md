# SPB Context Database

Status: repo-wide context map for low-usage AI work.

The Shokker Paint Booth app has monster files that should not be read casually. The context database gives agents named, small slices of those files.

## Files

- `scripts/spb_context.js` is the gateway/engine.
- `scripts/spb_context_targets.json` is the editable target database.
- `docs/SPB_LOW_USAGE_PROTOCOL.md` explains when to use it.

## How To Use

```powershell
node scripts\spb_context.js --list
node scripts\spb_context.js --target server-render-monitoring
node scripts\spb_context.js --target canvas-dispatch
node scripts\spb_context.js --find "register_render_monitoring_routes" server.py --context 2 --max 5
```

## How To Add A Target

Add an entry to `scripts/spb_context_targets.json`:

```json
"server-example": {
  "domain": "server",
  "description": "Short reason this target exists.",
  "slices": [["server_routes/example.py", 1, 120]]
}
```

Rules:

- Prefer extracted small modules over slices from monster files.
- Keep slices focused; a target should usually stay under 250 printed lines.
- If a monster-file slice is necessary, include only the local guard/entrypoint needed for orientation.
- Add a target whenever code is extracted into a smaller module.
- Do not add Electron mirrors, archives, logs, generated dumps, or image assets as targets.

## Current Priority

Continue moving safe server/UI responsibilities into smaller modules, then point this database at those modules. The win is twofold: better code structure and cheaper context for every future agent.
