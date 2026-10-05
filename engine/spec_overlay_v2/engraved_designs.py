"""SPB-105 v2 tick 12: eleven fine ornamental engravings and inlays.
Each has its own drawing grammar; shared geometry helpers carry no pattern.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box

def damascene_inlay(s):
    # SPB-105 tick21: single stem tile/Botryoidal .706 -> pending; M7 pending. Alternating acorn-ended inlay sprigs.
    u,v,gx,gy=s.cell(25,31,.5);t=s.rand(gx,gy,1063);bend=2.5*np.sin(v*.18);stem=u-bend
    leaf1=sat(7-abs(u+5)-.55*abs(v+5));leaf2=sat(7-abs(u-5)-.65*abs(v-6))
    s.mark('inlaid_leaf_blades',leaf1+leaf2,(18,246),(0,246),(24,248),sat((v+14)/28),rough_shade=t,coat_shade=sat((u+12)/24))
    s.mark('scrolling_inlay_stems',edge(stem,2.6)*sat(13-abs(v)),(146,255),(0,92),(0,114),1-t)
    s.mark('undercut_inlay_channels',edge(abs(stem)-3.5,1.5)*sat(13-abs(v)),(0,98),(180,255),(146,254),t)
    s.mark('leaf_vein_burin_cuts',line(u,v,-9,-9,-2,-2,1.8)+line(u,v,2,2,9,10,1.8),(56,204),(102,232),(68,204),t)
    s.mark('stippling_rosettes',disk(u-7,v+10,4.3)+ring(u+7,v-10,4.3,1.7),(96,228),(54,180),(164,255),1-t)

def engine_turn_medallions(s):
    u,v,gx,gy=s.cell(32,30,.5);t=s.rand(gx,gy,457);r=np.hypot(u+4,v);a=np.arctan2(v,u+4)
    s.mark('eccentric_turning_faces',disk(u,v,12),(18,246),(24,214),(24,248),sat(.5+.5*np.cos(r*.75+a*2)),coat_shade=t)
    s.mark('nested_burin_arclets',ring(u+4,v,5,1.5)+ring(u-4,v,8,1.5)*sat((-u+4)/3),(146,255),(16,108),(0,114),1-t)
    s.mark('medallion_separation_cuts',line(u,v,-11,-9,8,-11,1.9),(0,98),(180,255),(146,254),t)
    s.mark('turning_spindle_pits',disk(u+4,v,4.1),(56,204),(102,232),(68,204),t)
    s.mark('burnished_border_tabs',box(u-10,v-8,4,4),(96,228),(54,180),(164,255),1-t)

def barleycorn_cuts(s):
    u,v,gx,gy=s.cell(24,30,.5);t=s.rand(gx,gy,461);grain=sat(10-np.hypot(u*.95,(v-2)*.65))*sat((v+11)/3)
    s.mark('barley_grain_facets',grain,(18,246),(24,214),(24,248),sat((u+11)/22),coat_shade=t)
    s.mark('central_grain_keels',line(u,v,0,-10,2,12,2),(146,255),(16,108),(0,114),1-t)
    s.mark('separating_burin_hollows',line(u,v,-9,-9,-7,7,1.8)+line(u,v,7,7,9,-9,1.8),(0,98),(180,255),(146,254),t)
    s.mark('cross_grain_veins',line(u,v,-6,-2,0,3,1.5)+line(u,v,1,3,7,0,1.5),(56,204),(102,232),(68,204),t)
    s.mark('terminal_stipple_beads',disk(u,v-12,4.1),(96,228),(54,180),(164,255),1-t)

def florentine_hatch(s):
    # Tick 17: square filled tiles -> two independent families of interrupted chisel cuts.
    u,v,gx,gy=s.cell(21,29,.5,angle=19);t=s.rand(gx,gy,769);u+=5*(t-.5)
    a=line(u,v,-7,-11,6,9,1.7);shoulder=line(u,v,-5,-11,8,9,1.3)
    p,q,hx,hy=s.cell(31,23,.5,angle=-27);w=s.rand(hx,hy,773);b=line(p,q,-11,-7,10,5,1.9)
    s.mark('first_chisel_hatching',a,(20,240),(28,216),(24,248),sat((v+13)/26),coat_shade=t)
    s.mark('crosscut_engraving',b,(146,255),(16,108),(0,114),sat((p+13)/26),rough_shade=w)
    s.mark('recessed_cut_starts',disk(u+7,v+10,4.2)*a+disk(p+10,q+7,4)*b,(0,100),(180,255),(146,254),1-t)
    s.mark('raised_chisel_shoulders',shoulder*(1-b),(58,204),(102,230),(68,210),w)
    s.mark('crossing_burr_clusters',disk(u-5,v-4,4.1)*sat(b+.3),(96,228),(54,184),(164,255),1-w)

def acanthus_scrolls(s):
    u,v,gx,gy=s.cell(32,32,.5);t=s.rand(gx,gy,467);leaf=sat(12-abs(u-3*np.sin(v*.23))-.4*abs(v))
    s.mark('acanthus_leaf_lobes',leaf,(18,246),(24,214),(24,248),sat((v+15)/30),coat_shade=t)
    s.mark('engraved_leaf_spines',line(u,v,-5,-12,2,9,1.8),(146,255),(16,108),(0,114),1-t)
    s.mark('recessed_scroll_eyes',ring(u-4,v-7,5.4,1.8),(0,98),(180,255),(146,254),t)
    s.mark('lobed_leaf_serrations',line(u,v,-9,-3,-2,0,1.7)+line(u,v,1,4,10,0,1.7),(56,204),(102,232),(68,204),t)
    s.mark('curled_leaf_tips',ring(u+5,v+9,4.7,1.5)*sat((-v-4)/3),(96,228),(54,180),(164,255),1-t)

def celtic_triskeles(s):
    # Tick 18: disconnected ticks -> joined triple spirals with interrupted underpasses.
    u,v,gx,gy=s.cell(31,29,.5);t=s.rand(gx,gy,907);u+=7*(t-.5);v+=7*(s.rand(gx,gy,911)-.5)
    # Tick 18 density iteration: M/R std20.52/16.72; add a fine parallel engraving to each spiral.
    r=np.hypot(u,v);a=np.arctan2(v,u)+t*6.283;spiral=3*a+2.7*np.log(np.maximum(r,1));arms=sat(edge(np.sin(spiral),.58)+edge(np.sin(spiral+.85),.38))*sat(13-r)*sat(r-2)
    s.mark('three_spiral_bands',arms,(18,246),(0,255),(24,248),sat(r/13),coat_shade=t,rough_shade=sat(.5+.5*np.cos(spiral)))
    s.mark('spiral_outer_bevels',edge(np.sin(spiral+.33),.23)*sat(13-r)*sat(r-4),(146,255),(16,108),(0,114),1-t)
    s.mark('interlace_underpass_breaks',line(u,v,-7,-2,5,4,1.8)*arms,(0,100),(180,255),(146,254),t)
    s.mark('central_binding_knot',ring(u,v,4.5,1.7),(56,206),(102,232),(68,212),sat((u+6)/12))
    s.mark('engraver_endpoint_beads',disk(u-11,v-8,4)+disk(u+10,v+9,4),(96,228),(54,184),(164,255),1-t)

def seigaiha_etching(s):
    u,v,gx,gy=s.cell(32,24,.5);t=s.rand(gx,gy,487);r=np.hypot(u,v+8);arch=box(u,v,15,11)*sat((v+8)/3)
    s.mark('nested_wave_arches',arch,(18,246),(24,214),(24,248),sat(.5+.5*np.cos(r*.65)),coat_shade=t)
    s.mark('wave_crest_burin_lines',edge(r-10,1.5)*arch+edge(r-16,1.5)*arch,(146,255),(16,108),(0,114),1-t)
    s.mark('engraved_tide_gutters',line(u,v,-13,10,12,10,1.7),(0,98),(180,255),(146,254),t)
    s.mark('wave_foot_knots',ring(u,v+8,4.4,1.6),(56,204),(102,232),(68,204),t)
    s.mark('crest_stippling_pairs',disk(u-11,v-5,4)+disk(u+11,v-5,4),(96,228),(54,180),(164,255),1-t)

def art_deco_fans(s):
    u,v,gx,gy=s.cell(30,30,.5);t=s.rand(gx,gy,491);r=np.hypot(u,v-10);a=np.arctan2(v-10,u);fan=box(u,v,13,12)*sat((11-v)/3)*sat(16-r)
    s.mark('sunburst_fan_facets',fan,(18,246),(24,214),(24,248),sat(.5+.5*np.cos(a*7)),coat_shade=t)
    s.mark('radiating_fan_inlays',edge(np.sin(a*3.5),.22)*fan,(146,255),(16,108),(0,114),1-t)
    s.mark('recessed_fan_bases',box(u,v-10,4.4,4),(0,98),(180,255),(146,254),t)
    s.mark('stepped_fan_borders',line(u,v,-12,-8,0,-12,1.8)+line(u,v,0,-12,12,-8,1.8),(56,204),(102,232),(68,204),t)
    s.mark('deco_corner_gems',sat(6-abs(u-11)-abs(v-10)),(96,228),(54,180),(164,255),1-t)

def micro_cartouches(s):
    u,v,gx,gy=s.cell(32,28);t=s.rand(gx,gy,499);oval=np.maximum(abs(u)-6,0)**2+v*v;frame=edge(np.sqrt(oval)-8,2.6)
    s.mark('engraved_cartouche_frames',frame,(18,246),(24,214),(24,248),sat((u+16)/32),coat_shade=t)
    s.mark('inner_burnished_shields',sat(8-abs(u)-abs(v)*.65),(146,255),(16,108),(0,114),1-t)
    s.mark('recessed_scroll_tabs',ring(u-11,v,4.3,1.5)+ring(u+11,v,4.3,1.5),(0,98),(180,255),(146,254),t)
    s.mark('central_engraver_flourishes',line(u,v,-5,-4,4,4,1.6),(56,204),(102,232),(68,204),t)
    s.mark('border_witness_beads',disk(u,v-11,4.1),(96,228),(54,180),(164,255),1-t)

def laurel_links(s):
    u,v,gx,gy=s.cell(28,32,.5);t=s.rand(gx,gy,503);left=sat(7-abs(u+5)-abs(v+3)*.55);right=sat(7-abs(u-5)-abs(v-4)*.55)
    s.mark('paired_laurel_leaves',left+right,(18,246),(24,214),(24,248),sat((v+16)/32),coat_shade=t)
    s.mark('interlinked_leaf_stems',line(u,v,-7,-12,7,12,2),(146,255),(16,108),(0,114),1-t)
    s.mark('engraved_leaf_midribs',line(u,v,-9,-8,-2,2,1.4)+line(u,v,2,-1,9,10,1.4),(0,98),(180,255),(146,254),t)
    s.mark('leaf_base_ties',ring(u,v,4.5,1.5),(56,204),(102,232),(68,204),t)
    s.mark('laurel_berry_beads',disk(u+9,v-10,4.1),(96,228),(54,180),(164,255),1-t)

def rope_filigree(s):
    # SPB-105 tick21: isolated rope circles/Peen .683 -> pending; M7 pending. Continuous cable arabesques.
    u,v,gx,gy=s.cell(27,31,.5);t=s.rand(gx,gy,1061);a=v-6*np.sin(s.x*.23);b=u-5*np.sin(s.y*.27)
    rope=edge(a,3.6);cross=edge(b,2.9);twist=sat(.5+.5*np.sin(s.x*.87+a*.5))
    s.mark('twisted_rope_rings',rope+cross,(18,246),(0,246),(24,248),twist,rough_shade=sat(.5+.5*np.cos(s.y*.8+b*.5)),coat_shade=t)
    s.mark('rope_crossing_splices',rope*cross,(146,255),(0,92),(0,114),1-t)
    s.mark('filigree_center_openings',edge(abs(a)-4.3,1.5)+edge(abs(b)-3.7,1.4),(0,98),(180,255),(146,254),t)
    s.mark('soldered_link_tabs',line(u,v,-7,-9,0,-5,2.4),(56,204),(102,232),(68,204),sat((u+13)/26))
    s.mark('terminal_wire_curls',ring(u-8,v-8,4.6,1.9)*sat((-u+8)/3),(96,228),(54,180),(164,255),1-t)
