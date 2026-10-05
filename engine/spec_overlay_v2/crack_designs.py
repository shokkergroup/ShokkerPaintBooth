"""SPB-105 v2 tick 10: eleven fine weathering constructions, not recolors."""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def mud_crackle(s):
    # SPB-105 v2 tick 15: owner name-law; rejected checker -> curled polygon fragments.
    u,v,wall,t=voronoi(s,22);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    s.mark('dry_mud_platelets',sat(wall-1),(12,238),(38,226),(24,250),sat(wall/9),coat_shade=t)
    s.mark('shrinkage_fissures',edge(wall,2.2),(0,98),(176,255),(138,252),1-t)
    s.mark('curled_plate_edges',edge(wall-2.8,1.5)*sat((cu+3)/4),(150,255),(16,112),(0,114),sat((cv+12)/24))
    s.mark('secondary_dry_checks',line(cu,cv,-3,0,9,7,1.2)*sat(4-wall),(54,202),(100,234),(68,208),t)
    s.mark('crumbled_grit_pockets',disk(cu+5,cv-4,4)*sat((t-.48)*4),(96,224),(60,186),(168,255),1-t)

def wrinkled_lacquer(s):
    u,v,gx,gy=s.cell(32,30);t=s.rand(gx,gy,331);fold=u+4*np.sin(v*.28+t*3);ridged=sat(.5+.5*np.cos(fold*.6))
    s.mark('compressed_lacquer_ridges',box(u,v,14,13),(18,246),(22,218),(24,248),ridged,coat_shade=t)
    s.mark('fold_crest_splits',edge(fold-5,1.6)*box(u,v,12,12),(0,102),(174,255),(146,254),1-t)
    s.mark('polished_wrinkle_shoulders',line(u,v,-9,-10,-3,7,2),(148,255),(16,110),(0,114),t)
    s.mark('cross_fold_creases',line(u,v,1,4,11,9,1.8),(56,206),(100,230),(68,204),t)
    s.mark('trapped_coat_bubbles',ring(u-9,v+8,4.3,1.6),(98,228),(54,180),(164,255),1-t)

def corrosion_blisters(s):
    u,v,wall,t=voronoi(s,29);r=np.hypot(u,v);cap=sat(11-r)
    s.mark('lifted_blister_caps',cap,(16,240),(26,210),(24,248),sat((u+13)/26),coat_shade=t)
    s.mark('ruptured_radial_flaps',line(u,v,-9,-5,8,7,2.3)+line(u,v,0,0,-6,11,1.8),(142,255),(16,110),(0,114),1-t)
    s.mark('corrosion_halos',ring(u,v,12,1.9),(0,96),(182,255),(148,254),t)
    s.mark('exposed_core_windows',box(u+3,v-2,4,4),(52,204),(96,228),(66,204),t)
    s.mark('oxide_satellite_grains',disk(u-10,v-9,4.2),(96,226),(54,178),(164,255),1-t)

def spall_islands(s):
    u,v,gx,gy=s.cell(32,30,.5);t=s.rand(gx,gy,337);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a);flake=sat(12-abs(cu)-.55*abs(cv))
    s.mark('retained_coating_flakes',flake,(16,244),(26,216),(24,248),sat((cv+14)/28),coat_shade=t)
    s.mark('spalled_substrate_windows',sat(8-abs(cu-5)-abs(cv+5)),(148,255),(16,106),(0,114),1-t)
    s.mark('undercut_flake_edges',edge(abs(cu)+.55*abs(cv)-11,1.8),(0,102),(176,255),(142,254),t)
    s.mark('shear_bridge_filaments',line(cu,cv,-10,6,-1,11,1.7),(54,204),(102,232),(68,204),t)
    s.mark('detached_chip_triads',disk(cu+10,cv+9,4)+box(cu-10,cv-10,4,4),(98,228),(54,180),(164,255),1-t)

def stress_star_crazing(s):
    # SPB-105 tick19: shared cell substrate .973 -> pending; M7 pending. Offset impact pairs and forked cracks.
    u,v,gx,gy=s.cell(32,29,.5);t=s.rand(gx,gy,947);a=t*6.283
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    rays=line(cu,cv,-5,-3,-12,-11,2.2)+line(cu,cv,-5,-3,1,-13,2)+line(cu,cv,-5,-3,-13,9,2.3)
    rays+=line(cu,cv,6,5,13,12,2.1)+line(cu,cv,6,5,13,-6,2)+line(cu,cv,-5,-3,6,5,2.7)
    plate=sat(rays+.55*disk(cu+5,cv+3,8)+.55*disk(cu-6,cv-5,7))
    s.mark('stress_field_platelets',plate,(18,244),(0,240),(24,248),sat((cv+14)/28),coat_shade=t)
    s.mark('radial_star_fissures',rays,(0,96),(180,255),(146,254),1-t)
    s.mark('impact_center_chips',sat(6-abs(cu+5)-abs(cv+3))+sat(5-abs(cu-6)-abs(cv-5)),(150,255),(0,82),(0,110),t)
    s.mark('arrest_branch_segments',line(cu,cv,-9,-8,-13,-5,1.8)+line(cu,cv,10,9,7,13,1.8),(54,204),(100,230),(70,202),t)
    s.mark('fissure_tip_tabs',line(cu,cv,2,-11,7,-12,3)+line(cu,cv,-12,8,-8,12,3),(96,226),(56,184),(164,255),1-t)

