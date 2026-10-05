"""SPB-105 v2 tick 6: ten separate machining constructions, native 8-32px.
Identity contracts precede scoring; before/after evidence lives in the v2 log.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box

def crossed_hone(s):
    u,v,gx,gy=s.cell(28,24,.5);t=s.rand(gx,gy,41);a=line(u,v,-12,-9,11,8,2);b=line(u,v,-12,9,11,-8,1.4)
    s.mark('abrasive_lands',box(u,v,13,10),(24,178),(55,184),(36,224),t,coat_shade=sat((u+14)/28))
    s.mark('forward_grooves',a,(170,255),(10,96),(18,108),sat((u+14)/28),rough_shade=t)
    s.mark('return_grooves',b,(4,94),(160,253),(106,246),1-t)
    s.mark('crossing_burrs',disk(u-1,v,4.1),(92,225),(68,220),(0,190),t)
    s.mark('trapped_grit',box(u-10,v+7,4,4),(8,84),(186,255),(170,255),1-t)

def peen_crater_cluster(s):
    # SPB-105 tick22: one bowl / Rope .683 -> pending; M7 pending. Three overlapping unequal peen impacts.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1109);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    r1=np.hypot(cu+5,cv+5);r2=np.hypot(cu-6,cv);r3=np.hypot(cu+3,cv-8);bowls=sat(8-r1)+sat(6-r2)+sat(5-r3)
    lips=edge(r1-7,2.2)*(1-sat(6-r2))+edge(r2-5,1.8)+edge(r3-4,1.8)
    s.mark('impact_bowls',bowls,(8,178),(0,240),(24,240),sat(np.minimum.reduce([r1/8,r2/6,r3/5])),rough_shade=sat((cv+13)/26),coat_shade=t)
    s.mark('raised_crater_lips',lips,(182,255),(0,70),(0,146),sat((cu+14)/28))
    s.mark('secondary_strikes',disk(cu-9,cv-10,4.4),(36,156),(132,248),(130,252),t)
    s.mark('radial_tears',line(cu,cv,3,-3,11,-10,1.8)+line(cu,cv,-5,6,-12,10,1.8),(80,220),(52,198),(24,200),1-t)
    s.mark('flattened_crest',line(cu,cv,-9,0,-4,4,2.9)*bowls,(6,90),(180,255),(172,250),t)

def lapped_chevrons(s):
    # SPB-105 tick22: filled roof rows / Mica .689 -> pending; M7 pending. Two interrupted crossed lapping passes.
    u,v,gx,gy=s.cell(27,31,.5);t=s.rand(gx,gy,1117);r=v+abs(u)*.7;lap=edge(r,4.2)*sat(12-abs(u))
    p,q,hx,hy=s.cell(23,29,.5,angle=.73);w=s.rand(hx,hy,1123);second=edge(q-abs(p)*.65,2.8)*sat(10-abs(p))*sat((w-.25)*3)
    s.mark('lap_faces',lap+second,(14,252),(0,246),(34,226),sat((r+4)/8),rough_shade=sat((p+11)/22),coat_shade=t)
    s.mark('lapping_edges',edge(r-3,1.5)*sat(12-abs(u)),(112,246),(0,72),(0,104),1-t)
    s.mark('return_scrapes',line(p,q,-9,-7,-1,-11,2.1),(8,120),(130,253),(124,254),w)
    s.mark('keystone_pits',sat(6-abs(u)-abs(v+1)),(4,82),(182,251),(66,192),t)
    s.mark('feathered_tails',line(u,v,7,-4,12,3,1.9)+line(u,v,-7,-4,-12,3,1.9),(156,254),(30,154),(66,246),sat((v+15)/30))

def micro_broach(s):
    # SPB-105 tick23: shared stepped rectangular carrier .595 -> pending; M7 pending. Compact progressive tooth combs.
    u,v,gx,gy=s.cell(31,27,.5);t=s.rand(gx,gy,1213);spine=line(u,v,-12,8,11,8,2.9)
    teeth=box(u+8,v+2,3.8,6)+box(u,v,3.8,8)+box(u-8,v-2,3.8,10);depth=sat((u+14)/28)
    s.mark('stepped_cut_floors',spine+teeth,(4,246),(0,246),(20,246),depth,rough_shade=sat((v+12)/24),coat_shade=t)
    s.mark('tooth_shoulders',line(u,v,-12,-8,-4,-8,2.2)+line(u,v,-4,-8,4,-8,2.2)+line(u,v,4,-12,12,-12,2.2),(172,255),(0,76),(20,164),1-t)
    s.mark('chip_curls',ring(u+8,v-6,4.4,1.8)*sat((-u+11)/3),(42,204),(96,208),(142,255),t)
    s.mark('recessed_stops',line(u,v,-8,-4,-8,2,2.2)+line(u,v,0,-2,0,4,2.2),(4,74),(190,255),(56,166),1-t)
    s.mark('runout_tabs',sat(6-abs(u-10)-abs(v-9)),(116,246),(22,138),(0,86),t)

def fan_cut_lathe(s):
    u,v,gx,gy=s.cell(32,32,.5);t=s.rand(gx,gy,53);r=np.hypot(u,v);a=np.arctan2(v,u)
    s.mark('radial_cut_faces',disk(u,v,13),(16,248),(20,216),(24,232),sat(.5+.5*np.sin(5*a+r*.23)),coat_shade=t)
    s.mark('hub_collars',ring(u,v,4.5,2),(8,100),(160,255),(110,252),1-t)
    s.mark('blade_edges',edge(np.sin(a*2.5+r*.08),.22)*sat((13-r)/2)*sat((r-5)/2),(174,255),(16,100),(0,128),t)
    s.mark('peripheral_chips',box(u-10,v-7,4,4)*disk(u,v,14),(32,158),(124,242),(104,226),t)
    s.mark('tool_witness_arcs',ring(u,v,14,1.5)*sat(np.cos(a*3)*3),(84,208),(45,186),(68,250),sat((v+16)/32))

def chisel_ledger(s):
    # SPB-105 tick23: filled ledger pad / Pangolin .619 -> pending; M7 pending. Three offset chisel strikes.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1217);facet=np.zeros_like(u);heads=np.zeros_like(u);shade=np.zeros_like(u)
    for dx,dy in ((-6,-7),(5,0),(-5,8)):
        x=u-dx;y=v-dy;wedge=sat(7-abs(x)-.65*abs(y))*sat(4-y);facet+=wedge;heads+=line(x,y,-6,-3,5,-3,1.8);shade=np.maximum(shade,wedge*sat((y+5)/10))
    s.mark('chisel_facets',facet,(12,252),(0,246),(24,246),shade,rough_shade=t,coat_shade=sat((u+14)/28))
    s.mark('strike_heads',heads,(160,254),(0,64),(0,142),1-t)
    s.mark('lifted_shavings',ring(u-8,v-8,4.6,1.7)*sat((u-5)/3),(44,202),(52,166),(130,255),t)
    s.mark('tail_splits',line(u,v,7,1,12,5,1.8)+line(u,v,-4,10,0,14,1.8),(6,94),(160,248),(118,238),t)
    s.mark('corner_gouges',sat(6-abs(u+10)-abs(v+11)),(20,142),(100,218),(22,124),1-t)

def slotted_knurl(s):
    u,v,gx,gy=s.cell(26,30);t=s.rand(gx,gy,59);ridge=sat(12-abs(u)*1.2-abs(v)*.7)
    s.mark('knurl_teeth',ridge,(38,254),(16,182),(22,250),sat((u+12)/24),coat_shade=t)
    s.mark('relief_slots',box(u,v,3.9,10),(0,96),(148,255),(130,242),t)
    s.mark('tooth_bevels',edge(abs(u)*1.2+abs(v)*.7-11,1.6),(150,254),(26,128),(0,108),1-t)
    s.mark('corner_punches',disk(u-10,v-11,4.4)+disk(u+10,v+11,4.4),(12,148),(106,226),(54,188),t)
    s.mark('worn_bridges',line(u,v,-10,3,-3,10,2),(64,218),(44,200),(96,254),sat((v+15)/30))

def polish_comet(s):
    # SPB-105 tick25: one two-wake tile .648 -> pending; M7 pending. Intersecting polish passes with independent short wakes.
    u,v,gx,gy=s.cell(23,27,.5);t=s.rand(gx,gy,1423);head=disk(u+5,v+4,5.6);wake=v+4-.035*(u+5)**2
    p,q,hx,hy=s.cell(29,21,.5,angle=-.47);w=s.rand(hx,hy,1427);return_wake=q+2+.035*(p+7)**2
    s.mark('polish_heads',head,(116,255),(0,100),(20,144),sat(np.hypot(u+5,v+4)/6),coat_shade=t)
    s.mark('trailing_fans',edge(wake,3.2)*sat(u+4)*sat(10-u),(24,246),(0,246),(104,252),sat((u+4)/14),rough_shade=sat((wake+3)/6),coat_shade=t)
    s.mark('second_fan',edge(return_wake,2.6)*sat(p+6)*sat(12-p),(8,112),(138,248),(36,180),w)
    s.mark('compound_residue',line(p,q,5,-7,12,-3,2.9)+disk(p+8,q-6,4.1),(0,90),(180,255),(160,254),1-w)
    s.mark('tail_witnesses',line(u,v,3,8,10,12,2.9),(148,250),(18,98),(0,60),sat((v+13)/26))

def foil_scarf(s):
    u,v,gx,gy=s.cell(28,32,.5);t=s.rand(gx,gy,67);fold=v-.35*u
    s.mark('scarfed_laps',sat(12-abs(fold))*box(u,v,13,14),(16,244),(32,212),(24,236),sat((fold+12)/24),coat_shade=t)
    s.mark('fold_crests',edge(fold-3,2.3)*box(u,v,12,12),(178,255),(8,64),(0,112),1-t)
    s.mark('sheared_tabs',box(u-9,v+7,4,5),(44,164),(154,246),(106,252),t)
    s.mark('recessed_punches',disk(u+7,v-7,4.5),(4,88),(172,255),(82,184),t)
    s.mark('peel_curls',ring(u-5,v-9,4.8,1.5)*sat((v+12)/3),(104,230),(50,146),(40,216),1-t)

def etched_gear(s):
    # SPB-105 tick23 / owner unique fine construction: Mica .689 -> pending; M7 pending. Rack-and-pinion engravings.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1201);r=np.hypot(u+3,v-2);a=np.arctan2(v-2,u+3);rim=8+1.3*np.cos(a*9)
    wheel=sat(rim-r)*sat(r-3);rack=box(u-9,v,3.2,13);tooth=edge(np.mod(v+15,7)-3.5,2.2)*box(u-5,v,4,13)
    s.mark('gear_annuli',wheel+rack,(54,246),(0,246),(16,244),sat(r/10),rough_shade=sat((v+15)/30),coat_shade=t)
    s.mark('etched_teeth',edge(r-rim,1.7)+tooth,(6,120),(156,250),(140,255),1-t)
    s.mark('hub_spokes',edge(np.sin(a*2),.34)*sat(7-r),(154,255),(0,88),(0,122),t)
    s.mark('index_keyway',box(u+3,v-2,3.9,3.9),(12,148),(100,232),(52,178),t)
    s.mark('witness_dimples',disk(u+10,v+11,4.2),(108,222),(40,136),(112,250),sat((u+14)/28))
