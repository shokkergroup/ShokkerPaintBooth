"""SPB-105 v2 tick 8: eleven independent frozen-liquid/coating constructions."""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def dew_lenses(s):
    # SPB-105 tick19: circular Voronoi bowls/Obsidian1.0 -> pending; M7 pending. Wind-pinned drop triplets.
    u,v,gx,gy=s.cell(31,32);t=s.rand(gx,gy,967);drift=2.5*(t-.5)
    lens=np.zeros_like(u);rim=np.zeros_like(u);depth=np.zeros_like(u)
    for dx,dy,radius in ((-7,-6,7.8),(7,5,6.2),(-7,10,4.2)):
        x=u-dx-drift;y=v-dy;r=np.hypot(x*(1+.033*y),y*.82)
        body=sat(radius-r);lens=np.maximum(lens,body);rim+=edge(r-radius+1,1.8);depth=np.maximum(depth,body*sat((x+radius)/(2*radius)))
    s.mark('convex_dew_lenses',lens,(12,234),(0,216),(16,248),depth,rough_shade=1-depth,coat_shade=t)
    s.mark('pinned_contact_rims',rim,(132,254),(0,94),(0,108),1-t)
    s.mark('coalescence_necks',line(u,v,-4,-1,4,3,2.8)*lens,(46,202),(92,230),(126,252),t)
    s.mark('dry_dust_islands',disk(u-11,v+11,4.2),(0,96),(182,255),(172,255),1-t)
    s.mark('satellite_bead_collars',ring(u+10,v-10,4.2,1.6)+line(u,v,-8,-11,-7,-15,2),(94,226),(24,110),(56,208),t)

def capillary_rivulets(s):
    # Tick 18: identical wavy rows -> branching three-way liquid junctions with unequal wetting lobes.
    u,v,gx,gy=s.cell(31,29);t=s.rand(gx,gy,883);a=t*6.283;u+=8*(t-.5);v+=8*(s.rand(gx,gy,887)-.5)
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a);stem=edge(cu-2*np.sin(cv*.18),2.7)*box(cu,cv,12,12)
    arms=line(cu,cv,0,0,-11,-7,2.4)+line(cu,cv,1,2,11,8,2.1)
    s.mark('branching_wet_channels',stem+arms,(18,244),(24,214),(24,248),sat((cv+13)/26),coat_shade=t)
    s.mark('asymmetric_wetting_lobes',disk(cu+8,cv+5,4.8)+disk(cu-7,cv-6,4.2),(146,255),(16,108),(0,112),1-t)
    s.mark('receded_channel_edges',edge(cu-2*np.sin(cv*.18)-3.7,1.4)*box(cu,cv,12,12),(0,100),(180,255),(146,254),t)
    s.mark('junction_reservoir_pits',disk(cu,cv,4.1),(56,206),(102,232),(68,210),1-t)
    s.mark('detached_capillary_beads',disk(cu-10,cv-10,4.1)*sat((t-.25)*3),(96,228),(54,184),(164,255),sat((cu+13)/26))

def marangoni_fans(s):
    u,v,gx,gy=s.cell(32,30,.5);t=s.rand(gx,gy,271);r=np.hypot(u,v+8);a=np.arctan2(v+8,u);fan=disk(u,v+8,19)*box(u,v,14,12)*sat((v+8)/3)
    s.mark('fan_flow_lobes',fan,(18,246),(24,210),(20,248),sat(.5+.5*np.sin(a*8+r*.18)),coat_shade=t)
    s.mark('flow_separatrices',edge(np.sin(a*4),.18)*fan,(142,255),(16,112),(0,110),1-t)
    s.mark('source_meniscus',ring(u,v+8,4.5,1.8),(0,96),(174,255),(144,252),t)
    s.mark('deposit_fan_fronts',edge(r-16,2)*fan,(50,202),(108,236),(74,206),t)
    s.mark('bead_pinning_clusters',disk(u-11,v-10,4)+disk(u+10,v-8,4),(92,224),(42,178),(164,255),1-t)

