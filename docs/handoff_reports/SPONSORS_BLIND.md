# SPONSORS-BLIND (2026-10-03, logo mode, B01-B17 of 30; B18-B30 not done: hard stop 18:15)

```
kind sponsors | truth spon | don't-care = truth under numbers
id   paint                         tru_px places mine_px    IoU recall   prec   hit lenrec   leak  cap cand notes
B01  burke_toyota_truck_2023_psd    14481     10   28402   0.00   0.01   0.00  1/10      -   1.00    0    2  retried
B02  monster_ram_v4_psd             12413      9   33350   0.20   0.62   0.23  3/9       -   0.77    0    3 
B03  james_smith_next_gen_chevy_v   38001     25   25939   0.62   0.65   0.95  6/25      -   0.00    0    0 
B04  am_mod_psd                     36485     11   38408   0.78   0.90   0.85  7/11      -   0.15    0    0 
B05  spb_fractured_truck_psd        36839     14   13174   0.24   0.27   0.74  1/14      -   0.26    0    0 
B06  lunar_survey_v009_3_layer_si   16133     11   13782   0.64   0.72   0.84  9/11      -   0.16    0    0 
B07  burke_f150_2023_v2_psd         15157      9   35766   0.05   0.16   0.07  3/9       -   0.93    0    2 
B08  angelica_vigilante_truck_che    7336      9   23422   0.04   0.17   0.05  0/9       -   0.95    0    0 
B09  dlm_consume_marshmallow_psd    71600     11   66542   0.70   0.79   0.85  8/11      -   0.15    0    0 
B10  biohazard                      30209      8   28820   0.05   0.09   0.10  2/8       -   0.90    0    1 
B11  86_dirt_big_block_modified_r   14560     17   11047   0.47   0.56   0.74 10/17      -   0.26    0    3 
B12  rhrbull_psd                    44028     28   32910   0.28   0.38   0.51  4/28      -   0.49    0    2 
B13  signal_lost_v009_3_layer_sim   15419      8   12013   0.59   0.66   0.85  7/8       -   0.15    0    1 
B14  bed_ncs_chevroletzl1_1le_202    6308      9    4447   0.15   0.23   0.32  3/9       -   0.68    0    2 
B15  arca_2023_dr_psd               30987      8   15231   0.14   0.19   0.38  0/8       -   0.62    0    0 
B16  reaper_blueprint_v011_3_laye   12930      8   15143   0.75   0.93   0.79  7/8       -   0.21    0    1 
B17  future_flip_v009_3_layer_sim    6721      7   12874   0.52   1.00   0.52  7/7       -   0.48    0    0 

WITH sponsors in the truth (17 paints): mean IoU 0.366 | mean recall 0.489 | mean precision 0.518 | places found 78/202 (39%) | paints IoU>=0.5: 7/17 | length recall - | body leak mean 0.479 max 0.997 | capped boxes 0 | candidates offered 17 | declared "none" wrongly: 0
```

Boxes per paint: 7-10 (read off look_at_paint app_guess:false sheets), mode logo (default for kind sponsors), lettering:true never used. Bridge was killed 3x by another lane's closepages; B01 and B04 were re-marked after a restart (B04 first pass skipped). score ran twice (once mid-way by mistake).
