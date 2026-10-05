"""SPB-105 v2 tick 7: eleven small mineral growth/fracture constructions.
Artistic material interpretations; no claim that RGB spec is mineral color.
"""
import numpy as np
from .geometry import sat,edge,disk,ring,line,box,voronoi

def conchoidal_obsidian(s):
    u,v,wall,t=voronoi(s,28);r=np.hypot(u+5,v-2);a=np.arctan2(v-2,u+5)
    s.mark('shell_fracture_faces',disk(u,v,13),(12,240),(16,224),(24,248),sat(.5+.5*np.cos(r*.62)),coat_shade=t)
    s.mark('arrest_ridges',edge(np.mod(r+2,7)-3.5,1.5)*disk(u,v,13),(142,255),(22,110),(0,96),1-t)
    s.mark('impact_bulbs',disk(u+5,v-2,4.5),(0,102),(148,250),(128,252),t)
    s.mark('hackle_forks',line(u,v,-2,4,9,11,1.4)+line(u,v,3,7,3,13,1.4),(54,206),(66,188),(70,232),t)
    s.mark('sharp_chips',box(u-10,v+8,4,4)*sat((u+v-1)/3),(170,255),(10,66),(148,252),1-t)

def basalt_prisms(s):
    # Tick 17: one repeated hex face -> offset bundles of broken prism columns.
    u,v,gx,gy=s.cell(32,32);t=s.rand(gx,gy,719);a=t*6.283;u+=8*(t-.5);v+=10*(s.rand(gx,gy,727)-.5)
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    d1=np.maximum(abs(cu+5),abs(cv+4)*.866+abs(cu+5)*.5)
    d2=np.maximum(abs(cu-5)*1.1,abs(cv-5)*.866+abs(cu-5)*.5)
    faces=sat(6.5-d1)+sat(7-d2);sides=box(cu+5,cv,5,9)*(1-sat(6.5-d1))
    s.mark('broken_column_caps',faces,(24,252),(24,210),(24,250),sat((cu+12)/24),coat_shade=t)
    s.mark('prismatic_column_sides',sides,(130,255),(16,108),(0,122),sat((cv+10)/20))
    s.mark('bundle_joint_recesses',edge(d1-7.5,1.6)+edge(d2-8,1.4),(0,94),(180,255),(142,254),1-t)
    s.mark('vesicle_socket_pairs',disk(cu+6,cv+4,4)+disk(cu-5,cv-5,4),(54,204),(100,226),(72,216),t)
    s.mark('fractured_root_chips',line(cu,cv,-8,8,1,12,2.1),(98,238),(42,180),(168,255),1-t)

def tourmaline_spindles(s):
    # SPB-105 tick25: paired upright rods / Diatom .643 -> pending; M7 pending. Cross-grown needle populations at independent orientations.
    u,v,gx,gy=s.cell(23,29,.5);t=s.rand(gx,gy,1439);p,q,hx,hy=s.cell(31,21,.5,angle=1.07);w=s.rand(hx,hy,1447)
    first=box(u,v,4.2,11)*sat(14-abs(v)-abs(u));second=box(p,q,4.1,9)*sat(12-abs(q)-abs(p))
    s.mark('elongate_prism_faces',first+second,(18,246),(0,246),(24,248),sat((u+5)/10),rough_shade=sat((q+10)/20),coat_shade=t)
    s.mark('longitudinal_flutes',edge(u,1.7)*first+edge(p,1.7)*second,(146,255),(0,92),(0,114),1-w)
    s.mark('termination_facets',sat(6-abs(u)-abs(v+11))+sat(6-abs(p)-abs(q-9)),(0,98),(180,255),(146,254),t)
    s.mark('broken_roots',line(p,q,-4,-8,4,-6,2.6),(56,204),(102,232),(68,204),w)
    s.mark('crosswise_inclusions',line(u,v,-4,-2,4,1,2)*first+line(p,q,-4,4,4,5,2)*second,(96,228),(54,180),(164,255),1-t)

def pyrite_cuboids(s):
    # SPB-105 tick26 / owner cuboid name proof: twin cubes vs rack .601 -> pending; M7 pending. Dense staircase of intergrown cubic twins.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,1321);top=np.zeros_like(u+v);sides=np.zeros_like(top);seams=np.zeros_like(top);shade=np.zeros_like(top)
    for dx,dy,w,h in ((-7,-4,6.,7.),(1,2,7.,8.),(8,9,5.,6.),(5,-8,5.,6.)):
        x=u-dx;y=v-dy;roof=sat(w-abs(x)-2*abs(y+w*.5));left=sat(x+w)*sat(-x)*sat(y-.5*x)*sat(h-y+.5*x);right=sat(x)*sat(w-x)*sat(y+.5*x)*sat(h-y-.5*x);full=sat(left+right+roof)
        top=top*(1-full)+roof;sides=sides*(1-full)+left+right;shade=shade*(1-full)+.22*left+.66*right+.9*roof
        seams=seams*(1-full)+line(x,y,-w,-w*.5,0,0,1.3)+line(x,y,0,0,w,-w*.5,1.3)+line(x,y,0,0,0,h,1.4)
    s.mark('cubic_twin_roof_faces',top+sides,(18,246),(0,246),(24,246),shade,rough_shade=sat((v+15)/30),coat_shade=t)
    s.mark('penetrant_cube_sidewalls',sides,(56,235),(16,128),(0,132),shade,rough_shade=t)
    s.mark('intergrowth_contact_grooves',seams,(0,100),(180,255),(146,254),1-t)
    s.mark('growth_face_striations',edge(np.mod(u+v*.4,5)-2.5,1.1)*sides,(58,208),(100,230),(68,212),t)
    s.mark('crumbled_sulfide_corners',sat(6-abs(u+10)-abs(v-11)),(96,226),(54,184),(164,255),1-t)

