PLACEHOLDER PATTERN IMAGES
==========================

This folder contains FALLBACK images only. These are used when the actual
user-supplied PNG is missing from assets/patterns/<category>/.

NEVER OVERWRITE USER FILES
--------------------------
- User PNGs live in: assets/patterns/<category>/ (e.g. musicinspired/, 50s/, etc.)
- This folder (_placeholders/) is for programmatic fallbacks only
- The engine loads the USER path first; only if missing does it try _placeholders/
- Agent/automation must NEVER write to user category folders — only to _placeholders/
- When adding a new pattern, put the real HQ file in the category folder;
  put any generated 64x64 test image HERE with a _placeholder.png suffix

Convention: <pattern_id>_placeholder.png (e.g. smilexx_pure_placeholder.png)
