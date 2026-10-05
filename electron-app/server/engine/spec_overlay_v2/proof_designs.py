"""Twelve independently constructed proof surfaces, SPB-105 v2 tick 2.

Identity contracts live in designs/<id>.py before scoring. No function here
selects a common carrier by palette, seed or phase. Each owns five named marks
and different feature/material relationships. Metrics: first candidate -> gate
pending; record iterations in docs/SPEC_OVERLAYS_V2_2026-09-06.md.
"""
import numpy as np
from .geometry import sat,edge,disk,box,ring,line,voronoi

def toolpath_reversal(s):
    u,v,gx,gy=s.cell(32,24,.5);t=s.rand(gx,gy,1);rad=np.hypot(u,v+8)
    cut=edge(rad-15,2.4)*sat((v+3)/3);land=box(u,v,14,9)*(1-cut)
    s.mark('overlap_lands',land,(82,240),(0,255),(35,210),t,rough_shade=sat((v+6)/12))
    s.mark('cut_segments',cut,(180,255),(16,74),(26,160),sat((u+16)/32),coat_shade=t)
    s.mark('entry_crescents',ring(u+7,v+5,5,1.5)*sat(-u/3),(24,154),(108,228),(130,250),t)
    s.mark('exit_scallops',edge(np.hypot(u-8,v-4)-5,1.6)*sat(u/3),(110,236),(24,156),(16,220),sat((v+8)/16))
    s.mark('compact_burrs',disk(u-11,v+7,4)*sat((t-.35)*4),(8,118),(160,248),(110,245),1-t)

def braided_junction(s):
    u,v,gx,gy=s.cell(32,32);t=s.rand(gx,gy,2);cross=np.mod(gx+gy,2)
    a=box(u,v,14,5);b=box(u,v,5,14);under=a*(1-cross)+b*cross;over=b*(1-cross)+a*cross
    s.mark('underpassing_bundles',under,(24,134),(110,228),(16,252),t,coat_shade=1-t)
    s.mark('resin_pockets',disk(u-10,v-10,5)+disk(u+10,v+10,5),(4,86),(18,80),(16,94),sat((u+v+32)/64))
    s.mark('overpassing_bundles',over,(130,246),(22,116),(16,252),sat((u-v+32)/64),rough_shade=t,coat_shade=t)
    s.mark('stitch_collars',ring(u,v,9,1.5)*sat((abs(u)-3)/3),(64,202),(68,196),(32,220),1-t)
    s.mark('loose_fiber_ends',line(u,v,-13,-10,-6,-4,1.2)+line(u,v,6,4,13,10,1.2),(110,254),(24,68),(24,250),t)

def crystal_front(s):
    u,v,gx,gy=s.cell(30,30,.5);t=s.rand(gx,gy,3);d=np.maximum(abs(u)*.9,abs(v));terrace=np.mod(d+3*t,4.5)/4.5
    body=box(u,v,13,13)
    s.mark('growth_terraces',body,(24,250),(26,232),(24,238),terrace,rough_shade=1-terrace,coat_shade=t)
    s.mark('twin_seams',line(u,v,-12,12,12,-12,1.6),(138,244),(110,228),(16,115),sat((u+15)/30))
    s.mark('nuclei',disk(u,v,4.4),(6,92),(32,116),(130,255),t)
    s.mark('interstitial_pockets',box(u-12,v+12,4,4),(5,80),(178,248),(76,218),1-t)
    s.mark('chipped_tips',box(u+11,v-11,4,4)*sat((u+v+3)/4),(122,248),(52,180),(0,64),t)

def denticle_armor(s):
    u,v,gx,gy=s.cell(26,30,.5);t=s.rand(gx,gy,4);shield=sat(np.minimum(12-v,9+v-abs(u)*1.1))
    s.mark('individual_plates',shield,(40,196),(44,182),(42,226),sat((v+12)/24),coat_shade=t)
    keel=edge(u-2*np.sin(v*.25),1.6)*box(u,v,7,10)
    s.mark('split_keels',keel+line(u,v,0,0,7,9,1.3),(182,255),(16,92),(16,108),t)
    s.mark('root_collars',ring(u,v-10,5.5,1.5)*sat((12-v)/3),(18,134),(138,238),(114,252),1-t)
    s.mark('abrasion_patches',box(u+5,v+1,4,5)*sat((t-.2)*5),(108,234),(90,224),(0,54),t)
    s.mark('between_plate_pores',disk(u-10,v+11,4),(4,64),(172,248),(42,172),1-t)

