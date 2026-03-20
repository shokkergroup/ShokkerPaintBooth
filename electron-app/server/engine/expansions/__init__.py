# =============================================================================
# engine/expansions/ - Consolidated expansion modules
# =============================================================================
# Purpose: Houses ALL expansion satellite files in one place.
#          Previously scattered as shokker_*.py in the project root.
# 
# Modules:
#   arsenal_24k         - 100+ patterns, bases, specials (formerly shokker_24k_expansion.py)
#   fusions             - 150 FUSIONS hybrid materials    (formerly shokker_fusions_expansion.py)
#   paradigm            - Paradigm impossible materials   (formerly shokker_paradigm_expansion.py)
#   specials_overhaul   - Dark/Gothic, Effects, Shokk     (formerly shokker_specials_overhaul.py)
#   color_monolithics   - 260+ color-changing finishes    (formerly shokker_color_monolithics.py)
#
# Each module exposes an integrate_*() function that merges its registries
# into the parent engine module (shokker_engine_v2.py).
#
# Import pattern (from shokker_engine_v2.py or server.py):
#   from engine.expansions import arsenal_24k, paradigm, fusions, ...
# =============================================================================

from engine.expansions import arsenal_24k
from engine.expansions import fusions
from engine.expansions import paradigm
from engine.expansions import specials_overhaul
from engine.expansions import color_monolithics
from engine.expansions import color_clash

__all__ = [
    "arsenal_24k",
    "fusions",
    "paradigm",
    "specials_overhaul",
    "color_monolithics",
    "color_clash",
]