def mica_books(s):
    # SPB-105 tick22: brick rows / Tidal .756 -> pending; M7 pending. Splayed lamellar booklets with torn cleavage ends.
    u,v,gx,gy=s.cell(31,29,.5);t=s.rand(gx,gy,1129);a=t*6.283;cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    leaves=np.zeros_like(u);edges=np.zeros_like(u);shade=np.zeros_like(u)
    for k in (-1,0,1):
        x=cu-k*2;y=cv-k*4;shape=sat(10-abs(x)-abs(y)*.32)*sat(4-abs(y));leaves+=shape;edges+=edge(y-3,1.5)*sat(10-abs(x));shade=np.maximum(shade,shape*(k+1)/2)
    s.mark('cleavage_leaves',leaves,(18,248),(0,246),(16,250),shade,rough_shade=sat((cu+13)/26),coat_shade=t)
    s.mark('book_edges',edges,(160,255),(0,90),(0,108),1-t)
    s.mark('lifted_leaf_corners',sat(6-abs(cu-8)-abs(cv-7)),(62,212),(86,220),(126,250),t)
    s.mark('dark_interleaf_pockets',line(cu,cv,-10,2,-2,2,2.4),(0,100),(162,255),(160,255),t)
    s.mark('fracture_pinholes',disk(cu+4,cv-8,4.1),(12,152),(132,240),(56,184),1-t)

def dendrite_fern(s):
    u,v,gx,gy=s.cell(30,32);t=s.rand(gx,gy,193);u=u+2*np.sin(v*.2+t*3);branch=0
    for y in (-8,0,8):branch+=line(u,v,0,y,10,y-6,1.8)+line(u,v,0,y,-10,y-6,1.8)
    s.mark('primary_growth_stems',box(u,v,3.9,15),(146,255),(20,130),(24,230),sat((v+16)/32),coat_shade=t)
    s.mark('lateral_dendrite_arms',branch,(28,224),(38,226),(16,248),t)
    s.mark('branch_tip_plates',box(u-9,v+12,4,4)+box(u+9,v-4,4,4),(0,98),(170,255),(142,255),1-t)
    s.mark('interarm_deposits',disk(u-6,v-7,4.1),(70,194),(102,244),(56,192),t)
    s.mark('stem_growth_nodes',ring(u,v,4.8,1.7),(178,255),(16,70),(0,80),1-t)

def salt_hoppers(s):
    u,v,gx,gy=s.cell(30,30);t=s.rand(gx,gy,197);d=np.maximum(abs(u),abs(v));band=np.mod(d,4)/4
    s.mark('hopper_terraces',box(u,v,13,13)*(1-box(u,v,4,4)),(8,246),(26,220),(24,250),band,coat_shade=t)
    s.mark('raised_square_rims',edge(d-12,1.8),(160,255),(16,100),(0,118),1-t)
    s.mark('hollow_growth_centers',box(u,v,4.4,4.4),(0,86),(186,255),(158,254),t)
    s.mark('corner_bridges',line(u,v,-10,-10,-4,-4,1.7)+line(u,v,4,4,10,10,1.7),(74,218),(78,202),(70,218),t)
    s.mark('salt_satellites',disk(u-12,v+12,4.1),(22,174),(132,240),(106,248),1-t)

def quartz_clusters(s):
    # Tick 17: repeated single points -> independently splayed three-prism intergrowths.
    u,v,gx,gy=s.cell(32,32);t=s.rand(gx,gy,733);a=t*6.283;u+=8*(s.rand(gx,gy,739)-.5);v+=8*(t-.5)
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    left=sat(4-abs(cu+4+cv*.32)-abs(cv)*.23)*box(cu,cv,13,12)
    right=sat(4-abs(cu-5-cv*.38)-abs(cv+2)*.28)*box(cu,cv,13,12)
    center=sat(4.5-abs(cu)-abs(cv+1)*.21)*box(cu,cv,12,13)
    s.mark('splayed_crystal_prisms',left+right,(14,244),(28,218),(24,246),sat((cv+13)/26),coat_shade=t)
    s.mark('central_intergrowth_faces',center,(146,255),(16,106),(0,118),sat((cu+5)/10),rough_shade=1-t)
    s.mark('pyramidal_termination_edges',line(cu,cv,-4,-7,0,-13,1.8)+line(cu,cv,0,-13,4,-7,1.8),(0,100),(178,255),(144,254),t)
    s.mark('root_inclusion_matrix',box(cu,cv-9,9,4.2)*(1-center),(50,206),(98,232),(68,212),1-t)
    s.mark('healed_prism_fractures',line(cu,cv,-10,-3,7,3,1.4)*(left+right+center),(94,228),(54,184),(164,255),sat((cu+13)/26))

