"""SPB-105 v2 tick 13: eleven motorsport processes reduced to fine spec geometry."""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def tire_sipes(s):
    # SPB-105 tick25: two rectangular fingers / Rack .631 -> pending; M7 pending. Staggered rhomboidal tread lugs and zigzag drainage.
    u,v,gx,gy=s.cell(31,23,.5);t=s.rand(gx,gy,1433);x=u-v*.52;pad=box(x+7,v,5,8)+box(x-7,v,5,8);zig=v-2.6*np.sin(x*.65)
    s.mark('tread_block_faces',pad,(12,226),(0,246),(24,248),sat((x+14)/28),rough_shade=sat((v+11)/22),coat_shade=t)
    s.mark('zigzag_sipe_cuts',edge(zig-3,1.8)*pad+edge(zig+3,1.8)*pad,(0,86),(188,255),(150,254),1-t)
    s.mark('polished_tread_shoulders',edge(abs(x)-11,1.8)*sat(8-abs(v)),(158,255),(0,92),(0,112),t)
    s.mark('transverse_drainage_notches',line(x,v,-11,7,-4,7,2.2)+line(x,v,3,-7,11,-7,2.2),(62,202),(100,232),(70,204),t)
    s.mark('rubber_pickup_nibs',disk(x,v-9,4.2),(98,228),(54,180),(164,255),1-t)

def brake_rotor_slots(s):
    u,v,gx,gy=s.cell(32,26,.5);t=s.rand(gx,gy,523);slot=v+2*np.sin(u*.17);plate=box(u,v,14,11)
    s.mark('rotor_swept_lands',plate,(112,255),(20,198),(20,232),sat((u+16)/32),coat_shade=t)
    s.mark('curved_degas_slots',edge(slot,2.7)*box(u,v,11,9),(0,98),(180,255),(148,254),1-t)
    s.mark('slot_chamfers',edge(abs(slot)-3.5,1.4)*box(u,v,12,10),(156,255),(16,92),(0,112),t)
    s.mark('wear_track_arclets',ring(u+10,v-9,9,1.4)*plate,(54,204),(98,230),(68,204),t)
    s.mark('drilled_cooling_pores',disk(u-9,v+8,4.3),(96,228),(54,178),(164,255),1-t)

def pit_crew_grip(s):
    # SPB-105 tick21: diamond / Paired Facet .768 -> pending; M7 pending. Molded three-finger grip ribs.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1093);a=(np.mod(gx+gy,2)*2-1)*.52;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    ribs=box(cu+7,cv+3,3.2,8)+box(cu,cv,3.2,11)+box(cu-7,cv-3,3.2,8);root=line(cu,cv,-10,9,8,9,2.7)
    s.mark('molded_grip_lugs',ribs+root,(18,244),(0,246),(24,248),sat((cv+12)/24),rough_shade=t,coat_shade=sat((cu+12)/24))
    s.mark('raised_lug_crowns',(edge(cu+7,1.4)+edge(cu,1.4)+edge(cu-7,1.4))*ribs,(146,255),(0,92),(0,114),1-t)
    s.mark('grip_drain_channels',line(cu,cv,-11,-7,10,-7,2.1)*(1-root),(0,98),(180,255),(146,254),t)
    s.mark('lug_flex_notches',line(cu,cv,-10,2,10,2,1.6)*ribs,(56,204),(102,232),(68,204),t)
    s.mark('contact_wear_dimples',disk(cu+9,cv-10,4.1),(98,228),(54,180),(164,255),1-t)

def carbon_brake_grain(s):
    u,v,gx,gy=s.cell(26,26);t=s.rand(gx,gy,547);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    s.mark('compacted_carbon_grains',disk(cu*.8,cv*1.2,9),(14,228),(34,232),(24,248),sat((cu+13)/26),coat_shade=t)
    s.mark('fractured_fiber_fragments',line(cu,cv,-10,-5,9,5,2.1)+line(cu,cv,-7,5,4,-5,1.6),(146,255),(16,108),(0,114),1-t)
    s.mark('venting_matrix_pores',disk(cu+5,cv-5,4.2),(0,98),(180,255),(146,254),t)
    s.mark('resin_conversion_rims',ring(cu,cv,10,1.5)*sat((cv+2)/3),(56,204),(102,232),(68,204),t)
    s.mark('polished_grain_tips',box(cu-8,cv-8,4,4),(98,228),(54,180),(164,255),1-t)

