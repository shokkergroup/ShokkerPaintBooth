#!/usr/bin/env bash
# Bake pattern thumbnails so the front-end shows the EXACT engine output for each pattern.
# Run from repo root or V5 folder. Creates thumbnails/pattern/<id>.png for every pattern.
cd "$(dirname "$0")/.."
echo "Baking pattern thumbnails (exact engine output)..."
python rebuild_thumbnails.py --type pattern
echo "Done. Check thumbnails/pattern/*.png"