def spherulite_frost(s):
    # SPB-105 tick19 / owner unique construction: polar-star similarity1.0 -> pending; M7 pending.
    # Unequal intergrown fans, each carrying radial lamellae and a scalloped growth front.
    u,v,gx,gy=s.cell(29,31,.5);t=s.rand(gx,gy,941);a=t*6.283
    cu=u*np.cos(a)+v*np.sin(a);cv=-u*np.sin(a)+v*np.cos(a)
    x=cu+5;y=cv+6;r=np.hypot(x,y);angle=np.arctan2(y,x)
    fan=disk(x,y,22)*sat(y/2)*sat((x+6)/3);lamella=sat(.5+.5*np.cos(angle*19+r*.21))
    x2=cu-8;y2=cv-5;r2=np.hypot(x2,y2);a2=np.arctan2(y2,x2)
    inter=disk(x2,y2,12)*sat(-y2/2)*sat((x2+9)/3)
    s.mark('radiating_crystal_fans',fan+inter,(12,248),(0,246),(20,248),lamella,rough_shade=sat(r/20),coat_shade=t)
    s.mark('frozen_growth_fronts',edge(r-18-1.2*np.sin(angle*19),2.5)*fan+edge(r2-10,2)*inter,(136,254),(0,86),(0,114),1-t)
    s.mark('nucleation_pits',disk(x,y,4.3)+disk(x2,y2,4.1),(0,94),(178,255),(146,252),t)
    s.mark('fan_boundary_clefts',line(cu,cv,-5,-6,10,6,2)*fan,(40,190),(120,236),(66,190),t)
    s.mark('satellite_ice_tabs',line(cu,cv,-11,8,-5,12,3)+line(cu,cv,8,-12,12,-8,2.8),(86,232),(50,174),(144,255),1-t)

def botryoidal_buds(s):
    u,v,gx,gy=s.cell(32,28,.5);t=s.rand(gx,gy,211);r=np.minimum(np.hypot(u+5,v),np.hypot(u-5,v-4))
    s.mark('merged_mineral_buds',sat(10-r),(18,246),(26,216),(20,246),sat(r/10),coat_shade=t)
    s.mark('growth_layer_rings',edge(np.mod(r+1,5)-2.5,1.4)*sat(11-r),(134,255),(16,94),(0,112),1-t)
    s.mark('bud_junction_valleys',line(u,v,1,-10,-3,8,2),(0,100),(172,255),(142,252),t)
    s.mark('satellite_nodules',disk(u+11,v-10,4.4),(62,214),(78,206),(76,220),t)
    s.mark('fractured_bud_windows',box(u-8,v+4,4,4),(30,168),(124,236),(170,255),1-t)

def barite_petals(s):
    # SPB-105 tick26 / owner name-true detail: rosette vs diatom .643 -> pending; M7 pending. Open fans of overlapping tabular petals.
    u,v,gx,gy=s.cell(31,29,.5);t=s.rand(gx,gy,1483);petals=np.zeros_like(u+v);edges=np.zeros_like(petals);shade=np.zeros_like(petals)
    for k in range(5):
        a=(k-2)*.39;x=u*np.cos(a)+(v-7)*np.sin(a);y=-u*np.sin(a)+(v-7)*np.cos(a);petal=box(x,y+8,3.5,8)*sat(12-abs(u))*sat(13-abs(v))
        petals=np.maximum(petals,petal);edges+=edge(abs(x)-3.1,1.2)*petal;shade=np.maximum(shade,petal*(.12+k*.19))
    s.mark('tabular_petal_faces',petals,(18,246),(0,246),(24,248),shade,rough_shade=sat((v+14)/28),coat_shade=t)
    s.mark('crossing_crystal_blades',line(u,v,-10,6,9,-3,2.9)*petals,(146,255),(0,92),(0,114),1-t)
    s.mark('petal_growth_rims',edges*petals,(0,98),(180,255),(146,254),t)
    s.mark('matrix_pockets',disk(u,v-8,4.3),(56,204),(102,232),(68,204),t)
    s.mark('cleaved_petal_tips',line(u,v,-10,-10,-3,-12,2.7)+line(u,v,5,-11,12,-8,2.4),(96,228),(54,180),(164,255),1-t)