def checkered_microfoil(s):
    # SPB-105 tick23: checker ribbon / Weld .662 -> pending; M7 pending. Torn L-shaped checker fragments and folded square tabs.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1303);turn=np.mod(gx+gy,4)*1.5708;cu=u*np.cos(turn)+v*np.sin(turn);cv=-u*np.sin(turn)+v*np.cos(turn)
    patch=box(cu+4,cv+4,8,4.1)+box(cu+8,cv-4,4.1,4.1);checks=np.mod(np.floor((cu+12)/8)+np.floor((cv+8)/8),2)
    s.mark('checker_foil_squares',patch,(14,250),(0,246),(24,248),checks,rough_shade=sat((cv+12)/24),coat_shade=t)
    s.mark('creased_foil_ridges',line(cu,cv,-11,-7,-1,0,1.9)*patch,(144,255),(0,92),(0,112),sat((cu+13)/26))
    s.mark('torn_fragment_borders',line(cu,cv,-12,-8,4,-8,2)+line(cu,cv,-12,-8,-12,8,2),(0,100),(180,255),(146,254),1-t)
    s.mark('exposed_adhesive_tabs',line(cu,cv,3,3,10,9,2.8),(58,204),(102,230),(68,210),t)
    s.mark('folded_checker_corners',sat(6-abs(cu-5)-abs(cv+5)),(96,228),(54,184),(164,255),1-t)

def telemetry_dash(s):
    u,v,gx,gy=s.cell(32,28);t=s.rand(gx,gy,563);column=np.floor((u+16)/8);height=4+10*s.rand(gx*4+column,gy,569);bars=sat(height-abs(v))*sat(3.5-abs(np.mod(u+16,8)-4))
    s.mark('telemetry_bar_packets',bars,(18,246),(24,214),(24,248),sat((v+14)/28),coat_shade=t)
    s.mark('peak_hold_markers',edge(abs(v)-height,1.7)*box(u,v,14,12),(146,255),(16,108),(0,114),1-t)
    s.mark('display_grid_gutters',line(u,v,-12,10,12,10,1.8),(0,98),(180,255),(146,254),t)
    s.mark('sampling_clock_tabs',box(u+10,v+8,4,4),(56,204),(102,232),(68,204),t)
    s.mark('signal_trace_kinks',line(u,v,-8,-4,-1,3,1.7)+line(u,v,-1,3,7,-2,1.7),(98,228),(54,180),(164,255),1-t)

def rumble_strip_ticks(s):
    # SPB-105 tick21: square tire-like pads .816 -> pending; M7 pending. Alternating stepped kerb triplets.
    u,v,gx,gy=s.cell(29,23,.5);t=s.rand(gx,gy,1091);side=np.where(np.mod(gx+gy,2)==0,1,-1);x=u*side
    ramps=box(x+8,v+4,4.3,6)+box(x,v,4.3,8)+box(x-8,v-4,4.3,6);level=sat((x+14)/28)
    s.mark('kerb_ramp_packets',ramps,(18,246),(0,246),(24,248),level,rough_shade=sat((v+11)/22),coat_shade=t)
    s.mark('grooved_strip_separators',line(x,v,-4,-8,-4,8,1.7)+line(x,v,4,-8,4,8,1.7),(0,98),(180,255),(146,254),1-t)
    s.mark('worn_kerb_shoulders',line(x,v,-12,-10,-4,-10,2)+line(x,v,-4,-8,4,-8,2)+line(x,v,4,-2,12,-2,2),(146,255),(0,92),(0,114),t)
    s.mark('aggregate_breakouts',disk(x-8,v-6,4.2),(56,204),(102,232),(68,204),t)
    s.mark('tire_witness_ticks',line(x,v,-9,2,-2,7,1.8)+line(x,v,3,2,9,5,1.8),(98,228),(54,180),(164,255),1-t)

