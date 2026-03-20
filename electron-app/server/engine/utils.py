"""
Engine utilities: re-exports from engine.core for legacy callers.
shokker_engine_v2 imports TGA/noise/grid from here to avoid circular imports.
Single implementation lives in engine/core.py.
"""
from engine.core import (
    write_tga_32bit,
    write_tga_24bit,
    get_mgrid,
    generate_perlin_noise_2d,
    perlin_multi_octave,
)

__all__ = [
    "write_tga_32bit",
    "write_tga_24bit",
    "get_mgrid",
    "generate_perlin_noise_2d",
    "perlin_multi_octave",
]
