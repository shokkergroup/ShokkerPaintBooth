# HARDMODE autonomous worklog

## Iteration log

| time | finish | metric | before | after | test |
|---|---|---|---|---|---|
| 2026-04-20 07:52 | enh_wet_look | dR/dCC @seed=42 shape=256² | dR=3 dCC=2 | dR=22 dCC=12 | test_enh_wet_look_has_visible_flow_out_variation |
| 2026-04-20 08:06 | enh_ceramic_glaze | dR/dCC @seed=42 shape=256² | dR=5 dCC=3 | dR=25 dCC=14 | test_enh_ceramic_glaze_has_visible_pooling |
| 2026-04-20 08:14 | enh_gel_coat | dR/dCC @seed=42 shape=256² | dR=3 dCC=2 | dR=20 dCC=11 | test_enh_gel_coat_has_visible_flow_variation |
| 2026-04-20 08:20 | enh_baked_enamel | dR/dCC @seed=42 shape=256² | dR=5 dCC=5 | dR=19 dCC=14 | test_enh_baked_enamel_has_kiln_fired_depth |
| 2026-04-20 08:28 | neon_pink_blaze | dM/dR/dCC @seed=42 shape=256² | dM=13 dR=4 dCC=0 | dM=30 dR=30 dCC=25 | test_neon_pink_blaze_pulse_visible_in_spec |
| 2026-04-20 08:33 | neon_blacklight | dM/dR/dCC @seed=42 shape=256² | dM=11 dR=2 dCC=0 | dM=35 dR=28 dCC=20 | test_neon_blacklight_uv_response_visible_in_spec |
| 2026-04-20 08:42 | neon_dual_glow | dM/dR/dCC @seed=42 shape=256² | dM=2 dR=4 dCC=0 | dM=35 dR=30 dCC=24 | test_neon_dual_glow_split_visible_in_spec |
| 2026-04-20 08:45 | neon_ice_white | dM/dR/dCC @seed=42 shape=256² | dM=7 dR=5 dCC=0 | dM=30 dR=25 dCC=18 | test_neon_ice_white_dendrite_visible_in_spec |
| 2026-04-20 08:54 | neon_toxic_green | dM/dR/dCC @seed=42 shape=256² | dM=10 dR=5 dCC=0 | dM=35 dR=25 dCC=18 | test_neon_toxic_green_hotspots_visible_in_spec |
| 2026-04-20 08:58 | neon_rainbow_tube | dM/dR/dCC @seed=42 shape=256² | dM=10 dR=5 dCC=0 | dM=35 dR=25 dCC=20 | test_neon_rainbow_tube_bands_visible_in_spec |
| 2026-04-20 09:08 | neon_red_alert | dM/dR/dCC @seed=42 shape=256² | dM=12 dR=5 dCC=0 | dM=35 dR=25 dCC=18 | test_neon_red_alert_siren_visible_in_spec |
| 2026-04-20 09:11 | neon_electric_blue | dM/dR/dCC @seed=42 shape=256² | dM=15 dR=3 dCC=0 | dM=38 dR=28 dCC=18 | test_neon_electric_blue_veins_visible_in_spec |
| 2026-04-20 09:20 | neon_orange_hazard | dM/dR/dCC @seed=42 shape=256² | dM=15 dR=5 dCC=0 | dM=45 dR=30 dCC=25 | test_neon_orange_hazard_stripes_visible_in_spec |
| 2026-04-20 09:24 | neon_cyber_yellow | dM/dR/dCC @seed=42 shape=256² | dM=15 dR=4 dCC=0 | dM=40 dR=28 dCC=20 | test_neon_cyber_yellow_circuit_visible_in_spec |
| 2026-04-20 09:33 | anime_sakura_scatter | dM/dR/dCC @seed=42 shape=256² | dM=60 dR=20 dCC=8 | dM=130 dR=40 dCC=20 | test_anime_sakura_scatter_petals_visible_in_spec |
| 2026-04-20 09:37 | anime_comic_halftone | dM/dR/dCC @seed=42 shape=256² | dM=80 dR=50 dCC=20 | dM=170 dR=90 dCC=40 | test_anime_comic_halftone_ink_visible_in_spec |
| 2026-04-20 09:46 | beetle_rainbow | dM/dR/dCC @seed=42 shape=256² | dM=50 dR=15 dCC=8 | dM=130 dR=30 dCC=20 | test_beetle_rainbow_iridescence_visible_in_spec |
| 2026-04-20 09:50 | butterfly_monarch | dM/dR/dCC @seed=42 shape=256² | dM=55 dR=130 dCC=75 | dM=180 dR=130 dCC=75 | test_butterfly_monarch_wing_contrast_visible |
| 2026-04-20 09:59 | wasp_warning | dM/dR/dCC @seed=42 shape=256² | dM=60 dR=50 dCC=30 | dM=210 dR=70 dCC=47 | test_wasp_warning_band_contrast_visible |
| 2026-04-20 10:03 | moth_luna | dM/dR/dCC @seed=42 shape=256² | dM=80 dR=40 dCC=30 | dM=180 dR=130 dCC=74 | test_moth_luna_eye_spots_visible |
| 2026-04-20 10:12 | butterfly_morpho | dR/dCC @seed=42 shape=256² | dR=15 dCC=10 | dR=50 dCC=22 | test_butterfly_morpho_roughness_contrast_visible |
| 2026-04-20 10:16 | scarab_gold | dR/dCC @seed=42 shape=256² | dR=19 dCC=12 | dR=53 dCC=24 | test_scarab_gold_shell_contrast_visible |
| 2026-04-20 10:25 | enh_gloss | dR/dCC @seed=42 shape=256² | dR=7 dCC=3 | dR=25 dCC=12 | test_enh_gloss_has_wet_ripple_variation |
| 2026-04-20 10:30 | f_candy | dR @seed=42 shape=256² | REJECTED: noise_R key unused by _spec_foundation_flat (hardcoded ±2). Would need a dedicated spec_fn; defer. | — | — |
| 2026-04-20 10:39 | enh_piano_black | dR/dCC @seed=42 shape=256² | dR=10 dCC=2 | dR=29 dCC=14 | test_enh_piano_black_has_mirror_depth_variation |
| 2026-04-20 10:52 | enh_soft_gloss | dR/dCC @seed=42 shape=256² | dR=12 dCC=6 | dR=50 dCC=17 | test_enh_soft_gloss_has_shimmer_variation |
| 2026-04-20 11:05 | enh_semi_gloss | dR/dCC @seed=42 shape=256² | dR=16 dCC=8 | dR=52 dCC=28 | test_enh_semi_gloss_has_surface_nuance |
| 2026-04-20 11:18 | enh_carbon_fiber | dCC @seed=42 shape=256² | dCC=4 | dCC=18 | test_enh_carbon_fiber_resin_pool_visible |
| 2026-04-20 11:30 | enh_pearl | dCC @seed=42 shape=256² | dCC=4 | dCC=16 | test_enh_pearl_nacre_cc_visible |
| 2026-04-20 11:43 | enh_metallic | dCC @seed=42 shape=256² | dCC=4 | dCC=14 | test_enh_metallic_flake_depth_visible |
