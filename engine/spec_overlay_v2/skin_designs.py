"""SPB-105 v2 tick 7: ten biological surface interpretations, 8-32px marks.
Each function has its own carrier and five material-bearing features.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def pangolin_shingles(s):
    u,v,gx,gy=s.cell(30,26,.5);t=s.rand(gx,gy,227);shell=sat(12-np.hypot(u,v-5))*sat((v+11)/3)
    s.mark('keratin_shingles',shell,(18,246),(28,214),(24,248),sat((v+13)/26),coat_shade=t)
    s.mark('scale_overlap_rims',edge(np.hypot(u,v-5)-11,2)*sat((v+9)/3),(138,255),(16,102),(0,106),1-t)
    s.mark('growth_furrows',line(u,v,-7,2,-4,10,1.4)+line(u,v,7,2,4,10,1.4),(46,188),(124,242),(112,252),t)
    s.mark('protected_scale_roots',box(u,v+8,6,4),(0,104),(174,255),(160,254),t)
    s.mark('polished_scale_tips',disk(u,v-11,4.2)*shell,(176,255),(12,80),(60,196),1-t)

def feather_barbules(s):
    # SPB-105 tick22: simple crosshatch / Triaxial .719 -> pending; M7 pending. Curving rachis segments and alternating hooked barbules.
    u,v,gx,gy=s.cell(23,31,.5);t=s.rand(gx,gy,1151);shaft=u-2.8*np.sin(s.y*.2+gx*.9)
    branches=line(u,v,-1,-8,-10,-3,2.1)+line(u,v,2,0,10,6,2.1)+line(u,v,0,8,-9,13,2.1)
    s.mark('barb_shafts',edge(shaft,3.2),(72,246),(0,246),(24,240),sat((shaft+3)/6),rough_shade=sat((v+15)/30),coat_shade=t)
    s.mark('hooked_barbules',branches,(148,255),(0,110),(0,114),1-t)
    s.mark('interlocking_slots',line(u,v,-8,-10,-3,-4,2)+line(u,v,5,4,10,10,2),(0,104),(172,255),(144,254),t)
    s.mark('barbule_hook_heads',ring(u+8,v+3,4.2,1.8)*sat(-v/3)+ring(u-8,v-7,4.2,1.8)*sat(v/3),(44,194),(90,218),(64,226),t)
    s.mark('abraded_shaft_nodes',disk(u-1,v-3,4.1)*edge(shaft,4),(14,158),(132,238),(164,252),1-t)

def crocodile_scutes(s):
    # SPB-105 tick19: Voronoi plate/Kites .965 -> pending; M7 pending. Paired dorsal osteoderm rows.
    u,v,gx,gy=s.cell(31,27,.5);t=s.rand(gx,gy,953);cu=u+2*np.sin(v*.22);cv=v
    left=sat(9-abs(cu+7)-.22*abs(cv));right=sat(7-abs(cu-7)-.35*abs(cv+2))
    plate=(left+right)*sat(11-abs(cv));height=sat(1-np.minimum(abs(cu+7)/9,abs(cu-7)/7))
    s.mark('scute_plates',plate,(16,240),(0,244),(24,250),height,rough_shade=sat((cv+11)/22),coat_shade=t)
    s.mark('raised_dorsal_keels',(edge(cu+7,2.8)+edge(cu-7,2.3))*sat(10-abs(cv)),(156,255),(0,94),(0,106),1-t)
    s.mark('flexible_sutures',edge(cv-11,2.2)+edge(cu,2)*sat(11-abs(cv)),(0,108),(170,255),(130,252),t)
    s.mark('sensory_pits',disk(cu+9,cv+6,4.1)+disk(cu-9,cv-5,4.1),(34,180),(126,242),(68,192),t)
    s.mark('growth_corner_rings',(edge(abs(cu+7)+.22*abs(cv)-6,1.6)+edge(abs(cu-7)+.35*abs(cv+2)-5,1.6))*plate,(88,224),(54,182),(156,255),1-t)

def wing_scale_sockets(s):
    u,v,gx,gy=s.cell(24,32,.5);t=s.rand(gx,gy,233);blade=sat(8-abs(u))*sat((v+12)/3)*sat((13-v)/3)
    s.mark('scale_blades',blade,(18,246),(20,224),(24,248),sat((u+8)/16),coat_shade=t)
    s.mark('longitudinal_ribs',edge(u-3,1.6)*box(u,v,8,12),(146,255),(16,92),(0,112),1-t)
    s.mark('socket_cups',ring(u,v+11,5,2),(0,96),(170,255),(142,252),t)
    s.mark('cross_rib_windows',box(u,v-2,4,4),(52,204),(116,232),(72,210),t)
    s.mark('serrated_blade_ends',line(u,v,-7,10,-2,14,1.6)+line(u,v,2,14,7,10,1.6),(102,232),(62,192),(160,254),1-t)

def coral_polyps(s):
    # SPB-105 v2 tick 15: three unequal budding calices, not another frost rosette.
    u,v,wall,t=voronoi(s,27);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    calice=np.minimum(np.hypot(cu+5,cv+5),np.hypot((cu-6)*1.2,cv-4))
    septa=line(cu,cv,-10,-5,0,-5,1.6)+line(cu,cv,-5,-10,-5,0,1.6)+line(cu,cv,3,1,9,7,1.8)
    s.mark('polyp_septa',sat(7-calice),(18,248),(24,204),(24,246),sat(septa+.2),coat_shade=t)
    s.mark('calice_walls',edge(calice-6.5,1.8),(140,255),(16,106),(0,104),1-t)
    s.mark('central_mouths',disk(cu+5,cv+5,4)+disk(cu-6,cv-4,4),(0,90),(178,255),(148,254),t)
    s.mark('connecting_coenosteum',line(cu,cv,-3,-1,4,7,2.8),(46,194),(102,230),(64,194),t)
    s.mark('budding_sockets',ring(cu+8,cv-8,4.2,1.7),(92,222),(58,192),(164,255),1-t)

def cell_division(s):
    # SPB-105 tick21: repeated paired discs .693 -> pending; M7 pending. Mixed cytokinesis stages.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1033);a=t*6.283;u+=5*(t-.5);v+=5*(s.rand(gx,gy,1039)-.5)
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a);stage=s.rand(gx,gy,1049)
    waist=8-5*stage*np.exp(-cu*cu/18);body=sat(12-abs(cu))*sat(waist-abs(cv));membrane=edge(abs(cv)-waist+1,1.8)*sat(12-abs(cu))
    s.mark('daughter_cell_membranes',body,(18,238),(0,246),(24,248),sat((cv+8)/16),rough_shade=stage,coat_shade=t)
    s.mark('contractile_furrows',edge(cu,2.1)*body*stage,(0,102),(164,255),(132,252),1-t)
    s.mark('membrane_lips',membrane,(152,255),(0,98),(0,110),t)
    s.mark('paired_nuclei',disk(cu+5+stage*2,cv,4.1)+disk(cu-5-stage*2,cv,4.1),(54,200),(90,218),(66,206),1-t)
    s.mark('vesicle_chains',line(cu,cv,-5,-10,2,-11,2.9)+disk(cu-9,cv-9,4),(106,232),(48,172),(158,255),stage)

def leaf_stomata(s):
    # SPB-105 tick21: single oval/pore tiles .723 -> pending; M7 pending. Kidney guard cells and pavement-cell outlines.
    u,v,gx,gy=s.cell(29,27,.5);t=s.rand(gx,gy,1051);a=.4*np.sin(gy*1.9);cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    curve=4+2.7*np.cos(cu*.22);left=edge(cv-curve,3.5)*sat(11-abs(cu));right=edge(cv+curve,3.5)*sat(11-abs(cu));guard=left+right
    s.mark('guard_cell_pairs',guard,(16,246),(0,246),(24,248),sat((cu+11)/22),rough_shade=sat(abs(cv)/9),coat_shade=t)
    s.mark('stomatal_apertures',box(cu,cv,8,2.9),(0,94),(178,255),(140,254),1-t)
    s.mark('raised_pore_lips',(edge(cv-curve+2,1.5)+edge(cv+curve-2,1.5))*sat(10-abs(cu)),(150,255),(0,86),(0,112),t)
    s.mark('cuticle_folds',edge(abs(cv)-11-1.5*np.sin(cu*.7),1.8)+edge(abs(cu)-12-1.2*np.cos(cv*.7),1.6),(62,200),(100,230),(68,200),t)
    s.mark('wax_platelets',sat(6-abs(cu+10)-abs(cv+9)),(100,232),(54,182),(160,255),1-t)

def mushroom_gills(s):
    # SPB-105 tick26 / owner density > size: M7 88.02 but coverage .312 fails; denser unchanged fine gills -> pending.
    u,v,gx,gy=s.cell(26,26);t=s.rand(gx,gy,701);a=t*6.283
    u+=10*(s.rand(gx,gy,703)-.5);v+=10*(s.rand(gx,gy,709)-.5)
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    r=np.hypot(cu,cv+8);theta=np.arctan2(cv+8,cu);fan=disk(cu,cv+8,20)*sat((cv+7)/2)*box(cu,cv,13,13)
    # Tick 18: roughness std 17.6 -> denser fine gills and wider blade states; remeasure.
    ribs=edge(np.sin(theta*9+np.sin(r*.21)),.5)*fan
    s.mark('radial_lamella_blades',ribs,(24,250),(0,255),(24,240),sat(r/22),coat_shade=t,rough_shade=1-t)
    s.mark('short_intercalary_gills',edge(np.sin(theta*18+r*.04),.4)*fan*sat((r-9)/4),(154,255),(16,100),(0,126),1-t)
    s.mark('gill_attachment_roots',ring(cu,cv+8,5,2.3)*fan,(0,106),(176,255),(140,254),t)
    s.mark('spore_print_clusters',disk(cu-7,cv-5,4.1)*fan+disk(cu+7,cv-4,4.1)*fan,(70,216),(70,200),(68,222),1-t)
    s.mark('torn_lamella_tips',line(cu,cv,-10,7,-5,12,2)+line(cu,cv,6,5,11,10,2),(114,240),(36,164),(166,255),sat((cu+13)/26))

def trabecular_pores(s):
    u,v,wall,t=voronoi(s,26);r=np.hypot(u,v);pore=disk(u,v,7.5)
    s.mark('porous_bone_walls',sat((r-7)/3)*sat((14-r)/2),(18,242),(28,218),(24,250),sat((u+13)/26),coat_shade=t)
    s.mark('load_bearing_struts',line(u,v,-11,-8,9,10,2)*sat((r-5)/2),(142,255),(16,102),(0,106),1-t)
    s.mark('marrow_recesses',pore,(0,92),(180,255),(148,254),t)
    s.mark('pore_neck_rims',edge(r-7,1.8),(54,202),(94,226),(66,208),t)
    s.mark('remodeling_pits',disk(u-9,v+7,4.1),(92,226),(60,178),(164,255),1-t)

def retinal_mosaic(s):
    # Tick 18: scalloped rows -> mixed photoreceptor packs with one cone and offset rod pairs.
    u,v,gx,gy=s.cell(27,29);t=s.rand(gx,gy,863);a=t*6.283;u+=9*(s.rand(gx,gy,877)-.5);v+=9*(t-.5)
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a);cone=disk(cu+4,cv,6)
    rods=disk((cu-6)*1.5,np.maximum(abs(cv+4)-3,0),4.5)+disk((cu+1)*1.5,np.maximum(abs(cv-8)-2,0),4.2)
    s.mark('cone_receptor_bodies',cone,(16,244),(28,216),(24,248),sat(np.hypot(cu+4,cv)/6),coat_shade=t)
    s.mark('elongate_rod_pairs',rods,(146,255),(16,108),(0,114),sat((cv+13)/26),rough_shade=1-t)
    s.mark('receptor_membrane_lips',ring(cu+4,cv,6.7,1.5),(0,100),(180,255),(146,254),t)
    s.mark('synaptic_contact_bridges',line(cu,cv,-4,1,1,6,2),(58,206),(102,232),(68,212),1-t)
    s.mark('pigment_granule_pockets',disk(cu+10,cv+10,4.1),(96,228),(54,184),(164,255),sat((cu+13)/26))
