"""SPB-105 v2 tick 11: static optical-inspired material geometry.
These maps do not introduce a new iRacing shader, diffraction or painted color.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def fresnel_segments(s):
    # SPB-105 tick25: cylindrical lens pads .638 -> pending; M7 pending. Narrow stepped crescent slivers.
    u,v,gx,gy=s.cell(31,19,.5,angle=.29);t=s.rand(gx,gy,1429);r=np.hypot(u+14,v+14);center=v-u*.32
    sliver=sat(12-abs(u))*sat(5.8-abs(center));steps=np.mod(r,4.8)/4.8
    s.mark('stepped_lens_segments',sliver,(18,248),(0,246),(24,248),steps,rough_shade=sat((center+6)/12),coat_shade=t)
    s.mark('facet_reset_edges',edge(np.mod(r,4.8)-2.4,1.3)*sliver,(148,255),(0,92),(0,112),1-t)
    s.mark('segment_separator_slots',edge(abs(center)-5.6,1.7)*sat(12-abs(u)),(0,98),(180,255),(146,254),t)
    s.mark('lens_center_tabs',sat(6-abs(u+11)-abs(v+7)),(56,204),(102,232),(68,204),t)
    s.mark('truncated_facet_corners',line(u,v,8,2,13,6,2.8),(98,228),(54,180),(164,255),1-t)

def moire_packets(s):
    # SPB-105 tick21: boxed grating .65+ collisions -> pending; M7 pending. Interpenetrating clipped grating strips.
    u,v,gx,gy=s.cell(23,31,.5);t=s.rand(gx,gy,1069);a=np.sin((s.x+.31*s.y)*.78);b=np.sin((s.y-.27*s.x)*.91)
    strip=sat(10-abs(u+2*np.sin(v*.3)))*sat(13-abs(v));second=sat(8-abs(v+.6*u))*sat(10-abs(u))
    s.mark('crossed_grating_packets',strip,(18,246),(0,246),(24,248),sat(.5+.5*a),rough_shade=sat(.5+.5*b),coat_shade=t)
    s.mark('grating_beat_nodes',edge(a-b,.4)*second,(142,255),(0,92),(0,112),1-t)
    s.mark('packet_separation_gutters',edge(abs(u+2*np.sin(v*.3))-10,1.8)*sat(13-abs(v)),(0,98),(180,255),(146,254),t)
    s.mark('registration_tick_clusters',line(u,v,-8,-12,-2,-12,2.1)+line(u,v,3,11,9,11,2.1),(56,204),(102,232),(68,204),t)
    s.mark('etched_aperture_windows',sat(6-abs(u-6)-abs(v+5)),(96,228),(54,180),(164,255),1-t)

def prism_herringbone(s):
    # SPB-105 tick23: diamond-like ribbons .557 -> pending; M7 pending. Interlocked zigzag prism strips with alternating end joints.
    u,v,gx,gy=s.cell(23,29,.5);t=s.rand(gx,gy,1291);fold=v+.9*abs(u);band=edge(fold-1,4.3)+edge(fold+10,3.2)
    s.mark('prismatic_ribbons',band,(18,246),(0,246),(24,248),sat(.5+fold/8),rough_shade=sat((u+11)/22),coat_shade=t)
    s.mark('ridge_breaks',edge(fold-4,1.9)+edge(fold+7,1.7),(144,255),(0,92),(0,114),1-t)
    s.mark('end_face_sockets',line(u,v,-10,-7,-5,-11,2.5),(0,98),(178,255),(146,254),t)
    s.mark('cross_prism_notches',line(u,v,3,-2,9,3,2.1)*band,(56,204),(102,232),(68,204),t)
    s.mark('polished_terminal_facets',sat(6-abs(u-8)-abs(v-10)),(96,228),(54,180),(164,255),1-t)

def coded_apertures(s):
    # Tick 18: generic random checker -> a quadratic-residue aperture code with individual 8px windows.
    gx=np.floor(s.x/10);gy=np.floor(s.y/10);u=np.mod(s.x,10)-5;v=np.mod(s.y,10)-5
    residues=np.array([0,1,0,1,1,0,0,0,0,1,1,0,1],np.float32);a=residues[np.mod(gx,13).astype(int)];b=residues[np.mod(gy,13).astype(int)]
    aperture=(a!=b).astype(np.float32);t=s.rand(gx,gy,859);window=box(u,v,4,4)
    s.mark('coded_opaque_platelets',window*(1-aperture),(18,244),(28,224),(24,248),t,coat_shade=sat((u+5)/10))
    s.mark('milled_aperture_windows',window*aperture,(0,102),(176,255),(140,254),1-t)
    s.mark('polished_window_chamfers',edge(np.maximum(abs(u),abs(v))-4,1.1)*aperture,(150,255),(16,100),(0,112),sat((v+5)/10))
    s.mark('registration_diamonds',sat(4-abs(u)-abs(v))*(np.mod(gx+gy*3,11)==0),(56,206),(102,232),(68,212),t)
    s.mark('interrupted_support_tabs',box(u,v,4,1.8)*(np.mod(gx*2+gy,7)==0),(98,228),(54,184),(164,255),1-t)

def reflector_triplets(s):
    # SPB-105 tick23: triangular facets .574 -> pending; M7 pending. Recessed corner cubes in a staggered hex aperture array.
    u,v,gx,gy=s.cell(25,22,.5);t=s.rand(gx,gy,1237);d=np.maximum(abs(v),.866*abs(u)+.5*abs(v));a=np.arctan2(v,u);body=sat(9-d)
    face=np.floor(np.mod(a+3.14159,6.28318)/2.09439)/2;seams=edge(np.sin(a*1.5),.25)*body
    s.mark('three_corner_faces',body,(18,246),(0,246),(24,248),face,rough_shade=sat(d/9),coat_shade=t)
    s.mark('corner_cube_seams',seams,(146,255),(0,92),(0,114),1-t)
    s.mark('central_return_pits',sat(4.5-d),(0,98),(180,255),(146,254),t)
    s.mark('reflector_border_tabs',edge(d-9,1.9),(56,204),(102,232),(68,204),sat((u+12)/24))
    s.mark('chipped_cube_tips',sat(6-abs(u-9)-abs(v-7)),(96,228),(54,180),(164,255),1-t)

def polar_starlets(s):
    # SPB-105 tick27 / owner unique native structure: shared Voronoi .974 rejected; M7 88.58 -> pending. Paired polar stars with independent tip geometry.
    u,v,gx,gy=s.cell(29,25,.5);t=s.rand(gx,gy,1511);u=u+3*(s.rand(gx,gy,1523)-.5);v=v+3*(s.rand(gx,gy,1531)-.5)
    x=u+6;y=v+4;r=np.hypot(x,y);a=np.arctan2(y,x);star=sat(5.2+3.7*np.cos(a*4)-r)
    p=u-7;q=v-6;r2=np.hypot(p,q);a2=np.arctan2(q,p);small=sat(4.5+3*np.cos(a2*4+.55)-r2)
    s.mark('polar_facet_stars',star+small,(18,246),(0,246),(24,248),sat((x+9)/18),rough_shade=sat((q+9)/18),coat_shade=t)
    s.mark('radial_bevel_spines',edge(x-y,1.8)*star+edge(p+q,1.8)*small,(144,255),(16,108),(0,112),1-t)
    s.mark('etched_star_centers',disk(x,y,4.1)+disk(p,q,4.1),(0,98),(180,255),(146,254),t)
    s.mark('detached_facet_slivers',line(u,v,-12,5,-5,11,2.6)+line(u,v,3,-11,11,-8,2.2),(56,204),(102,232),(68,204),t)
    s.mark('star_tip_witnesses',line(u,v,8,-4,13,1,2.6)+line(u,v,-3,-12,3,-9,2.2),(96,228),(54,180),(164,255),1-t)

def waveguide_meander(s):
    # SPB-105 tick23: square meander tile .585 -> pending; M7 pending. Two interdigitated hairpin guides.
    u,v,gx,gy=s.cell(29,27,.5);t=s.rand(gx,gy,1231);left=ring(u+5,v+4,6,2.3)*sat(-u/2)+line(u,v,-5,-10,-5,-4,2.3)+line(u,v,1,4,10,4,2.3)
    right=ring(u-5,v-4,6,2.3)*sat(u/2)+line(u,v,5,4,5,10,2.3)+line(u,v,-10,-4,-1,-4,2.3);guide=left+right
    s.mark('meandering_guide_ribbons',guide,(18,246),(0,246),(24,248),sat((u+14)/28),rough_shade=sat((v+13)/26),coat_shade=t)
    s.mark('guide_turn_crowns',edge(abs(u)-10,1.8)*sat(8-abs(v)),(146,255),(0,92),(0,114),1-t)
    s.mark('absorbing_terminations',disk(u+10,v+4,4.2)+disk(u-10,v-4,4.2),(0,98),(180,255),(146,254),t)
    s.mark('coupling_bridge_ports',line(u,v,-3,0,3,0,2.9),(56,204),(102,232),(68,204),t)
    s.mark('etched_locator_dots',disk(u+9,v-10,4.1)+disk(u-9,v+10,4.1),(96,228),(54,180),(164,255),1-t)

def split_lenslets(s):
    # Tick 18: scallop rows -> opposed cylindrical halves separated by a diagonal registration slit.
    u,v,gx,gy=s.cell(25,31,.5,angle=-17);t=s.rand(gx,gy,857);split=u+v*.23
    capsule=disk(u*.8,np.maximum(abs(v)-6,0),7.8);l=capsule*sat((-split-1)/2);r=capsule*sat((split-1)/2)
    s.mark('left_lens_half',l,(14,244),(26,218),(24,248),sat((u+10)/20),coat_shade=t)
    s.mark('right_registered_half',r,(146,255),(16,108),(0,114),sat((10-u)/20),rough_shade=1-t)
    s.mark('diagonal_registration_slits',edge(split,1.8)*capsule,(0,100),(180,255),(146,254),t)
    s.mark('lens_mount_shoulders',line(u,v,-10,-10,-10,8,2)+line(u,v,10,-8,10,10,2),(58,204),(102,232),(68,210),1-t)
    s.mark('alignment_witness_pairs',disk(u+7,v+12,4)+disk(u-7,v-12,4),(96,228),(54,184),(164,255),sat((v+15)/30))

def zone_plate_shards(s):
    u,v,gx,gy=s.cell(32,32);t=s.rand(gx,gy,433);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a);rad=np.hypot(cu+8,cv+8);shard=sat(13-abs(cu)-abs(cv)*.8)
    s.mark('broken_zone_plate_sectors',shard,(18,246),(24,214),(24,248),sat(.5+.5*np.cos(rad*rad*.06)),coat_shade=t)
    s.mark('sector_facet_boundaries',edge(np.sin(rad*rad*.03),.23)*shard,(144,255),(16,108),(0,112),1-t)
    s.mark('shard_edge_losses',box(cu-7,cv-4,4,4),(0,98),(180,255),(146,254),t)
    s.mark('recessed_focus_arclets',ring(cu+8,cv+8,7,1.6)*shard,(56,204),(102,232),(68,204),t)
    s.mark('detached_plate_grains',disk(cu+10,cv-10,4.2),(96,228),(54,180),(164,255),1-t)

def diffractive_hatch(s):
    u,v,gx,gy=s.cell(32,24,.5);t=s.rand(gx,gy,439);bars=np.mod(u+16,8)/8;gate=box(u,v,14,9)*sat((v+8+u*.25)/3)
    s.mark('segmented_grating_lands',gate,(18,246),(24,214),(24,248),bars,coat_shade=t)
    s.mark('hatch_crosscuts',line(u,v,-12,-8,10,8,1.8),(0,98),(180,255),(146,254),1-t)
    s.mark('polished_grating_crests',edge(v+5,2)*gate,(144,255),(16,108),(0,112),t)
    s.mark('missing_grating_teeth',box(u-8,v+4,4,4),(56,204),(102,232),(68,204),t)
    s.mark('termination_fan_tabs',sat(6-abs(u+10)-abs(v-8)),(96,228),(54,180),(164,255),1-t)

def optic_pinwheels(s):
    # SPB-105 tick25 / name gate: disconnected flecks rejected -> four connected folded angular sails; M7 pending.
    u,v,gx,gy=s.cell(31,29,.5);t=s.rand(gx,gy,1459);sails=np.zeros_like(u);creases=np.zeros_like(u);tips=np.zeros_like(u);shade=np.zeros_like(u)
    for k in range(4):
        a=t*6.283+k*1.5708;x=u*np.cos(a)+v*np.sin(a);y=-u*np.sin(a)+v*np.cos(a);blade=sat(x-y)*sat(y)*sat(12-x-y/3)
        sails+=blade;creases+=line(x,y,1,1,10,5,1.7)*blade;tips+=sat(5-abs(x-9)-abs(y-7));shade=np.maximum(shade,blade*sat(y/8))
    s.mark('folded_angular_sails',sails,(18,246),(0,246),(24,248),shade,rough_shade=sat(np.hypot(u,v)/14),coat_shade=t)
    s.mark('sail_fold_crests',creases,(146,255),(0,92),(0,114),1-t)
    s.mark('central_rotor_hubs',disk(u,v,4.2),(0,98),(180,255),(146,254),t)
    s.mark('blade_clearance_notches',tips,(56,204),(102,232),(68,204),t)
    s.mark('registration_pinholes',disk(u+11,v+10,4.1),(96,228),(54,180),(164,255),1-t)