def scuffed_enamel(s):
    u,v,gx,gy=s.cell(32,26);t=s.rand(gx,gy,353);a=t*.9-.45;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    s.mark('enamel_witness_pads',box(cu,cv,13,9),(16,238),(28,216),(24,248),sat((cv+9)/18),coat_shade=t)
    s.mark('abrasion_sweeps',line(cu,cv,-12,-6,10,1,2.2)+line(cu,cv,-10,1,8,7,1.8),(148,255),(16,106),(0,110),1-t)
    s.mark('embedded_road_grit',disk(cu+7,cv+7,4.3),(0,98),(180,255),(146,254),t)
    s.mark('chipped_scuff_starts',box(cu+10,cv+4,4,4),(54,204),(100,232),(66,204),t)
    s.mark('burnished_exit_hooks',ring(cu-8,cv-6,4.4,1.6)*sat((cu-5)/3),(98,228),(54,178),(164,255),1-t)

def freeze_thaw(s):
    u,v,gx,gy=s.cell(30,32,.5);t=s.rand(gx,gy,359);wedge=sat(13-abs(u)-abs(v)*.5);fracture=u+2*np.sin(v*.45)
    s.mark('frost_lifted_wedges',wedge,(18,242),(26,216),(24,248),sat((v+15)/30),coat_shade=t)
    s.mark('ice_jacking_splits',edge(fracture,2.2)*box(u,v,10,13),(0,102),(176,255),(142,254),1-t)
    s.mark('fresh_fracture_faces',line(u,v,-10,7,-2,12,2.6),(148,255),(16,108),(0,114),t)
    s.mark('stepped_frost_lenses',box(u-6,v+6,4,4),(56,204),(102,230),(70,204),t)
    s.mark('friable_grain_clusters',disk(u+10,v+11,4)+disk(u-10,v-10,4),(96,228),(54,182),(164,255),1-t)

def oxide_pitting(s):
    u,v,wall,t=voronoi(s,25);r=np.hypot(u*.9,v);a=np.arctan2(v,u)
    s.mark('oxidized_pit_slopes',disk(u*.9,v,10),(16,238),(26,214),(24,248),sat(r/10),coat_shade=t)
    s.mark('undercut_pit_lips',edge(r-9,2)*sat(np.cos(a+t)*3),(144,255),(16,108),(0,114),1-t)
    s.mark('deep_corrosion_pores',disk(u+3,v-2,4.3),(0,96),(182,255),(146,254),t)
    s.mark('oxide_growth_needles',line(u,v,-10,-6,-4,1,1.8)+line(u,v,5,3,11,9,1.6),(54,204),(102,232),(68,204),t)
    s.mark('passivated_bridge_islets',box(u-9,v-8,4,4),(98,226),(54,178),(164,255),1-t)

def creased_foil(s):
    # SPB-105 tick22: single folded pad .670 -> pending; M7 pending. Opposed crumple tents with converging crease networks.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1171);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    left=sat(11-abs(cu+4)-.6*abs(cv+4));right=sat(9-abs(cu-5)-.85*abs(cv-5));crease=abs(cv+4)-.6*abs(cu+4)
    s.mark('crumpled_foil_facets',left+right,(16,248),(0,246),(24,248),sat((crease+7)/14),rough_shade=sat((cu+13)/26),coat_shade=t)
    folds=line(cu,cv,-4,-4,-12,5,2)+line(cu,cv,-4,-4,4,-12,2)+line(cu,cv,-4,-4,5,5,2)+line(cu,cv,5,5,12,1,2)
    s.mark('fold_intersections',folds,(148,255),(0,92),(0,112),1-t)
    s.mark('fatigue_crease_splits',line(cu,cv,-8,-3,1,-7,2.1),(0,102),(178,255),(146,254),t)
    s.mark('pinched_corner_tabs',sat(6-abs(cu-9)-abs(cv-9)),(56,206),(102,232),(70,202),t)
    s.mark('crease_scuff_lozenges',sat(6-abs(cu+8)-abs(cv-9)),(96,228),(54,180),(164,255),1-t)

def alligator_coat(s):
    u,v,gx,gy=s.cell(26,30,.5);t=s.rand(gx,gy,373);edge_d=np.maximum(abs(v)*.7,abs(u)+.18*v);plate=sat(10-edge_d)
    s.mark('aged_coating_blocks',plate,(18,244),(26,216),(24,248),sat((u+11)/22),coat_shade=t)
    s.mark('deep_coat_channels',edge(edge_d-10,2.1),(0,98),(180,255),(146,254),1-t)
    s.mark('curled_block_shoulders',line(u,v,-8,-9,8,-6,2),(146,255),(16,108),(0,112),t)
    s.mark('secondary_cross_checks',line(u,v,-5,2,6,5,1.4),(56,204),(100,230),(68,204),t)
    s.mark('exposed_corner_chips',box(u-8,v-9,4.1,4.1),(98,228),(54,180),(164,255),1-t)

def micro_chipping(s):
    # SPB-105 tick23: one diamond crater .633 -> pending; M7 pending. Undercut impact crescents and detached sharp flake triplets.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1249);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    r=np.hypot(cu+2,cv+3);chip=disk(cu+2,cv+3,10)*(1-disk(cu-3,cv+1,7));flakes=sat(5-abs(cu-7)-abs(cv-8))+sat(5-abs(cu+8)-abs(cv-10))
    s.mark('stone_chip_craters',chip,(18,244),(0,246),(24,248),sat(r/10),rough_shade=sat((cv+14)/28),coat_shade=t)
    s.mark('bare_chip_centers',disk(cu+5,cv+4,4.2)*chip,(148,255),(0,94),(0,112),1-t)
    s.mark('fractured_enamel_rims',edge(r-9,1.9)*sat((cu+2)/3),(0,98),(180,255),(146,254),t)
    s.mark('impact_comet_scars',line(cu,cv,-7,-7,-12,-12,2.4),(56,204),(102,232),(70,204),t)
    s.mark('detached_paint_specks',flakes,(98,228),(54,180),(164,255),1-t)
