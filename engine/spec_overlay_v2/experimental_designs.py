"""SPB-105 v2 tick 14: eleven mathematical material constructions.
Known mathematics inspires original drawings; no claim of new physical shaders.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def gyroid_windows(s):
    x=s.x*.28;y=s.y*.28;field=np.sin(x)*np.cos(y)+np.sin(y)*.63+np.cos(x)*.48
    u,v,gx,gy=s.cell(28,28);t=s.rand(gx,gy,601)
    s.mark('saddle_surface_lobes',sat((field+.4)*1.3),(18,246),(24,214),(24,248),sat(field*.5+.5),coat_shade=t)
    s.mark('gyroid_neck_crests',edge(field,.32),(146,255),(16,108),(0,114),1-t)
    s.mark('open_saddle_windows',sat((-field-.8)*3),(0,98),(180,255),(146,254),t)
    s.mark('junction_shoulder_ribs',edge(field-.8,.22),(56,204),(102,232),(68,204),sat((u+14)/28))
    s.mark('etched_saddle_ticks',line(u,v,-9,-8,-2,-2,1.8)*sat(field),(96,228),(54,180),(164,255),1-t)

def kagome_bridges(s):
    u,v,gx,gy=s.cell(32,28,.5);t=s.rand(gx,gy,607);tri=np.maximum.reduce([v-6,u*.866-v*.5-6,-u*.866-v*.5-6]);net=edge(tri,2.4)
    s.mark('trihexagonal_ligaments',net,(18,246),(24,214),(24,248),sat((u+16)/32),coat_shade=t)
    s.mark('three_way_bond_knots',disk(u,v+12,4.3),(146,255),(16,108),(0,114),1-t)
    s.mark('recessed_hex_windows',ring(u,v-5,5.2,1.8),(0,98),(180,255),(146,254),t)
    s.mark('bridge_stress_gussets',line(u,v,-11,8,-3,4,2),(56,204),(102,232),(68,204),t)
    s.mark('bonded_corner_tabs',box(u-11,v-8,4,4),(96,228),(54,180),(164,255),1-t)

def voronoi_kites(s):
    # SPB-105 tick19: center diamonds/Scutes .965 -> pending; M7 pending.
    # Kites span the dual bonds between nearest sites, instead of decorating cell centers.
    pitch=22.;gx=np.floor(s.x/pitch);gy=np.floor(s.y/pitch);best=np.full((s.h,s.w),1e9,np.float32);second=best.copy()
    ax=best.copy();ay=best.copy();bx=best.copy();by=best.copy()
    for oy in (-1,0,1):
        for ox in (-1,0,1):
            ix=gx+ox;iy=gy+oy;px=(ix+.12+.76*s.rand(ix,iy,991))*pitch;py=(iy+.12+.76*s.rand(ix,iy,997))*pitch;d=(s.x-px)**2+(s.y-py)**2
            hit=d<best;next_hit=(~hit)&(d<second)
            bx=np.where(hit,ax,np.where(next_hit,px,bx));by=np.where(hit,ay,np.where(next_hit,py,by));second=np.where(hit,best,np.minimum(second,d))
            ax=np.where(hit,px,ax);ay=np.where(hit,py,ay);best=np.minimum(best,d)
    dx=bx-ax;dy=by-ay;length=np.maximum(np.hypot(dx,dy),1);x=s.x-(ax+bx)*.5;y=s.y-(ay+by)*.5
    u=(x*dx+y*dy)/length;v=(-x*dy+y*dx)/length;half=np.minimum(length*.46,14);kite=sat(1-abs(u)/half-abs(v)/5.5)*4
    t=s.rand(np.floor(ax/pitch),np.floor(ay/pitch),1009)
    s.mark('asymmetric_kite_faces',kite,(18,246),(0,246),(24,248),sat((v+5.5)/11),rough_shade=sat(abs(u)/half),coat_shade=t)
    s.mark('kite_diagonal_spines',edge(v,1.8)*sat(half-abs(u)),(146,255),(0,88),(0,114),1-t)
    s.mark('interkite_recesses',edge(abs(u)/half+abs(v)/5.5-1,.24),(0,98),(180,255),(146,254),t)
    s.mark('offset_kite_hinges',disk(u+half*.65,v,4.1)*sat(kite),(56,204),(102,232),(68,204),sat(abs(v)/5.5))
    s.mark('beveled_tail_chips',line(u,v,-half*.5,1,-half,0,2.8),(96,228),(54,180),(164,255),1-t)

def quasicrystal_fans(s):
    q=0.;cross=0.
    for i in range(5):
        a=i*np.pi/5;phase=(s.x*np.cos(a)+s.y*np.sin(a))*.38
        q=q+np.cos(phase);cross=cross+np.sin(phase)*np.cos(a*3)
    u,v,gx,gy=s.cell(24,24);t=s.rand(gx,gy,613)
    s.mark('five_axis_facet_packets',sat((q+.7)/2),(18,246),(24,214),(24,248),sat(q*.2+.5),coat_shade=t)
    s.mark('quasiperiodic_bond_edges',edge(q,.42),(146,255),(16,108),(0,114),sat(cross*.25+.5))
    s.mark('deep_interference_nodes',sat((-q-1.5)*2),(0,98),(180,255),(146,254),t)
    s.mark('fan_crossing_saddles',edge(cross,.4)*sat(q),(56,204),(102,232),(68,204),sat((u+12)/24))
    s.mark('growth_front_islets',edge(q-2.5,.35),(96,228),(54,180),(164,255),1-t)

def truchet_switchyard(s):
    u,v,gx,gy=s.cell(28,28);t=s.rand(gx,gy,617);flip=s.rand(gx,gy,619)>.5;cu=np.where(flip,-u,u);r1=np.hypot(cu+14,v+14);r2=np.hypot(cu-14,v-14);arcs=edge(r1-14,3)+edge(r2-14,3)
    s.mark('paired_truchet_tracks',arcs,(18,246),(24,214),(24,248),sat((v+14)/28),coat_shade=t)
    s.mark('track_switch_collars',ring(cu,v,4.5,1.6)*sat((t-.3)*3),(146,255),(16,108),(0,114),1-t)
    s.mark('recessed_arc_interstices',sat(8-np.minimum(r1,r2)),(0,98),(180,255),(146,254),t)
    s.mark('junction_contact_tabs',box(cu+11,v,4,4),(56,204),(102,232),(68,204),t)
    s.mark('guideway_index_ticks',line(cu,v,7,-10,12,-4,1.6),(96,228),(54,180),(164,255),1-t)

def hilbert_relays(s):
    u,v,gx,gy=s.cell(32,32);t=s.rand(gx,gy,631)
    points=[(-12,-12),(-4,-12),(-4,-4),(-12,-4),(-12,4),(-12,12),(-4,12),(-4,4),(4,4),(4,12),(12,12),(12,4),(12,-4),(4,-4),(4,-12),(12,-12)]
    path=0.
    for a,b in zip(points[:-1],points[1:]):path=path+line(u,v,*a,*b,1.7)
    s.mark('space_filling_relay_tracks',path,(18,246),(24,214),(24,248),sat((u+v+32)/64),coat_shade=t)
    s.mark('relay_corner_pads',box(u+12,v+12,4,4)+box(u-12,v-12,4,4),(146,255),(16,108),(0,114),1-t)
    s.mark('insulating_channel_pockets',box(u,v,4,4),(0,98),(180,255),(146,254),t)
    s.mark('path_terminal_slots',line(u,v,-12,-12,-4,-12,2),(56,204),(102,232),(68,204),t)
    s.mark('bridge_via_collars',ring(u-4,v+4,4.1,1.4),(96,228),(54,180),(164,255),1-t)

def reaction_maze(s):
    # Analytic reaction-front drawing, explicitly not a Gray-Scott simulation.
    x=s.x*.31;y=s.y*.31;phase=np.sin(x+1.3*np.sin(y))+np.cos(y+.8*np.cos(x*.73))
    u,v,gx,gy=s.cell(26,26);t=s.rand(gx,gy,641)
    s.mark('reaction_front_ribbons',edge(phase,.72),(18,246),(24,214),(24,248),sat(.5+.5*np.sin(x-y)),coat_shade=t)
    s.mark('branching_front_crests',edge(phase-.55,.19),(146,255),(16,108),(0,114),1-t)
    s.mark('depleted_reaction_pools',sat((-phase-1)*3),(0,98),(180,255),(146,254),t)
    s.mark('front_collision_nodes',edge(np.sin(x-y),.25)*sat(phase),(56,204),(102,232),(68,204),sat((v+13)/26))
    s.mark('nucleation_seed_pores',disk(u-7,v+7,4.1)*sat(phase),(96,228),(54,180),(164,255),1-t)

def auxetic_hinges(s):
    u,v,gx,gy=s.cell(30,28);t=s.rand(gx,gy,643);waist=4+abs(v)*.5;bow=sat(waist-abs(u))*box(u,v,12,11)
    s.mark('reentrant_bowtie_plates',bow,(18,246),(24,214),(24,248),sat((u+15)/30),coat_shade=t)
    s.mark('rotating_hinge_necks',box(u,v,4.3,4.3),(146,255),(16,108),(0,114),1-t)
    s.mark('reentrant_edge_slots',edge(abs(u)-waist,1.7)*box(u,v,13,12),(0,98),(180,255),(146,254),t)
    s.mark('shear_relief_eyelets',ring(u+9,v+9,4.2,1.5),(56,204),(102,232),(68,204),t)
    s.mark('hinge_corner_bearing_tabs',box(u-9,v-9,4,4),(96,228),(54,180),(164,255),1-t)

def tensegrity_cells(s):
    # SPB-105 tick25: crossed grid / Stomata .603 -> pending; M7 pending. Three disjoint compression struts joined only by cables.
    u,v,gx,gy=s.cell(31,29,.5);t=s.rand(gx,gy,1451);a=t*1.7;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    bars=line(cu,cv,-10,-6,-4,9,2.7)+line(cu,cv,0,-11,10,-4,2.7)+line(cu,cv,4,0,-1,12,2.7)
    cables=line(cu,cv,-10,-6,0,-11,1.5)+line(cu,cv,10,-4,4,0,1.5)+line(cu,cv,-4,9,-1,12,1.5)+line(cu,cv,0,-11,-1,12,1.4)
    s.mark('compression_strut_pairs',bars,(18,246),(0,246),(24,248),sat((cu+14)/28),rough_shade=sat((cv+14)/28),coat_shade=t)
    s.mark('tension_cable_triangles',cables,(146,255),(0,92),(0,114),1-t)
    s.mark('floating_joint_recesses',disk(cu+4,cv-9,4.2),(0,98),(180,255),(146,254),t)
    s.mark('anchored_strut_collars',ring(cu+10,cv+6,4.1,1.8)+ring(cu-10,cv+4,4.1,1.8),(56,204),(102,232),(68,204),t)
    s.mark('cable_clamp_tabs',line(cu,cv,5,6,11,10,2.9),(96,228),(54,180),(164,255),1-t)

def fractal_seeds(s):
    # SPB-105 tick22: one perforated triangle / Stencil .682 -> pending; M7 pending. Three nested triangular seed generations.
    u,v,gx,gy=s.cell(31,29,.5);t=s.rand(gx,gy,1163);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    plates=np.zeros_like(u);bound=np.zeros_like(u);holes=np.zeros_like(u)
    for dx,dy in ((0,-6),(-6,5),(6,5)):
        x=cu-dx;y=cv-dy;d=np.maximum(-y*.7,abs(x)*.866+y*.5);plates+=sat(5-d);bound+=edge(d-4,1.5);holes+=sat(2.2-d)
    s.mark('recursive_triangle_plates',plates,(18,246),(0,246),(24,248),sat((cv+14)/28),rough_shade=sat((cu+14)/28),coat_shade=t)
    s.mark('three_seed_vertex_nodes',disk(cu,cv+11,4.1)+disk(cu-10,cv-9,4.1)+disk(cu+10,cv-9,4.1),(146,255),(0,92),(0,114),1-t)
    s.mark('central_triangle_voids',holes,(0,98),(180,255),(146,254),t)
    s.mark('recursive_edge_notches',bound,(56,204),(102,232),(68,204),t)
    s.mark('seed_bridge_witnesses',line(cu,cv,-5,1,5,1,2.1),(96,228),(54,180),(164,255),1-t)

def hyperbolic_scales(s):
    # Tick 18: nested circular rows -> saddle-shaped scale plates and conjugate hyperbola cuts.
    u,v,gx,gy=s.cell(29,31,.5,angle=23);t=s.rand(gx,gy,881);u+=4*(t-.5);saddle=u*v/18
    plate=box(u,v,12,13)*sat(10-abs(saddle));waist=edge(saddle,1.8)*plate
    s.mark('saddle_scale_faces',plate,(18,246),(24,216),(24,248),sat((saddle+10)/20),coat_shade=t)
    s.mark('conjugate_hyperbola_rims',edge(abs(saddle)-7,1.6)*plate,(146,255),(16,108),(0,114),sat((u+13)/26),rough_shade=1-t)
    s.mark('scale_waist_recesses',waist,(0,100),(180,255),(146,254),t)
    s.mark('overlap_corner_studs',disk(u+9,v+10,4)+disk(u-9,v-10,4),(58,204),(102,232),(68,212),1-t)
    s.mark('split_cusp_tabs',line(u,v,-10,10,-3,7,2)+line(u,v,3,-7,10,-10,2),(96,228),(54,184),(164,255),sat((v+15)/30))