def tidal_meniscus(s):
    u,v,gx,gy=s.cell(30,28,.5);t=s.rand(gx,gy,5);r=np.hypot(u*.85,v);wet=disk(u*.85,v,10.5)
    s.mark('receding_islands',wet,(25,126),(18,104),(16,246),sat((u+12)/24),coat_shade=t)
    s.mark('contact_line_arcs',edge(r-10.5,1.7)*sat((v+9)/4),(100,212),(28,166),(32,224),1-t)
    s.mark('residue_rings',edge(r-13.5,1.3)*sat((-v+5)/5),(6,104),(150,250),(146,252),sat((u+15)/30))
    s.mark('pinning_points',disk(u-9,v-5,4.2),(124,252),(72,208),(70,240),t)
    s.mark('bead_clusters',disk(u+11,v+9,4)+disk(u-9,v+11,4),(60,208),(16,58),(16,68),sat((v+14)/28))

def crazed_porcelain(s):
    # SPB-105 tick21: Coral similarity .878 -> pending; M7 pending. Owner: unique fine construction.
    # A warped quadrilateral glaze fracture network, with secondary cracks arrested inside each platelet.
    x=s.x+3.1*np.sin(s.y*.37)+1.7*np.sin(s.x*.31+s.y*.17);y=s.y+3.8*np.sin(s.x*.29)-1.4*np.cos(s.y*.43)
    u=np.mod(x,23)-11.5;v=np.mod(y,21)-10.5;gx=np.floor(x/23);gy=np.floor(y/21);t=s.rand(gx,gy,1021)
    fracture=np.minimum(11.5-abs(u),10.5-abs(v));lip=edge(fracture-3,2.8)
    s.mark('glaze_lips',lip,(8,94),(0,190),(0,252),sat((u+11)/22),rough_shade=t,coat_shade=1-t)
    s.mark('primary_fissures',edge(fracture,2),(90,214),(134,250),(140,250),t)
    s.mark('secondary_checks',line(u,v,-10,-3,3,3,1.8)+line(u,v,3,3,5,9,1.6),(8,144),(176,242),(68,190),1-t)
    s.mark('pore_clusters',disk(u-5,v+5,4.1)*sat((t-.3)*3),(20,126),(116,226),(96,224),t)
    s.mark('exposed_chips',sat(7-abs(u+8)-abs(v-8)),(168,254),(0,116),(0,70),sat((u+11)/22))

def paired_facet_lattice(s):
    u,v,gx,gy=s.cell(28,28);t=s.rand(gx,gy,7);diamond=sat(13-abs(u)-abs(v));face=(u>0)
    s.mark('alternating_platelets',diamond,(22,242),(25,196),(24,250),face.astype(float),rough_shade=1-t,coat_shade=1-face)
    s.mark('bevel_bands',edge(abs(u)+abs(v)-12,1.8),(90,224),(36,162),(35,190),sat((v+14)/28))
    s.mark('junction_knots',disk(u,v,4.3),(8,116),(156,252),(112,232),t)
    s.mark('etched_notches',line(u,v,-8,-3,-2,-9,1.5)*diamond,(34,174),(92,240),(164,255),1-t)
    s.mark('polished_tips',disk(u-10,v,4)*diamond,(174,255),(16,48),(0,54),t)

def security_guilloche(s):
    # SPB-105 v2 tick 18: isolated medallions rejected; two interlaced engraving passes.
    u,v,gx,gy=s.cell(27,31,.5,angle=11);t=s.rand(gx,gy,809)
    r1=np.hypot(u+5,v);r2=np.hypot(u-5,v);arcs=(edge(r1-9,1.8)+edge(r2-9,1.8))*box(u,v,12,13)
    p,q,hx,hy=s.cell(23,29,.5,angle=-33);w=s.rand(hx,hy,811);r3=np.hypot(p,q+3)
    s.mark('interlaced_arclets',arcs,(16,246),(24,226),(24,248),sat((v+14)/28),coat_shade=t)
    s.mark('crossover_saddles',edge(r3-8,2.1)*sat(q/3),(148,255),(16,106),(0,112),w)
    s.mark('recessed_knots',disk(u,v,4.2)*sat(arcs+.35),(0,100),(180,255),(144,254),1-t)
    s.mark('beaded_borders',disk(p-8,q+8,4.1)+disk(p+7,q-8,4.1),(58,210),(102,234),(70,212),1-w)
    s.mark('burnished_crests',edge(r2-7,1.1)*sat(v/3),(100,230),(50,184),(162,255),sat((u+13)/26))

def pit_lane_ghost(s):
    # Tick 18: generic micro checker -> service-box corners and staggered lane markings.
    u,v,gx,gy=s.cell(29,31,.5,angle=7);t=s.rand(gx,gy,827);u+=5*(t-.5)
    bay=line(u,v,-10,-11,-10,10,2)+line(u,v,-10,10,6,10,2)+line(u,v,6,10,6,3,2)
    p,q,hx,hy=s.cell(19,23,.5,angle=-14);w=s.rand(hx,hy,829)
    s.mark('service_box_corners',bay,(20,240),(28,218),(24,248),sat((v+14)/28),coat_shade=t)
    s.mark('staggered_tick_clusters',line(p,q,-6,-8,4,-8,2.8),(148,255),(16,108),(0,114),w)
    s.mark('corner_tabs',box(u-6,v+8,4,4)*(1-bay),(0,100),(180,255),(146,254),1-t)
    s.mark('wear_scuffs',line(u,v,-4,-7,5,1,1.5)+line(p,q,-5,3,6,8,1.3),(56,206),(102,230),(68,212),1-w)
    s.mark('polished_witness_dots',disk(p-7,q-7,4.1)*sat((w-.4)*4),(98,228),(54,184),(164,255),sat((p+10)/20))

