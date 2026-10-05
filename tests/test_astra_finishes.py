"""ASTRA contract, renderer boundary and identity-detector regression tests."""
import numpy as np
import pytest
from engine.expansions.astra import MODULES,ALL_MODULES,EXPANSION_MODULES,install
from engine.expansions.astra.common import clear_cache,pair
from scripts.spb_finish_identity import contract_from_module
from scripts.spb_iridescent_insects_similarity_gate import _identity_similarity

def test_ten_distinct_contracts_and_non_destructive_registration():
    registry={'existing':object()}; original=registry['existing']
    assert install(registry)==50
    assert registry['existing'] is original
    for attr in ('FID',): assert len({getattr(m,attr) for m in MODULES})==10
    contracts=[contract_from_module(m,m.FID) for m in MODULES]
    for key in ('construction_key','spec_key'):
        assert len({c[key] for c in contracts})==10
    assert all(len(c['mark_types'])>=5 for c in contracts)

def test_expansion_contracts_and_lane_counts():
    from collections import Counter
    assert len({m.FID for m in ALL_MODULES})==50
    assert Counter(m.LANE for m in EXPANSION_MODULES)=={'COLOR SHOXX':10,'SURFS UP':10,'MAD SCIENTIST':10,'FUTURE SHOXX':10}
    contracts=[contract_from_module(m,m.FID) for m in ALL_MODULES]
    for key in ('construction_key','spec_key'):
        assert len({c[key] for c in contracts})==50

def test_pair_seed_mask_non_square_and_cache_isolation():
    m=MODULES[0]; clear_cache()
    p,s=pair(m,(96,160),42)
    assert p.shape==s.shape==(96,160,3)
    assert np.isfinite(p).all() and np.isfinite(s).all()
    assert 0<=p.min()<=p.max()<=1
    assert s[...,1:].min()>=16 and s.max()<=255
    p2,s2=pair(m,(96,160),42)
    assert p2 is p and s2 is s
    assert not p.flags.writeable and not s.flags.writeable
    original=np.full_like(p,.4); zero=np.zeros(p.shape[:2],np.float32)
    assert np.array_equal(m.paint(original,p.shape[:2],zero,42),original)
    one=np.ones(p.shape[:2],np.float32)
    assert np.allclose(m.paint(original,p.shape[:2],one,42),p)
    assert np.allclose(m.paint(original,p.shape[:2],one,42,0),original)
    spec=m.spec(p.shape[:2],42)
    spec[0][:]=0
    assert np.array_equal(pair(m,p.shape[:2],42)[1],s)
    other,_=pair(m,p.shape[:2],43)
    # Engine material and colour-source calls use different job-seed salts.
    # A fixed authored finish must remain the same across all those calls.
    assert np.array_equal(other,p)
    clear_cache()

def test_detector_rejects_channel_rotation_and_phase_copies():
    # Deliberate positive controls prove transforms cannot turn a copy into
    # a new design. Fixed sampled native evidence, not a decorative generator.
    import cv2
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    original=cv2.imread(str(root/'thumbnails/picker_split/base/astra_quasicrystal_crown.png'))
    assert original is not None,'Bake real picker evidence before running ASTRA release tests'
    source=cv2.resize(original[:,:original.shape[1]//2],(128,128))
    for copied in (source[...,::-1],np.rot90(source),np.roll(source,17,axis=0)):
        result=_identity_similarity(source,copied.copy())
        # Use the actual ship rejection threshold. Phase filtering at image
        # borders can make an exact cyclic copy score below 1; it still rejects.
        assert max(result.direct,result.transformed,result.phased)>=.68