def drying_fronts(s):
    u,v,gx,gy=s.cell(32,28);t=s.rand(gx,gy,277);front=v+4*np.sin(u*.17+t*2);island=box(u,front,14,9)
    s.mark('wet_remnant_bands',island,(14,236),(20,198),(20,244),sat((front+9)/18),coat_shade=t)
    s.mark('receding_front_lips',edge(front-7,1.9)*box(u,v,14,12),(142,255),(16,114),(0,108),1-t)
    s.mark('dried_residue_islands',box(u+7,front+7,5,4),(0,102),(180,255),(156,254),t)
    s.mark('arrested_drop_tails',line(u,v,5,0,12,10,2),(54,208),(96,230),(76,212),1-t)
    s.mark('contact_line_beads',disk(u-9,v+6,4.3),(98,226),(36,154),(152,252),t)

def foam_raft(s):
    u,v,wall,t=voronoi(s,24);r=np.hypot(u,v)
    s.mark('bubble_film_faces',sat((wall-1)/3),(16,242),(24,214),(16,250),sat(r/13),coat_shade=t)
    s.mark('plateau_borders',edge(wall,2.5),(148,255),(16,112),(0,112),1-t)
    s.mark('thinning_film_windows',disk(u,v,4.3),(0,106),(174,255),(142,254),t)
    s.mark('drainage_necks',line(u,v,-9,-3,-2,2,2),(56,204),(98,232),(66,198),t)
    s.mark('burst_film_tabs',box(u-8,v-8,4,4),(94,228),(52,180),(166,255),1-t)

def fisheye_crater(s):
    # SPB-105 tick23: single circular cavity .592 -> pending; M7 pending. Coalesced off-center dewetting defects with a displaced rim.
    u,v,gx,gy=s.cell(25,31,.5);t=s.rand(gx,gy,1279);cu=u+2*np.sin(v*.19+t*3);r=np.hypot(cu,v+3);q=np.hypot((cu-4)*1.2,v-7)
    slope=sat(11-r)+sat(6-q);rim=edge(r-10,2.1)*(1-sat(6-q))+edge(q-5,1.8)
    s.mark('dewetting_crater_slopes',slope,(18,246),(0,246),(24,248),sat(np.minimum(r/11,q/6)),rough_shade=sat((v+15)/30),coat_shade=t)
    s.mark('raised_coating_rings',rim,(146,255),(0,92),(0,114),1-t)
    s.mark('contaminant_cores',disk(cu+3,v+4,4.2),(0,98),(180,255),(146,254),t)
    s.mark('radial_coat_tears',line(cu,v,-7,-5,-11,-10,2)+line(cu,v,6,6,11,11,2),(56,204),(102,232),(68,204),t)
    s.mark('residue_splashes',sat(6-abs(cu+9)-abs(v-11)),(96,228),(54,180),(164,255),1-t)

def orange_peel_film(s):
    u,v,wall,t=voronoi(s,23);r=np.hypot(u,v);bump=np.exp(-(u*u+v*v)/70)
    s.mark('coating_hillocks',disk(u,v,12),(16,240),(26,218),(24,248),bump,coat_shade=t)
    s.mark('valley_polish_arcs',edge(r-9,2.4)*sat((u+4)/3),(134,255),(16,106),(0,110),1-t)
    s.mark('solvent_pop_pores',disk(u+4,v+3,4),(0,102),(180,255),(148,254),t)
    s.mark('flow_leveling_saddles',line(u,v,-9,-4,-1,3,2.1),(54,204),(102,230),(68,206),t)
    s.mark('dust_nib_collars',ring(u-8,v-7,4.1,1.5),(98,228),(56,180),(162,255),1-t)

def spray_coalescence(s):
    # SPB-105 tick22: identical three discs / Salt .699 -> pending; M7 pending. Unequal splash lobes join a raised wet neck.
    u,v,gx,gy=s.cell(27,31,.5);t=s.rand(gx,gy,1153);a=t*6.283;r=np.hypot(u,v);theta=np.arctan2(v,u)
    rim=8+2*np.sin(theta*3+a)+1.3*np.cos(theta*5-a);island=sat(rim-r);depth=sat(r/rim)
    s.mark('merged_spray_islands',island,(18,244),(0,246),(20,248),depth,rough_shade=sat(.5+.5*np.sin(theta+a)),coat_shade=t)
    s.mark('scalloped_island_edges',edge(r-rim+1,1.9),(146,255),(0,94),(0,110),1-t)
    s.mark('three_drop_junctions',line(u,v,-5,-3,4,5,2.6)*island,(0,104),(176,255),(142,254),t)
    s.mark('satellite_mist_drops',disk(u-10,v-11,4.1)+disk(u+10,v-10,4.1),(52,202),(94,228),(68,200),t)
    s.mark('dry_spray_necks',line(u,v,-6,7,1,13,2.4),(94,226),(52,176),(164,255),1-t)

