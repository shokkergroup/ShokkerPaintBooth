# SPB PSD Template Catalog

This folder contains **metadata** describing PSD (Photoshop Document) templates that Shokker Paint Booth (SPB) recognizes. The folder does NOT contain actual `.psd` files. Instead, it stores JSON files that describe the layer structure, safe areas, number panel positions, and sponsor-friendly UV regions of each template, so SPB can act intelligently on a template even before the heavy `.psd` is loaded into memory.

## What this folder is for

When a livery designer drops a PSD into SPB, the engine needs to answer questions like:

- Which layer holds the base paint?
- Where do driver number panels live in UV space?
- Which areas of the body are paintable vs masked?
- Where is the TV panel / windshield banner / contingency row?
- What zones make sense to suggest as defaults?

Loading a 100+ MB PSD just to answer these questions is wasteful. Storing a pre-computed metadata JSON next to the PSD lets SPB:

1. Show a thumbnail catalog of available templates without parsing any binary data.
2. Auto-suggest zone layouts when a template is selected.
3. Validate that custom user PSDs match the expected layer convention.
4. Surface warnings ("this PSD is missing the Class Lights layer — your livery will fail iRacing checks").
5. Pre-position sponsor placeholders during quick-design / AI-suggested liveries.

## How templates interact with SPB

```
   User picks a vehicle in SPB UI
                  |
                  v
   SPB looks up template metadata in /psd_templates/<id>.json
                  |
                  v
   Metadata returns: canvas size, layer tree, safe areas, recommended zones
                  |
                  v
   SPB pre-builds zone defaults + sponsor slots BEFORE loading the PSD
                  |
                  v
   When user clicks "Load PSD", SPB parses only the layers that match
   the metadata's expected layer_tree (fast path)
```

If the user supplies a custom PSD that does NOT have a metadata entry, SPB falls back to layer auto-discovery: it scans for layer names matching common conventions (`Car_Paint`, `Numbers`, `Sponsors`, etc.) and surfaces a warning if expected layers are missing.

## File structure

```
psd_templates/
  README.md                      <- this file
  catalog.json                   <- master index of all templates
  chevy_silverado_2019.json      <- per-template metadata
  toyota_tundra_2022.json
  ford_f150_2021.json
  generic_gt3.json
  generic_lmp.json
  generic_stock_car.json
```

The `catalog.json` file lists every known template with quick-lookup fields (id, name, category, canvas size, top-level layers, file pointer to the per-template JSON). Per-template JSONs hold the deep layer tree, UV-space safe areas, and zone recipes.

## JSON schema reference

### catalog.json

```jsonc
{
  "version": "6.2.0",            // SPB version this catalog was built for
  "schema_version": "1.0.0",     // metadata schema version
  "templates": [                 // array of template summaries
    {
      "id": "string",            // unique snake_case identifier
      "name": "string",          // human display name
      "category": "string",      // grouping (NASCAR Truck, GT3 Sportscar, etc.)
      "canvas_size": [w, h],     // pixel dimensions, typically [2048, 2048]
      "standard_layers": [],     // expected top-level layer names
      "recommended_zones": int,  // suggested zone count for SPB UI
      "safe_areas": [],          // human-readable list of paintable regions
      "iracing_folder": "path",  // where this PSD lives in the iRacing tree
      "metadata_file": "path",   // pointer to the per-template JSON
      "notes": "string"          // free-form designer notes
    }
  ]
}
```

### Per-template JSON

```jsonc
{
  "id": "string",
  "name": "string",
  "canvas_size": [w, h],
  "color_space": "sRGB",
  "alpha_required": true,
  "iracing_folder": "path",
  "schema_version": "1.0.0",

  "layer_tree": [                // expected layers in this PSD
    {
      "name": "string",
      "type": "raster|mask|smart_object|group",
      "purpose": "what this layer does",
      "default_visibility": true,
      "export_visibility": true,
      "children": [],            // for groups
      "locked": false            // optional
    }
  ],

  "uv_safe_areas": [             // paintable / sponsor-friendly regions
    {
      "name": "string",
      "bbox_uv": [u_min, v_min, u_max, v_max],  // 0..1 UV space
      "use": "intended purpose"
    }
  ],

  "number_panels": [             // driver number locations
    {"id": "string", "bbox_uv": [...], "shape": "rectangle|circle"}
  ],

  "windshield_banner": {
    "bbox_uv": [...],
    "max_chars": int,
    "default_height_px": int
  },

  "recommended_zones": [         // SPB zone defaults for first-run experience
    {
      "id": "string",
      "label": "string",
      "default_finish": "finish_name from FINISH_REGISTRY",
      "default_color": "#RRGGBB"
    }
  ],

  "warnings": ["string"],        // things designers commonly get wrong
  "tips": ["string"]             // designer-facing best practices
}
```

UV coordinates use **0..1 space with origin top-left** to match Photoshop and SPB's canvas convention (note: this is opposite of standard OpenGL UV, which has origin bottom-left).

## How to add your own template metadata

1. Open the PSD in Photoshop, identify all top-level layers and groups.
2. Copy `generic_stock_car.json` as a starting template and rename to `<your_id>.json`.
3. Fill in the `layer_tree` to exactly match the PSD's actual layer names.
4. Use Photoshop's ruler set to "Percent" to estimate UV bbox values for safe areas.
5. Pick 3-5 logical zones for `recommended_zones` (hood, doors, roof, etc.).
6. Add an entry to `catalog.json` with summary fields + a pointer to your file.
7. Restart SPB or call the catalog reload endpoint to pick up the new template.

When in doubt, mimic the closest existing template — the seven baselines here cover NASCAR Trucks, NASCAR Cup, GT3, and LMP, which together share a lot of structure.

## Contribution guide

If you build a high-quality template metadata file for a vehicle the community uses often, please open a PR:

- Validate JSON with `python -m json.tool < your_template.json`.
- Verify your `id` is unique against `catalog.json`.
- Use realistic UV coordinates — measure from the actual PSD if possible, otherwise approximate from a similar vehicle.
- Keep `warnings` and `tips` concise (one sentence each, max 5-7 entries).
- Match the existing layer_tree structure (groups before flat layers, `Wire` first, `Turn Off Before Exporting TGA` last).
- Add the file to `catalog.json` with all required fields.

For questions or template requests, reach out to ricky@shokkergroup.com or open an issue on the SPB repo.

## See also

- `../SPB_PSD_TEMPLATE_GUIDE.md` — full guide to creating SPB-compatible PSDs.
- `../SPB_SPONSOR_GUIDELINES.md` — sponsor placement best practices by car type.
- `../README.md` (root) — main SPB documentation.
- `../CHANGELOG.md` — see v6.2.0 entry for catalog system introduction.
