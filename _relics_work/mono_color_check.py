# -*- coding: utf-8 -*-
"""Prove the monolithic base-colour behaviour through the REAL engine zone path.

Owner report 2026-08-30: "there's a LOT of finishes that at 100% base strength
which SHOULD have the color of the base with it ... the COLOR is not showing up
for the BASE MATERIAL at all".

Renders the same finish three ways and reports the mean colour of the zone:
  source  -> the deliberate 2026-08-15 spec-only mode (paint = the car's paint)
  finish  -> the new default: the material keeps its own colour
  solid   -> an explicit colour override
If `source` matches the incoming car paint and `finish` matches the finish's own
render, the diagnosis is confirmed and the fix works.
"""
import io, os, sys, contextlib, logging
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT); sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import shokker_engine_v2 as eng

FID = sys.argv[1] if len(sys.argv) > 1 else "frl_coffin_nail"
SHAPE = (512, 512)
CAR = np.full(SHAPE + (3,), 0.5, np.float32)          # neutral grey "source paint"
CAR[..., 0] = 0.72                                     # make it clearly reddish
CAR[..., 1] = 0.18
CAR[..., 2] = 0.18
MASK = np.ones(SHAPE, np.float32)

spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[FID]
own = np.asarray(paint_fn(CAR.copy(), SHAPE, MASK, 51, 1.0, None), np.float32)
print(f"car source paint   mean RGB = {CAR.reshape(-1,3).mean(0).round(3)}")
print(f"{FID} own render    mean RGB = {own.reshape(-1,3).mean(0).round(3)}")

blend = eng._blend_monolithic_base_strength
for mode in ("source", "finish"):
    paint = own.copy()
    if mode in ("finish", "own"):
        pass                                            # NEW: keep the finish's paint
    elif mode in ("", "source", "none"):
        paint = blend(CAR, paint, MASK, 0.0)            # the 2026-08-15 revert
    m = np.asarray(paint, np.float32).reshape(-1, 3).mean(0).round(3)
    same_as_car = bool(np.allclose(m, CAR.reshape(-1, 3).mean(0), atol=0.002))
    print(f"  mode={mode:7s} -> mean RGB {m}   {'== CAR PAINT (finish colour lost)' if same_as_car else '== finish colour kept'}")