def varnish_lace(s):
    # SPB-105 v2 tick 15: continuous ruptured film replaces checker-like islands.
    x,y=s.x,s.y;lace=np.sin(x*.21+1.1*np.sin(y*.13))+np.cos(y*.24+.8*np.sin(x*.17))
    t=sat(.5+.5*np.sin(x*.113+y*.179));u,v,gx,gy=s.cell(23,27,.5)
    s.mark('varnish_lace_webs',edge(lace,.7),(18,246),(24,214),(24,248),sat(lace+.5),coat_shade=t)
    s.mark('thickened_web_junctions',edge(lace,.9)*edge(np.cos(x*.21)*np.sin(y*.24),.25),(142,255),(16,108),(0,114),1-t)
    s.mark('broken_film_apertures',sat((abs(lace)-.8)*3),(0,98),(178,255),(146,254),t)
    s.mark('edge_curl_tabs',edge(lace-.8,.18)*sat(np.sin(x*.31+y*.22)*3),(56,204),(102,232),(70,204),t)
    s.mark('dust_trapped_beads',disk(u-6*s.rand(gx,gy,307),v,4)*edge(lace,1.1),(98,230),(54,180),(162,255),1-t)

def rheology_combs(s):
    u,v,gx,gy=s.cell(30,32);t=s.rand(gx,gy,311);finger=edge(u+5*np.sin(v*.12),3.8)*box(u,v,13,14)
    s.mark('viscous_fingers',finger,(18,246),(24,214),(22,248),sat((v+16)/32),coat_shade=t)
    s.mark('finger_tip_caps',disk(u+5,v-10,4.4),(144,255),(16,108),(0,110),1-t)
    s.mark('trailing_furrows',line(u,v,-9,-10,-7,12,2.2),(0,98),(178,255),(146,254),t)
    s.mark('side_comb_teeth',line(u,v,-2,-4,9,-7,1.7)+line(u,v,-1,5,11,2,1.7),(58,204),(104,234),(68,206),t)
    s.mark('recoil_meniscus_loops',ring(u-8,v+10,4.4,1.6),(96,228),(54,180),(164,255),1-t)

def ink_reticulation(s):
    # SPB-105 tick19: Voronoi network/Polar .94 -> pending; M7 pending.
    # Short reaction/diffusion growth creates a connected film maze, with pigment collecting on its banks.
    import cv2
    rng=np.random.default_rng(s.seed+977);b=rng.random((1024,1024),dtype=np.float32)*.3;a=np.ones_like(b)
    for _ in range(42):
        la=cv2.Laplacian(a,cv2.CV_32F);lb=cv2.Laplacian(b,cv2.CV_32F);reaction=a*b*b
        a=np.clip(a+.19*la-reaction+.051*(1-a),0,1);b=np.clip(b+.095*lb+reaction-(.051+.062)*b,0,1)
    b=b-cv2.GaussianBlur(b,(0,0),4);field=cv2.resize(b,(s.w,s.h),interpolation=cv2.INTER_CUBIC);lo,hi=np.percentile(field,[4,96]);q=sat((field-lo)/max(float(hi-lo),1e-4))
    gx=cv2.Sobel(q,cv2.CV_32F,1,0);gy=cv2.Sobel(q,cv2.CV_32F,0,1);slope=sat(np.hypot(gx,gy)*2.7)
    banks=sat((q-.25)*3);network=edge(q-.5,.18);u,v,ix,iy=s.cell(19,23,.5);t=s.rand(ix,iy,983)
    s.mark('reticulated_film_banks',banks,(18,242),(0,242),(24,248),q,rough_shade=1-slope,coat_shade=sat(.5+gx))
    s.mark('rupture_network',network,(142,255),(0,94),(0,114),slope)
    s.mark('retained_ink_pools',sat((q-.76)*5),(0,102),(176,255),(144,254),1-q)
    s.mark('short_drying_feathers',edge(q-.3,.07)*sat(abs(gy)-abs(gx)),(58,206),(100,232),(68,204),sat(.5+gy))
    s.mark('pigment_aggregate_islets',disk(u,v,4.2)*sat((q-.38)*4),(98,230),(54,178),(164,255),t)
