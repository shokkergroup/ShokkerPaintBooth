"""
Registry patch for Chrome & Mirror category.
Maps base_id -> new paint_fn name.

Used by import_staged.py to update BASE_REGISTRY in base_registry_data.py
"""

REGISTRY_PATCH = {
    "chrome":           "paint_chrome_mirror",
    "black_chrome":     "paint_black_chrome_v2",
    "blue_chrome":      "paint_blue_chrome_v2",
    "red_chrome":       "paint_red_chrome_v2",
    "satin_chrome":     "paint_satin_chrome_v2",
    "antique_chrome":   "paint_antique_chrome_v2",
    "bullseye_chrome":  "paint_bullseye_chrome_v2",
    "checkered_chrome": "paint_checkered_chrome_v2",
    "dark_chrome":      "paint_dark_chrome_v2",
    "vintage_chrome":   "paint_vintage_chrome_v2",
}


SPEC_PATCH = {
    "chrome": "spec_chrome_mirror",
    "black_chrome": "spec_black_chrome",
    "blue_chrome": "spec_blue_chrome",
    "red_chrome": "spec_red_chrome",
    "satin_chrome": "spec_satin_chrome",
    "antique_chrome": "spec_antique_chrome",
    "bullseye_chrome": "spec_bullseye_chrome",
    "checkered_chrome": "spec_checkered_chrome",
    "dark_chrome": "spec_dark_chrome",
    "vintage_chrome": "spec_vintage_chrome",
}
