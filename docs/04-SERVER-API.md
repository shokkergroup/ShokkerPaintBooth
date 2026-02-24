# Shokker Paint Booth — Server API Reference (server.py)

## Overview

Flask server running on `http://localhost:5000`. Serves the frontend HTML and exposes REST endpoints for rendering, configuration, and file management. ~1,417 lines.

## Starting the Server

```
cd "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"
C:\Python313\python.exe server.py
```

Or via PowerShell with output capture:
```powershell
Start-Process -FilePath "C:\Python313\python.exe" -ArgumentList "server.py" -WorkingDirectory "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine" -RedirectStandardOutput "stdout.log" -RedirectStandardError "stderr.log"
```

## Endpoints

### GET /
Serves `paint-booth-v2.html` — the entire frontend.

### GET /status
Health check and server info.

**Response:**
```json
{
  "status": "online",
  "version": "2.0.0-alpha",
  "engine": "shokker_engine_v2",
  "license": { "valid": true, "key": "SHOKKER-XXXX-XXXX-XXXX", "tier": "alpha" }
}
```

Used by `ShokkerAPI.startPolling()` every 10 seconds to keep the status dot green.

### POST /render
Main render endpoint. Takes full zone configuration, produces spec map + paint files.

**Request Body (JSON):**
```json
{
  "car_paint": "path/to/car_paint.tga",
  "output_dir": "path/to/output/",
  "iracing_id": "car_001",
  "seed": 42,
  "zones": [
    {
      "name": "Body Color",
      "color": "#FF0000",
      "colors": ["#FF0000", "#CC0000"],
      "tolerance": 30,
      "base": "gloss",
      "pattern": "carbon_fiber",
      "patternStack": [
        { "id": "carbon_fiber", "opacity": 1.0, "scale": 1.0, "rotation": 0 }
      ],
      "monolithic": null,
      "intensity": "medium",
      "customIntensity": { "spec_mult": 1.0, "paint_mult": 0.6, "bright_mult": 0.5 },
      "wear": 0,
      "regionMask": "base64-encoded-RLE-data",
      "muted": false
    }
  ],
  "extras": {
    "export_zip": true,
    "dual_spec": false,
    "helmet_file": null,
    "suit_file": null,
    "wear_global": 0,
    "recolor_rules": [
      { "source": "#FF0000", "target": "#0000FF", "tolerance": 30 }
    ],
    "recolor_mask": "base64-RLE",
    "import_spec_map": null
  }
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "uuid-string",
  "files": {
    "spec_map": "output/car_001_spec.tga",
    "paint": "output/car_001.tga",
    "preview_spec": "output/car_001_spec_preview.png",
    "preview_paint": "output/car_001_preview.png",
    "night_spec": "output/car_001_night_spec.tga",
    "zip": "output/car_001_bundle.zip"
  },
  "render_time": 12.5
}
```

**Note:** License gate on this endpoint is commented out (~line 532) for Alpha.

### POST /preview-render
Lightweight preview render at reduced resolution.

**Request Body:** Same structure as /render but typically fewer zones and lower detail.

**Response:** Preview image paths for split-view display.

### GET /license
Returns current license status.

**Response:**
```json
{
  "valid": false,
  "key": null,
  "tier": null,
  "message": "No license activated"
}
```

### POST /license
Activate a license key.

**Request Body:**
```json
{ "key": "SHOKKER-XXXX-XXXX-XXXX" }
```

### POST /license/deactivate
Deactivate current license.

### GET /finish-groups
Returns the grouped finish data for the UI tabs.

**Response:**
```json
{
  "bases": { "Classic": ["gloss", "matte", ...], "Metallic": [...], ... },
  "patterns": { "Weaves": [...], "Geometric": [...], ... },
  "monolithics": { "Color-Shift": [...], ... }
}
```

### GET /swatch/{base}/{pattern}
Generates a composited swatch preview image.

**Parameters:**
- `base` — Base ID (e.g., "gloss")
- `pattern` — Pattern ID (e.g., "carbon_fiber")

**Response:** PNG image (64×64 swatch)

### GET /swatch/mono/{id}
Generates a monolithic finish swatch.

**Parameters:**
- `id` — Monolithic ID (e.g., "chameleon_v2")

**Response:** PNG image

### GET /config
Returns saved server-side configuration.

### POST /config
Saves configuration to server.

**Request Body:** Full config JSON (same structure as client-side getConfig())

### GET /iracing-cars
Lists available car folders in the iRacing paint directory.

**Response:**
```json
{
  "cars": [
    { "id": "car_001", "name": "Mazda MX-5", "path": "C:/Users/.../iRacing/paint/car_001" }
  ]
}
```

### POST /deploy-to-iracing
Copies rendered files to the iRacing paint folder.

**Request Body:**
```json
{
  "job_id": "uuid",
  "car_id": "car_001"
}
```

### POST /cleanup
Removes old render job files from temp directory.

### POST /check-file
Checks if a file exists at a given path.

**Request Body:**
```json
{ "path": "E:/some/file.tga" }
```

### POST /browse-files
Opens a file browser dialog and returns selected path.

**Request Body:**
```json
{ "type": "paint" }  // or "spec", "output", "helmet", "suit"
```

### GET /preview-tga
Converts a TGA file to PNG for browser preview.

**Query Params:** `path=E:/some/file.tga`

### POST /upload-composited-paint
Uploads a pre-composited paint file for use in rendering.

### POST /upload-spec-map
Uploads an external spec map for import/merge.

### POST /reset-backup
Restores original paint file from backup.

### GET /preview/{job_id}/{filename}
Serves preview images from a render job.

### GET /download/{job_id}/{filename}
Serves downloadable files from a render job.

### POST /apply-finish
Applies a finish to a specific zone and returns preview data.

## Recolor System (Server-Side)

The `apply_paint_recolor()` function in the server handles HSV-based paint recoloring:

1. Receives recolor rules (source hex → target hex + tolerance)
2. Optionally receives a spatial mask (RLE-encoded Uint8Array)
3. For each pixel in the paint TGA:
   - Convert to HSV
   - Check if within tolerance of any source color
   - If match: shift H/S/V toward target
   - If spatial mask exists: only apply where mask = 255
4. Write modified paint TGA

## Error Handling

All endpoints return JSON with `success` boolean:
```json
{ "success": false, "error": "Description of what went wrong" }
```

Common errors:
- File not found (paint TGA doesn't exist)
- Invalid zone configuration
- Engine crash during render (caught and returned as error message)
- License invalid (when gate is enabled)

## CORS & Security

- No CORS headers (localhost only)
- No authentication beyond license system
- No rate limiting
- Designed for single-user local operation only
