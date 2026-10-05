"""SPB-105 v2 tick 6: individually constructed fiber/composite surfaces.
Five authored feature materials per construction; identity/quality gates precede acceptance.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box

def triaxial_basket(s):
    u,v,gx,gy=s.cell(32,28,.5);t=s.rand(gx,gy,101);a=line(u,v,-14,0,14,0,3);b=line(u,v,-8,-12,8,12,3);c=line(u,v,8,-12,-8,12,3)
    # SPB-105 v2 tick 16: M/Cc correlation .909 -> independent resin along each tow.
    s.mark('horizontal_tows',a,(6,118),(124,246),(16,252),t,coat_shade=sat((u+14)/28))
    s.mark('ascending_tows',b,(110,248),(20,116),(16,252),sat((v+14)/28),coat_shade=1-t)
    s.mark('descending_tows',c*sat((abs(v)-3)/3),(36,210),(44,218),(16,252),1-t,coat_shade=sat((u-v+24)/48))
    s.mark('triangular_resin_pockets',sat(6-abs(u)-abs(v-8)),(0,84),(16,68),(0,106),t)
    s.mark('bundle_frays',line(u,v,-13,-9,-6,-4,1.3)+line(u,v,6,4,13,9,1.3),(160,255),(148,255),(146,254),t)

def leno_lock(s):
    # Tick 17: repeating cropped loops -> continuous counter-twisted warp pairs.
    col=np.floor(s.x/24);t=s.rand(col,np.zeros_like(col),757);u=np.mod(s.x,24)-12
    along=s.y+9*t;phase=along*(.17+.035*t);wa=u-5*np.sin(phase);wb=u+5*np.sin(phase)
    row=np.floor(along/16);v=np.mod(along,16)-8;fiber=s.rand(col,row,761);over=sat(.5+np.cos(phase)*2)
    s.mark('countertwisted_warp_pairs',edge(wa,3.8)+edge(wb,3.2),(16,242),(28,224),(24,250),sat((u+11)/22),coat_shade=fiber)
    s.mark('locking_weft_passes',box(u,v,11,3.8)*over,(148,255),(16,108),(0,116),fiber)
    s.mark('underpass_resin_slots',box(u,v,4.1,4.1)*(1-over),(0,102),(180,255),(146,254),1-fiber)
    s.mark('twist_contact_shoulders',edge(wa-2,1.1)*sat(np.sin(phase)*3),(56,208),(104,232),(68,214),fiber)
    s.mark('short_loose_filaments',line(u,v,-10,-6,-4,1,1.2)+line(u,v,6,1,10,7,1.2),(96,226),(54,184),(164,255),1-fiber)

def satin_float(s):
    u,v,gx,gy=s.cell(32,24);t=s.rand(gx,gy,107);shift=np.mod(gx+2*gy,5);x=u+(shift-2)*2
    s.mark('long_float_caps',box(x,v,13,4.4),(96,246),(16,136),(32,238),sat((x+14)/28),coat_shade=t)
    s.mark('buried_weft',box(u,v+7,14,3.9),(4,124),(142,253),(140,254),t)
    s.mark('binding_knots',box(x-8,v,4.1,6),(28,192),(58,200),(16,122),1-t)
    s.mark('resin_channels',line(u,v,-13,10,12,10,1.4),(0,76),(12,70),(0,64),t)
    s.mark('raised_fiber_tips',line(u,v,6,-8,13,-3,1.7),(180,255),(108,234),(104,246),t)

def needle_felt(s):
    u,v,gx,gy=s.cell(26,26);t=s.rand(gx,gy,109);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    s.mark('compressed_fiber_pads',disk(u,v,11.5),(4,144),(88,220),(44,220),t,coat_shade=sat((u+13)/26))
    s.mark('tangled_fibers',line(cu,cv,-11,-5,9,6,1.8)+line(cu,cv,-8,7,10,-4,1.6),(138,255),(22,140),(24,244),sat((cu+13)/26))
    s.mark('needle_punctures',disk(u-6,v+5,4.3),(0,64),(188,255),(170,255),1-t)
    s.mark('fiber_loops',ring(cu,cv-4,5,1.6)*sat(cu/4),(54,224),(44,196),(0,108),t)
    s.mark('raised_nap',line(cu,cv,-8,-9,-2,-2,1.6),(164,254),(120,250),(130,250),1-t)

def chopped_tow(s):
    # SPB-105 tick23: rectangular tow patches .551 -> pending; M7 pending. Broken fiber combs embedded at three directions.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1297);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    bundle=np.zeros_like(u);splits=np.zeros_like(u)
    for dx,dy,ang in ((-4,-6,.15),(5,3,1.2),(-6,8,-.7)):
        x=(cu-dx)*np.cos(ang)+(cv-dy)*np.sin(ang);y=-(cu-dx)*np.sin(ang)+(cv-dy)*np.cos(ang)
        packet=box(x,y,7,4);bundle+=packet;splits+=(edge(y-2,1.1)+edge(y+2,1.1))*packet
    s.mark('angular_tow_chips',bundle,(18,246),(0,246),(24,248),sat((cv+14)/28),rough_shade=sat((cu+14)/28),coat_shade=t)
    s.mark('split_bundle_edges',splits,(146,255),(0,92),(0,114),1-t)
    s.mark('epoxy_windows',sat(6-abs(cu-7)-abs(cv+10)),(0,98),(180,255),(146,254),t)
    s.mark('crossing_offcuts',line(cu,cv,-10,-3,7,7,1.9),(56,204),(102,232),(68,204),t)
    s.mark('torn_fiber_ends',line(cu,cv,-11,10,-5,13,2.4)+line(cu,cv,6,8,12,11,2.4),(96,228),(54,180),(164,255),1-t)

def knitted_loop(s):
    # SPB-105 tick26 / owner unique construction: knit vs weld .617 -> pending; M7 pending. Alternating knit/purl ribs, crossing cable shoulders.
    u,v,gx,gy=s.cell(29,27);t=s.rand(gx,gy,1481);parity=np.mod(gx+gy,2);legs=np.zeros_like(u+v);filaments=np.zeros_like(legs)
    for dx in (-7,7):
        x=u-dx;curve=x-3.2*np.sin(v*.22);outer=edge(curve,3.2)*sat(11-abs(v));legs=np.maximum(legs,outer);filaments+=edge(curve+1.2,1.1)*sat(11-abs(v))
    purl=ring(u,v,6.5,2.8)*sat(5-abs(v));knit=line(u,v,-6,-10,5,10,2.8)+line(u,v,6,-10,-5,10,2.8)
    s.mark('loop_shoulders',legs,(18,246),(0,246),(24,248),sat((u+14)/28),rough_shade=sat((v+13)/26),coat_shade=t)
    s.mark('crossed_loop_legs',knit*(1-parity)+purl*parity,(146,255),(0,92),(0,114),1-t)
    s.mark('underpass_knots',disk(u,v-9,4.3)+disk(u,v+9,4.3),(0,98),(180,255),(146,254),t)
    s.mark('loop_inner_filaments',filaments,(56,204),(102,232),(68,204),t)
    s.mark('loose_stitch_tails',line(u,v,-12,-9,-9,-3,2.1)+line(u,v,9,4,12,10,2.1),(96,228),(54,180),(164,255),1-t)

def chain_stitch(s):
    u,v,gx,gy=s.cell(28,32);t=s.rand(gx,gy,131);r1=np.hypot(u*.75,(v+5)*.85);r2=np.hypot(u*.75,(v-6)*.85)
    s.mark('forward_chain_links',edge(r1-8,2.8)*sat((8-v)/3),(44,242),(18,172),(24,234),sat((u+14)/28),coat_shade=t)
    s.mark('return_chain_links',edge(r2-8,2.2)*sat((v+6)/3),(132,255),(30,128),(0,116),t)
    s.mark('locking_bars',box(u,v,5,4),(0,100),(166,255),(138,254),1-t)
    s.mark('needle_eyelets',ring(u+10,v+11,4.1,1.5),(12,160),(110,244),(68,210),t)
    s.mark('tension_scars',line(u,v,6,-6,12,-12,1.5),(100,232),(62,202),(134,252),1-t)

def spacer_mesh(s):
    u,v,gx,gy=s.cell(30,26,.5);t=s.rand(gx,gy,137);r=np.hypot(u,v)
    s.mark('spacer_crowns',sat(13-abs(u)-abs(v))*(1-disk(u,v,5)),(26,246),(22,212),(20,248),sat((u+v+26)/52),coat_shade=t)
    s.mark('vertical_pillars',box(u+10,v,4,9),(140,254),(16,106),(0,114),t)
    s.mark('buried_diagonals',line(u,v,-12,-10,12,10,1.6)*sat((r-6)/3),(0,114),(170,255),(140,252),1-t)
    s.mark('open_window_rims',ring(u,v,5,1.8),(84,218),(62,186),(70,222),t)
    s.mark('resin_bridge_drops',disk(u-11,v-9,4.2),(4,90),(16,74),(16,80),1-t)

def ply_delamination(s):
    # SPB-105 tick 9: replace regular lapped bands (.72185 vs chevrons)
    # with individually torn, lifted triangular ply packets.
    u,v,gx,gy=s.cell(32,30,.5);t=s.rand(gx,gy,139);a=t*1.4-.7
    cu=u*np.cos(a)+v*np.sin(a);v=-u*np.sin(a)+v*np.cos(a);u=cu
    z=v+2*np.sin(u*.25+t*2);packet=sat(14-abs(u)-.5*abs(z))*sat((z+11)/3)
    s.mark('lifted_ply_shingles',packet,(14,246),(26,202),(36,246),sat((z+10)/20),coat_shade=t)
    s.mark('peeled_lips',edge(z-8,2.1)*box(u,v,13,12),(168,255),(16,80),(0,92),1-t)
    s.mark('exposed_underlayers',box(u+5,z+8,6,4),(0,110),(150,254),(136,252),t)
    s.mark('bridging_filaments',line(u,v,-7,3,2,11,1.4)+line(u,v,-3,3,6,11,1.4),(66,218),(50,174),(86,230),t)
    s.mark('epoxy_blisters',ring(u-8,v+7,4.6,1.7),(28,172),(22,94),(16,86),1-t)

def resin_fray(s):
    u,v,gx,gy=s.cell(32,32);t=s.rand(gx,gy,149);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    # SPB-105 v2 tick 16: R/Cc correlation .971 -> independent pooled-coat gradient.
    s.mark('resin_islands',sat(12-abs(cu)*.65-abs(cv)*1.2-1.8*np.cos(cu*.7)),(6,108),(16,112),(16,252),sat((v+16)/32),coat_shade=sat((cu+12)/24))
    s.mark('frayed_fiber_fans',line(cu,cv,-8,-8,10,2,1.5)+line(cu,cv,-8,-8,6,10,1.5)+line(cu,cv,-8,-8,12,-7,1.5),(134,255),(42,214),(68,250),t)
    s.mark('bundle_collars',ring(cu+5,cv+4,5.4,1.7),(48,224),(16,96),(0,90),1-t)
    s.mark('dry_fiber_knots',disk(cu-5,cv-8,4.4),(0,82),(196,255),(0,108),t)
    s.mark('fractured_resin_tips',box(cu-10,cv+9,4,4),(88,238),(114,240),(108,244),sat((u+16)/32))

def stitched_hex(s):
    # SPB-105 tick21: filled plate/Pangolin .831 -> pending; M7 pending. Open hex seams with offset running stitches.
    u,v,gx,gy=s.cell(27,23,.5);t=s.rand(gx,gy,1097);hex_d=np.maximum(abs(v),abs(u)*.866+abs(v)*.5);seam=edge(hex_d-10,3.3)
    angle=np.arctan2(v,u);stitch=edge(np.sin(angle*12),.5)*seam
    s.mark('quilted_panels',seam,(18,228),(0,246),(24,236),sat((v+11)/22),rough_shade=t,coat_shade=sat((u+13)/26))
    s.mark('seam_stitches',stitch,(160,255),(0,92),(0,122),t)
    s.mark('buttoned_centers',disk(u+2,v-1,4.2),(0,84),(180,255),(132,255),1-t)
    s.mark('tension_pleats',line(u,v,-9,-5,-2,-1,1.9)+line(u,v,9,5,2,1,1.9),(70,212),(76,206),(66,204),t)
    s.mark('thread_return_loops',ring(u-10,v+6,4.2,1.6)*sat((-u+9)/3),(24,184),(116,244),(152,252),1-t)
