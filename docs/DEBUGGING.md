# SPB Debugging Guide

> What to do when SPB misbehaves, and the tools to figure out why.

---

## General Strategy

Always check these first, in order:

1. **Server terminal log** — does it show a Python traceback?
2. **Electron DevTools console** — Ctrl+Shift+I, look for red errors.
3. **`%APPDATA%\Shokker Paint Booth\logs\`** — persistent log files (packaged app only).
4. **Last render request** — `last_render_request.json` captures the POST body of the last render.

If those yield nothing, reproduce in the dev loop where you have full stdout.

---

## Enabling Debug Output

### Python engine debug
Edit `shokker_engine_v2.py` around line 84 to enable `_engine_rot_debug()`:

```python
def _engine_rot_debug(*args, **kwargs):
    # Flip this from `pass` to `print(...)` temporarily
    print("[engine]", *args, **kwargs)
```

> Don't commit this flipped. The function ships as a no-op for performance.

### JS client debug
Most SPB JS modules have a `DEBUG` flag near the top. Set to `true` to enable verbose `console.log`:

```js
const DEBUG = true;  // paint-booth-5-api-render.js etc.
```

### Flask server debug
`server.py` has `app.run(debug=True)` gated by an env var. Set:

```bash
set SPB_DEBUG=1
python server.py
```

---

## Common Symptoms → Common Fixes

### Symptom: "My new finish doesn't appear in the picker"

Checklist in order:
1. Is the finish in `BASES` (paint-booth-0-finish-data.js)?
2. Is the finish's ID listed in a `BASE_GROUPS` entry? (Un-grouped IDs are stripped at boot.)
3. Is the finish registered in `FINISH_REGISTRY` (engine/base_registry_data.py)?
4. Did you update all three copies?
5. Hard-reload the Electron window (Ctrl+Shift+R).

### Symptom: "Pattern silently renders nothing"

Likely missing from `PATTERN_REGISTRY` in Python. The UI shows it (because `PATTERNS` in JS has it) but the render returns no pattern contribution. Add the texture function to `engine/expansion_patterns.py` and register it.

### Symptom: "Render returns 500"

1. Check server terminal for traceback.
2. Reproduce in isolation:
   ```bash
   python -c "from server import render_spec; render_spec(<paste last_render_request.json>)"
   ```
3. Common: a `None` zone color, a missing finish ID, a mismatched spec shape.

### Symptom: "Chrome looks matte"

Spec map's B (clearcoat) channel is inverted from intuition. Chrome wants **B=16** (max gloss). If you set B=255 thinking "max shine" you'll get dull. See [../SPB_SPEC_MAP_GUIDE.md](../SPB_SPEC_MAP_GUIDE.md).

### Symptom: "App won't start after install"

1. Check `%APPDATA%\Shokker Paint Booth\logs\main.log`.
2. Common: Python server can't spawn because an antivirus quarantined `pyserver.exe`. Add AV exclusion.
3. Reinstall (uninstaller + fresh Setup.exe).

### Symptom: "Zones disappear after reload"

`.spb` file serialization issue. Check:
1. Did the save complete? (File dialog may have been cancelled.)
2. Is the file valid JSON? Open in a text editor.
3. Is there a version mismatch? `.spb` files from older SPB versions may drop fields.

---

## Tools

### Python profiler
```bash
python -m cProfile -o profile.prof benchmark_finishes.py --finish chrome
pip install snakeviz
snakeviz profile.prof
```

### JS profiler
DevTools → Performance tab → Record → do the slow thing → Stop. Look for long tasks.

### Memory leak hunter (JS)
DevTools → Memory tab → Heap snapshot → do suspicious thing → another snapshot → compare.

### Memory leak hunter (Python)
```bash
pip install memray
memray run server.py
memray flamegraph memray-*.bin
```

### Diff two spec maps
```bash
python -c "
import numpy as np; from PIL import Image
a = np.array(Image.open('spec_a.png'))
b = np.array(Image.open('spec_b.png'))
print('max diff:', np.abs(a.astype(int) - b.astype(int)).max())
print('channel diffs:', [(np.abs(a[:,:,i].astype(int) - b[:,:,i].astype(int))).max() for i in range(4)])
"
```

### Log HTTP traffic
In DevTools → Network tab. Filter to `localhost`. Inspect `/render` POST body and response.

---

## Reproducing Customer Bugs

When a user reports a bug:

1. Get their SPB version (Help → About).
2. Ask for their `.spb` file if they're willing to share.
3. Get the `last_render_request.json` if relevant.
4. Get a screenshot or screen recording.
5. Get any console errors (DevTools → Console → screenshot).
6. Get the server log tail (Help → Open Server Log).

Load their `.spb` in your local SPB to reproduce before hypothesizing.

---

## Server-Side Debugging Tricks

### Add a temporary endpoint

```python
# server.py
@app.route('/debug/dump_state', methods=['POST'])
def debug_dump_state():
    import json
    with open('_debug_state.json', 'w') as f:
        json.dump(request.json, f, indent=2)
    return 'ok'
```

Have the UI POST to `/debug/dump_state` instead of `/render` to capture state without rendering.

### Dump the spec map

In any finish's `spec()` function, add:

```python
from PIL import Image
Image.fromarray(spec_map).save(f'_debug_spec_{finish_name}.png')
```

Open the PNG in Photoshop to see what the engine produced.

---

## When All Else Fails

- Ask in Discord `#dev-chat` with a full repro.
- Email ricky@shokkergroup.com.
- Open a GitHub issue with every diagnostic you've gathered.
- Step through in the Python debugger:
  ```bash
  python -m pdb server.py
  ```

Remember: most SPB bugs reduce to the 3-copy sync rule, a missing `PATTERN_REGISTRY` entry, or an inverted spec map channel. Check those three first.

---

## See Also

- [DEVELOPMENT.md](DEVELOPMENT.md)
- [PERFORMANCE.md](PERFORMANCE.md) — when the bug is "it's slow"
- [TESTING.md](TESTING.md)
- [../SPB_TROUBLESHOOTING.md](../SPB_TROUBLESHOOTING.md) — user-side troubleshooting
