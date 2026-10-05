# FRACTURED HOUDINI H1 — Track Capture Protocol

Status: staging gate for `houdini_veiled_skull` I33 P17. This is a capture
checklist, not acceptance evidence by itself.

## Fixed setup

Use one car, one paint file, one track position, one camera position, and one
zoom for every image in a set. Apply the current H1 card from the
live-development catalog before entering the session. Keep at least 80% of the
side and both curved fenders visible. Do not alter paint, spec strength,
exposure, livery, camera, zoom, or position between captures—only let track
lighting or an actual light angle change.

## Required images

1. Neutral daylight / non-grazing baseline: premium filigree material, no
   readable skull graphic.
2. Same place under a hard track-light reflection: chrome/crown fragments may
   rise while satin wells recede.
3. Same place with a materially different light angle or night condition:
   different eye/cheek/tooth fragments should trade places rather than simply
   become uniformly brighter.
4. Same place after the reflection moves away: the relief should recede back
   into the carrier. This fourth frame is required for an acceptance decision.

Each frame must show the same side/curved regions. Save unedited PNG captures
with a shared H1 prefix and clear light suffix, for example `h1_neutral`,
`h1_chrome`, `h1_satin`, `h1_recede`.

After the set is saved, run:

```powershell
C:\Python313\python.exe scripts\spb_houdini_track_capture_audit.py <capture-folder>
```

The audit checks identical frame dimensions, approximate scene alignment, and
lighting deltas. It is capture hygiene only; it cannot make an accept decision.

## Keep decision

The neutral frame must read as complete black-chrome cobalt/plum filigree
without a painted skull. Across the matched lighting frames, small recurring
skull-and-filigree reliefs must emerge, recede, and reorganize only through
material states. Reject if the neutral carrier looks like wallpaper/noise, the
motif is a paint/decal read, every fragment brightens identically, or the
effect depends on changing camera/paint instead of lighting.

## Existing offline evidence

`_houdini_proof/houdini_veiled_skull_native_material_audit_current.png`,
`_houdini_proof/houdini_veiled_skull_neutral_grazing_material_sim_not_track.png`,
and `_houdini_proof/houdini_veiled_skull_material_angle_suite_not_track.png`
are diagnostics only. They do not replace these actual matched captures.
