# Catalog ID Rename Migration Template

**When you need this:** any time you rename a finish ID in BASES /
PATTERNS / MONOLITHICS / SPEC_PATTERNS. Saved zone configs / autosaves
/ presets persist raw IDs to disk; a rename without a migration entry
silently corrupts every prior save.

**Cost saved:** without this template, each rename is ~30-60 min of
research + risk. With this template, a rename is ~5-10 min.

---

## The recipe

### Step 1 — pick the rename

Decide which side of the collision keeps the canonical ID. Convention:
the ENTRY SHIPPED FIRST keeps the canonical ID; the duplicate gets a
namespace prefix or suffix.

| Collision class | Convention |
|---|---|
| BASE × PATTERN | PATTERN entry → `<id>_pattern` |
| PATTERN × MONOLITHIC | MONOLITHIC entry → `<id>_mono` |
| SPEC_PATTERN × MONOLITHIC | SPEC entry → `spec_<id>` |
| Intra-registry duplicate | second entry → `<id>_classic` (or specific suffix) |

### Step 2 — edit the entry definition

Find the line in `paint-booth-0-finish-data.js`:

```js
{ id: "old_id", name: "Old Name", desc: "...", swatch: "..." },
```

Add the rename comment + change the ID:

```js
// 2026-MM-DD HEENAN <WIN> — `old_id` collided with <REGISTRY> at L###.
// <CLASS>-tier entry renamed; HP-MIGRATE handles backward compat.
{ id: "new_id", name: "New Name (Type)", desc: "...", swatch: "..." },
```

### Step 3 — update group references

Search for `"old_id"` in every `*_GROUPS` constant. Update each that
points at the renamed registry tier (NOT the canonical-tier groups).

```bash
grep -nE '"old_id"' paint-booth-0-finish-data.js
```

For each match in a group that maps to your renamed registry, update
the group entry inline. Add a one-line comment explaining the rename.

### Step 4 — add migration entry

In `paint-booth-2-state-zones.js`, locate `_SPB_LEGACY_ID_MIGRATIONS`
and add the entry under the correct field-type scope:

```js
const _SPB_LEGACY_ID_MIGRATIONS = Object.freeze({
    monolithic: Object.freeze({
        // ... existing entries ...
        'old_id': 'new_id',  // <WIN> — <one-line reason>
    }),
    pattern: Object.freeze({ /* ... */ }),
    specPattern: Object.freeze({ /* ... */ }),
});
```

**Field-type scope rules:**
- `monolithic` — applies to `z.finish` field
- `pattern` — applies to `z.pattern` and `patternStack[].id`
- `specPattern` — applies to `specPatternStack[].id` + 4 overlay stacks

### Step 5 — add metadata alias

In `paint-booth-0-finish-metadata.js`, copy the `FINISH_METADATA["old_id"]`
entry as a new alias under `new_id` so the renamed finish surfaces in
the same browser tab with the same sort priority. Place inside the
`HP-METADATA` block at the bottom (or add a new dated block).

```js
"new_id": {                       // <WIN> — was `old_id`
    "family": "...",
    "browserGroup": "...",
    "browserSection": "...",
    "hero": false,
    "featured": false,
    "advanced": false,
    "utility": false,
    "readability": ...,
    "distinctness": ...,
    "sortPriority": ...,
    "score": ...
},
```

### Step 6 — sync 3 copies

```bash
cp paint-booth-0-finish-data.js electron-app/server/paint-booth-0-finish-data.js
cp paint-booth-0-finish-data.js electron-app/server/pyserver/_internal/paint-booth-0-finish-data.js
cp paint-booth-0-finish-metadata.js electron-app/server/paint-booth-0-finish-metadata.js
cp paint-booth-0-finish-metadata.js electron-app/server/pyserver/_internal/paint-booth-0-finish-metadata.js
cp paint-booth-2-state-zones.js electron-app/server/paint-booth-2-state-zones.js
cp paint-booth-2-state-zones.js electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js
```

### Step 7 — extend the migration ratchet

Edit `tests/_runtime_harness/legacy_id_migration.mjs` and add the
old-id to the `preRenameZone` test fixture under the appropriate field.
Edit `tests/test_runtime_legacy_id_migration.py` to bump the
`change_count` assertion if the new fixture entries change the total.

### Step 8 — verify

```bash
node --check paint-booth-0-finish-data.js
node tests/_runtime_harness/registry_collisions.mjs   # collisions should reduce
node tests/_runtime_harness/validate_finish_data.mjs  # 0 problems
node tests/_runtime_harness/legacy_id_migration.mjs   # all migrations execute
python scripts/spb_golden_net.py --check             # golden net: 0 changed / 0 removed / 0 error
python -m pytest tests/ -q                            # all green
```

If any check fails, **do not sync to mirrors yet** — fix in canonical
first.

---

## Failure modes this prevents

1. **Saved-config corruption.** Without migration, `z.finish = 'old_id'`
   from a painter's prior project loads as undefined → engine renders
   nothing where they expected their finish.
2. **Picker hidden tile.** Without metadata alias, the renamed finish
   loses browser/search metadata and only shows in `all` mode.
3. **Group reference orphan.** If you forget Step 3, the validator
   surfaces `cross_registry_pattern_group` or `phantom` warnings.
4. **3-copy drift.** Without Step 6, the electron build picks up old
   IDs while dev runs new.

---

## Cumulative coverage

The migration map currently handles **13 legacy IDs** across HP1-HP4 +
HB2 + H4HR-1..H4HR-8 (see `_SPB_LEGACY_ID_MIGRATIONS` in
`paint-booth-2-state-zones.js`). Every entry is runtime-tested by
`tests/test_runtime_legacy_id_migration.py` (12 assertions).

Adding a 14th rename takes ~5-10 min if you follow this template
carefully. Adding it WITHOUT this template typically takes 30-60 min
plus a non-zero chance of leaving a saved-config corruption bug.

— Heenan Family, 2026-04-19
