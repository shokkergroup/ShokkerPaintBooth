# Actual-game material investigation — 18 September 2026

The daytime test has demonstrated localized spectral edge flashes on the owner's ARCA Chevrolet in iRacing. This is a mechanism calibration, not an accepted catalog finish or proof that twenty replacements are complete.

## Reproducible settings

- Replay: `ARCAChevy2026TexasAfternoonNight.rpy`, Texas Motor Speedway.
- Driver/UserID: 23371, car number 155, custom-number paint active.
- Camera: original Chase, position 4.63 / 8.82 / 3.01, rotation 0 / 0.10 / 0, FOV 36.34, exposure 0.
- Paint: fixed continuous spectral field, HSV saturation 0.995, maximum **120/255 in stored RGB**. This is much brighter than I3's approximately 18/255 maximum.
- Spec RGB: **255 / 40 / 218** (metalness / roughness / clearcoat channel).
- Maps: `controlled_maps/pigment_120_r40_c218/paint.tga` and `spec.tga`, native 2048 square.
- Generator: `build_controlled_maps.py`. Reference pixels are not used.

## Observed, not inferred

`DAYLIGHT_120_CLEAN.png` shows red, blue, green and violet along the front fender/door crease and window pillar while most body panels remain gray/taupe. `DAYLIGHT_120_PEAK.png` captures a much brighter band across the door and window surround. Other lap angles reduce these bands substantially. Paint/spec textures remain fixed. There is no animated shader or composited glow.

The40/80 daylight pigment tests were weaker in the observed views; the earlier18-value test was at night, not a matched daylight comparison. The earlier analytic model was not calibrated to the game's color/light response and its successful-looking low-pigment render was misleading. The neutral control and clearcoat-off test establish that the real rendering pipeline is responding to material changes, but these are not a complete BRDF characterization.

## Still to improve

- Faint rainbow coloration remains visible in some dark views; quiet-body balance needs refinement.
- Current Chase view demonstrates strong edge streaks; a reference-equivalent overhead hood flare and normal viewing-distance test remain required.
- These maps intentionally have a broad calibration field and constant material values. They are **not** identity-compliant finished assets. No M7, owner PASS, name-test pass, or final-count credit is claimed.
- Final construction must have original, name-true fine features and feature-bound spec states without losing the demonstrated spectral response to texture filtering.

## Direction for the replacement collection

Build the light response first. Fine features should modulate pigment strength and the width/intensity of the reflection without converting the body into always-visible rainbow wallpaper. Each of twenty designs needs its own construction and spec silhouette; palette substitutions do not count. Validate exported maps in the actual game, then update and rebake the matching SPB cards. Keep the existing R1 rejected designation until each replacement meets its actual-output gates.

## Preservation

The controlled lab backs up only the owner's three paint/spec files, checks concurrent edits, records recipe changes and restores exact source hashes. `USER_REPLAY_START.json` preserves the user's original replay position/camera. The first daylight test restored all three source files successfully before restarting the saved replay to activate native video recording. No external post or message has been sent.


## Recovery and sampled sequence checkpoint

Native recording caused the simulator to exit; no video was produced. Capture was returned to its original disabled setting. The same saved replay has recovered, all three owner material hashes match the original snapshots, and playback is paused at the closest available end frame115378 (original snapshot115438). Original Chase camera values were restored manually and verified visually. No camera file was overwritten.

`DAYLIGHT_REVIEW.html` contains18 unaltered sampled observations spanning72.464 seconds. They are discrete frames, not continuous video. After replay restart the saved Chase camera used position4.63/8.82/2.67, rotation0/0/0 and FOV41.22; that setup stayed fixed for the18-frame sequence. Earlier captures used the original camera described above. Exposure remained0. The review does not compare different poses as a quantitative brightness test.

The mechanism evidence is ready for inspection. The reference-equivalent overhead hood flare, finer quiet-body balance, distance checks and twenty distinct finished replacements remain outstanding. R1 rejection labels and source pixels remain unchanged.