def grid_stencil_mesh(s):
    u,v,gx,gy=s.cell(32,30);t=s.rand(gx,gy,577);frame=edge(np.maximum(abs(u),abs(v))-10,2.3);gap=1-box(u,v+10,4,4)
    s.mark('stencil_cell_frames',frame*gap,(18,246),(24,214),(24,248),sat((u+16)/32),coat_shade=t)
    s.mark('stencil_bridge_tabs',box(u,v+9,4,5),(146,255),(16,108),(0,114),1-t)
    s.mark('recessed_grid_corners',box(u+8,v-8,4,4),(0,98),(180,255),(146,254),t)
    s.mark('registration_chevrons',line(u,v,-5,-3,0,3,1.8)+line(u,v,0,3,5,-3,1.8),(56,204),(102,232),(68,204),t)
    s.mark('overspray_edge_grains',disk(u-12,v-11,4.1),(98,228),(54,180),(164,255),1-t)

def catch_fence_clips(s):
    u,v,gx,gy=s.cell(30,30);t=s.rand(gx,gy,587);a=line(u,v,-13,-13,13,13,1.8);b=line(u,v,-13,13,13,-13,1.8)
    s.mark('crossed_fence_strands',a+b,(18,246),(24,214),(24,248),sat((u+15)/30),coat_shade=t)
    s.mark('wrapped_wire_clips',ring(u,v,6,2.2)*sat((v+3)/3),(146,255),(16,108),(0,114),1-t)
    s.mark('clip_crimp_pockets',box(u,v+4,4,4),(0,98),(180,255),(146,254),t)
    s.mark('wire_twist_tails',line(u,v,3,5,10,11,1.6),(56,204),(102,232),(68,204),t)
    s.mark('galvanized_contact_nibs',disk(u+9,v-9,4.2),(98,228),(54,180),(164,255),1-t)

def aero_vortex_tabs(s):
    u,v,gx,gy=s.cell(30,28,.5);t=s.rand(gx,gy,593);left=sat(9-abs(u+5)-abs(v)*.45);right=sat(9-abs(u-5)-abs(v)*.45)
    s.mark('paired_vortex_vanes',left+right,(18,246),(24,214),(24,248),sat((u+15)/30),coat_shade=t)
    s.mark('vane_leading_crests',line(u,v,-10,-9,-2,9,1.8)+line(u,v,2,9,10,-9,1.8),(146,255),(16,108),(0,114),1-t)
    s.mark('mounting_recesses',box(u,v+9,4,4),(0,98),(180,255),(146,254),t)
    s.mark('shear_layer_witness_arcs',ring(u-8,v-7,5,1.5)*sat((v-4)/3),(56,204),(102,232),(68,204),t)
    s.mark('riveted_vane_feet',disk(u+10,v+10,4.1),(98,228),(54,180),(164,255),1-t)

def rivet_safety_wire(s):
    u,v,gx,gy=s.cell(32,28,.5);t=s.rand(gx,gy,599);r1=np.hypot(u+8,v+6);r2=np.hypot(u-8,v-6);wire=v-u*.75
    s.mark('rivet_head_discs',sat(6-r1)+sat(6-r2),(18,246),(24,214),(24,248),sat((u+16)/32),coat_shade=t)
    s.mark('twisted_safety_wires',edge(wire+1.4*np.sin(u*.9),1.6)*box(u,v,11,11),(146,255),(16,108),(0,114),1-t)
    s.mark('drilled_lock_holes',disk(u+8,v+6,4)+disk(u-8,v-6,4),(0,98),(180,255),(146,254),t)
    s.mark('rivet_annular_lips',edge(r1-6,1.4)+edge(r2-6,1.4),(56,204),(102,232),(68,204),t)
    s.mark('folded_wire_tails',line(u,v,7,-7,13,-11,1.7),(98,228),(54,180),(164,255),1-t)
