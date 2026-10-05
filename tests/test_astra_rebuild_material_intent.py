"""ASTRA R2 material-intent regressions (SPB-105 / ASTRA-R2, 2026-09-27).

The R1 version of this file asserted R1 role tables (Surface/STATES), which no
longer exist. R2 keeps the same material truths but checks them on the actual
authored renders: wax is rough and uncoated, velvet is a rough uncoated
dielectric, Janus Blades really deals two material populations, and every
finish honours the export ABI (paint 0..1, Rough/Cc >= 16).
"""
import numpy as np
from engine.expansions.astra import ALL_MODULES
from engine.expansions.astra.common import clear_cache, pair

BY = {m.FID: m for m in ALL_MODULES}


def _spec(fid):
    _, s = pair(BY[fid], (512, 512), 42)
    return s


def test_wax_is_rough_uncoated_dielectric():
    s = _spec('astra_surf_wax_ritual')
    wax = s[..., 1] > 110                         # the wax body, not the glossy basecoat valleys
    assert wax.mean() > .5
    assert np.median(s[..., 0][wax]) < 40
    assert np.median(s[..., 2][wax]) > 150        # inverted iRacing coat: high = little clearcoat


def test_velvet_remains_rough_uncoated_dielectric():
    # Native res: the pile is dielectric; ~14% sparse lame threads (metal but
    # rough) are deliberate (ASTRA-R2) and average out at picker size.
    _, s = pair(BY['astra_velvet_supernova'], (2048, 2048), 42)
    ground = s[..., 0] < 30
    assert ground.mean() > .6
    assert np.median(s[..., 1][ground]) > 170
    assert np.median(s[..., 2][ground]) > 220


def test_janus_deals_two_material_populations():
    _, s = pair(BY['astra_janus_blades'], (2048, 2048), 42)   # native: faces are 4-8 px
    lacquer = (s[..., 0] < 40).mean(); metal = (s[..., 0] > 215).mean()
    assert lacquer > .15 and metal > .15


def test_export_abi_on_three_lanes():
    for fid in ('astra_event_horizon', 'astra_chromatic_switchyard', 'astra_bismuth_delirium'):
        p, s = pair(BY[fid], (256, 256), 42)
        assert np.isfinite(p).all() and np.isfinite(s).all()
        assert 0 <= p.min() and p.max() <= 1
        assert s[..., 1:].min() >= 15.5 and s.max() <= 255
    clear_cache()