def aperiodic_alloy(s):
    # Beatty-sequence displacements vary tile widths/joins nonperiodically.
    x=s.x+7*np.floor(s.x/31/1.61803398875);y=s.y+5*np.floor(s.y/29/1.41421356237)
    u=np.mod(x+y*.37,29)-14.5;v=np.mod(y-x*.23,27)-13.5
    gx=np.floor(x/29);gy=np.floor(y/27);t=s.rand(gx,gy,10)
    tile=sat(13-np.maximum(abs(u),abs(v)))*sat(19-abs(u)-abs(v))
    s.mark('unequal_small_tiles',tile,(24,224),(24,220),(22,248),sat((u+v+28)/56),coat_shade=t)
    s.mark('multiway_junctions',ring(u,v,6,1.7)*sat((u+v+5)/6),(154,254),(66,176),(0,106),1-t)
    s.mark('inset_windows',box(u+3,v-2,4.2,5.3),(8,112),(150,242),(96,246),t)
    s.mark('interrupted_bridges',line(u,v,-12,7,2,9,1.4)*sat((t-.15)*5),(114,250),(16,72),(42,184),sat((u+14)/28))
    s.mark('corner_scars',line(u,v,7,-11,12,-5,1.5),(34,164),(102,228),(162,250),1-t)

def diatom_sieve(s):
    # SPB-105 tick23: round sieve .610 -> pending; M7 pending. Bilateral pennate frustules with axial raphe and striae.
    u,v,gx,gy=s.cell(27,31,.5);t=s.rand(gx,gy,1259);a=(t-.5)*.9;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    r=np.hypot(cu*1.4,cv*.85);valve=sat(12-r);rim=edge(r-11,2.5)
    s.mark('valve_rims',rim,(16,246),(0,246),(24,248),sat((cv+14)/28),rough_shade=sat((cu+10)/20),coat_shade=t)
    s.mark('radial_struts',edge(np.mod(cv+15,7)-3.5,2)*valve,(146,255),(0,92),(0,114),1-t)
    pores=(disk(cu-5,np.mod(cv+15,9)-4.5,4)+disk(cu+5,np.mod(cv+15,9)-4.5,4))*valve
    s.mark('perforation_rows',pores,(0,98),(180,255),(146,254),t)
    s.mark('bridge_ribs',edge(cu,2.5)*valve,(56,204),(102,232),(68,204),sat((cv+14)/28))
    s.mark('scar_plugs',disk(cu,cv-11,4.1)+disk(cu,cv+11,4.1),(96,228),(54,180),(164,255),1-t)

def weld_pool_archive(s):
    # SPB-105 tick27 / owner independent construction: continuous seam vs knit .652 -> pending; M7 99.27 -> pending. Three-way tack-weld junctions.
    u,v,gx,gy=s.cell(31,31,.5);t=s.rand(gx,gy,1543);pool=np.zeros_like(u+v);arcs=np.zeros_like(pool);toes=np.zeros_like(pool);shade=np.zeros_like(pool)
    for ax,ay,bx,by in ((-11,-7,9,-7),(8,-7,8,11),(-11,-7,-11,8)):
        for k in range(3):
            x=u-(ax+(bx-ax)*k/2);y=v-(ay+(by-ay)*k/2);r=np.hypot(x,y);bead=sat(5.3-r)
            pool=np.maximum(pool,bead);arcs+=edge(r-3.6,1.6)*sat((x+y+3)/3);toes+=edge(r-5.6,1.5);shade=np.maximum(shade,bead*(.15+.34*k))
    s.mark('solidification_crescents',pool,(24,250),(0,246),(24,248),shade,rough_shade=sat((v+15)/30),coat_shade=t)
    s.mark('overlap_saddles',arcs*pool,(152,255),(0,88),(0,114),1-t)
    s.mark('edge_toes',toes*(1-pool),(0,100),(180,255),(146,254),sat((u+15)/30))
    s.mark('spatter_clusters',disk(u,v-7,4.2)+disk(u-11,v+12,4.1),(58,206),(102,232),(68,210),t)
    s.mark('polished_breaks',line(u,v,-5,-8,3,-6,1.9)+line(u,v,7,2,9,8,1.9),(98,228),(54,184),(164,255),1-t)
