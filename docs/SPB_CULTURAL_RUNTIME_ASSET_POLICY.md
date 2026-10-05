# SPB Cultural Runtime Asset Policy

Union Jacked, Rising Sun, and Viva Mexico use image-authored cultural paint plates.
The app should load optimized runtime derivatives, not the oversized authoring PNG
masters.

## Runtime folders

Runtime assets live under:

- `assets/reference_textures/cultural/union_jacked`
- `assets/reference_textures/cultural/rising_sun`
- `assets/reference_textures/cultural/viva_mexico`

Each runtime folder should contain:

- `manifest.json`
- `jpg_2048/`

The renderer prefers `jpg_2048/{finish_id}.jpg` and
`jpg_2048/{finish_id}_spec.jpg` when present. Set `SPB_CULTURAL_USE_JPG=0` to
force PNG fallback during local debugging, if PNG fallback files have been
restored.

`electron-app/copy-server-assets.js` copies these slim cultural runtime packs by
default even when bulky `reference_textures` are excluded. `SPB_INCLUDE_REFERENCE_TEXTURES=1`
is reserved for dev/full-reference builds.

## Archived masters

Large PNG authoring/source material is intentionally isolated under:

`_dev_asset_masters/reference_textures/cultural/`

That folder is ignored by git and is not copied by the Electron packaging path.
Keep it for future rebakes, but do not point runtime loaders or runtime-sync at
it.

## Rebake

Run this after changing source PNG plates:

```powershell
python scripts/bake_cultural_jpg_runtime.py union_jacked rising_sun viva_mexico
```

The baker writes 2048x2048 JPG derivatives at quality 92, 4:4:4 chroma.
