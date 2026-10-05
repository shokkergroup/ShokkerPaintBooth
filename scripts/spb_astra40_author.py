"""Authored source recipes, one independent construction per ASTRA expansion card.

SPB-105 / W1: owner wants more diverse designs, ten in each named lane.
This authoring source generates small reviewable modules, not seed variants.
"""
from pathlib import Path
import json,textwrap
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'engine/expansions/astra/wave2'
RECIPES=[]
def add(lane,slug,name,idea,grammar,marks,code,colors=None):
    RECIPES.append(dict(lane=lane,slug=slug,name=name,idea=idea,grammar=grammar,marks=marks,code=textwrap.dedent(code).strip(),colors=colors))

add('COLOR SHOXX','janus_blades','Janus Blades','Red lacquer valleys against blue polished blade faces.',
 'Offset scimitar blades with concave heels, forked tips and interrupted transverse collars.',
 ['valley','blade face','concave heel','forked tip','collar','cutback'],'''
 ix,iy,u,v,g=frames(x,y,29,23,seed,.19,.5)
 j=hash01(ix,iy,seed+111);u+=.1*(g-.5)
 d=u+.55*v*v-.11*np.sin(v*7)
 lab=np.zeros(x.shape,np.int32);lab[d>-.17]=1;lab[d>.17]=2
 lab[(d>.02)&(d<.22)&(v>.12)]=3
 lab[(abs(v)<.12)&(u<.22)]=4;lab[(u<-.18)&(v<-.17)]=5
 a=.5+.5*np.sin(d*8);b=np.clip(v+.5,0,1)
''')
add('COLOR SHOXX','scarlet_undertow','Scarlet Undertow','Scarlet diffuse hooks lock into ultramarine reflective troughs.',
 'Counter-running hooked gutters with rolled triangular breakers and alternating lip notches.',
 ['trough','hook','rolled lip','breaker','notch','backwash'],'''
 ix,iy,u,v,g=frames(x,y,24,31,seed,-.31,.35);j=hash01(ix,iy,seed+13)
 f=v+.25*np.sin(u*6.2)+.09*(g-.5)
 lab=np.zeros(x.shape,np.int32);lab[f>.02]=1;lab[f>.27]=2
 lab[(f<-.18)&(u>.05)]=3;lab[(f>.05)&(u<-.22)]=4
 lab[(abs(f)<.14)&(u>.24)]=5
 a=.5+.5*np.cos(f*9);b=.5+.5*np.sin(u*5+v*2)
''')
add('COLOR SHOXX','cobalt_guillotine','Cobalt Guillotine','Blue chrome shutters cut across vermilion enamel hinges.',
 'Unequal diagonal shutter plates with clipped corners, vertical kerfs and isolated rectangular pivots.',
 ['hinge bed','shutter','clipped corner','kerf','pivot','bevel'],'''
 ix,iy,u,v,g=frames(x,y,32,19,seed,.0,.5);j=hash01(ix,iy,seed+37)
 f=np.maximum(abs(u+.22*v)*1.6,abs(v)*1.1)
 lab=np.zeros(x.shape,np.int32);lab[f<.43]=1;lab[(f<.43)&(u+v>.3)]=2
 lab[(abs(u-.06)<.13)&(v<.12)]=3
 lab[(u<-.18)&(v>.02)&(v<.38)]=4;lab[(f<.43)&(f>.3)&(v<0)]=5
 a=np.clip(1-f,0,1);b=u+.5
''')
add('COLOR SHOXX','chromatic_switchyard','Chromatic Switchyard','Red service beds and blue conductive routes compete under daylight.',
 'Staggered right-angle switch tracks, dead-end spurs and broad junction contact pads.',
 ['service bed','through track','elbow','spur','contact pad','insulator'],'''
 ix,iy,u,v,g=frames(x,y,27,27,seed,0,.23);j=hash01(ix,iy,seed+5)
 h=abs(v+.19);k=abs(u-.18)
 lab=np.zeros(x.shape,np.int32);lab[h<.14]=1;lab[(k<.14)&(v>-.19)]=2
 lab[(abs(u+.22)<.13)&(v<.11)]=3
 lab[(abs(u-.18)<.2)&(abs(v-.2)<.18)]=4
 lab[(u<-.15)&(v>.15)]=5
 a=.5+.5*np.cos(np.minimum(h,k)*9);b=.5+.5*np.sin((u-v)*4)
''')
add('COLOR SHOXX','ruby_blue_cyclone','Ruby Blue Cyclone','Ruby satin wakes wrap blue mirror-metal rotor vanes.',
 'Three curved micro-vane lobes around a triangular hub, interrupted by unequal exhaust pockets.',
 ['wake','vane','hub','exhaust','vane crown','root fillet'],'''
 ix,iy,u,v,g=frames(x,y,31,30,seed,.11,.5);j=hash01(ix,iy,seed+15)
 d=np.hypot(u,v);ang=np.arctan2(v,u);f=np.sin(3*ang+10*d)
 lab=np.zeros(x.shape,np.int32);lab[(f>.05)&(d<.49)]=1
 lab[d<.16]=2;lab[(f<-.52)&(d>.27)]=3
 lab[(f>.64)&(d>.22)&(d<.43)]=4;lab[(d<.28)&(u<-.03)]=5
 a=.5+.5*f;b=np.clip(d*1.7,0,1)
''')
add('COLOR SHOXX','prism_rebellion','Prism Rebellion','Wide red prisms and blue mirrored facets challenge color dominance.',
 'Oblique scalene triangular facets cut by nonuniform barycentric seams and displaced crystal inclusions.',
 ['crystal bed','long facet','short facet','cleavage','inclusion','shoulder'],'''
 ix,iy,u,v,g=frames(x,y,25,29,seed,.47,.31);j=hash01(ix,iy,seed+47)
 f=u+.43*v+.12*(g-.5);q=v-.58*u
 lab=np.zeros(x.shape,np.int32);lab[f>-.1]=1;lab[(q>.08)&(f>.03)]=2
 lab[(abs(q+.15)<.13)&(u<.26)]=3
 lab[(abs(u+.2)+abs(v-.18))<.21]=4;lab[(q<-.2)&(f>.1)]=5
 a=.5+.5*np.sin(f*6);b=np.clip(q+.5,0,1)
''')
add('COLOR SHOXX','redshift_rivets','Redshift Rivets','Red recessed enamel surrounds blue domed metallic rivet faces.',
 'Eccentrically punched overlapping D-shaped rivets with broad crescent flanges and squared sockets.',
 ['recess','rivet face','flange','socket','punch','overlap lip'],'''
 ix,iy,u,v,g=frames(x,y,26,28,seed,-.13,.5);j=hash01(ix,iy,seed+27)
 d=np.hypot(u+.08,v);f=np.maximum(d,abs(v)*1.2)
 lab=np.zeros(x.shape,np.int32);lab[(f<.41)&(u<.28)]=1
 lab[(f>.3)&(f<.48)&(u<.1)]=2
 lab[(u>.11)&(v<-.1)]=3;lab[(abs(u+.08)<.14)&(abs(v)<.15)]=4
 lab[(v>.22)&(u>-.13)]=5
 a=np.clip(1-d*1.3,0,1);b=.5+.5*np.sin(u*6-v*2)
''')
add('COLOR SHOXX','blueblood_chevron','Blueblood Chevron','Sapphire fork tines alternate with bright red return cuts.',
 'Asymmetric interlocking Y-forks, with broad shoulders, offset necks and detached heel blocks.',
 ['return cut','left tine','right tine','neck','shoulder','heel'],'''
 ix,iy,u,v,g=frames(x,y,30,24,seed,0,.5);j=hash01(ix,iy,seed+91)
 f=abs(u)-.48*v-.16
 lab=np.zeros(x.shape,np.int32);lab[(abs(f)<.16)&(u<0)]=1
 lab[(abs(f)<.16)&(u>=0)]=2;lab[(abs(u)<.14)&(v<-.03)]=3
 lab[(abs(u)>.2)&(v>.17)]=4;lab[(abs(u)<.18)&(v>.24)]=5
 a=.5+.5*np.cos(f*8);b=v+.5
''')
add('COLOR SHOXX','duality_scales','Duality Scales','Blue polished arrow scales overlap a red diffuse under-skin.',
 'Pointed shield scales with concave roots, branching central ridges and stepped side flanges.',
 ['under skin','shield','ridge','root','side flange','tip'],'''
 ix,iy,u,v,g=frames(x,y,23,32,seed,.17,.5);j=hash01(ix,iy,seed+51)
 f=abs(u)*1.25+v*.5
 lab=np.zeros(x.shape,np.int32);lab[(f<.43)&(v>-.3)]=1
 lab[(abs(u)<.14)&(v>-.2)]=2;lab[(v<-.15)&(abs(u)<.29)]=3
 lab[(f>.25)&(f<.46)&(v>.03)]=4;lab[(abs(u)<.22)&(v>.22)]=5
 a=np.clip(1-f,0,1);b=.5+.5*np.sin(v*5+u*3)
''')
add('COLOR SHOXX','polarity_lace','Polarity Lace','Red saddle membranes stretch between blue reflective boundary threads.',
 'Open hyperbolic saddles divided by two disconnected sinuous crossings and corner tension pads.',
 ['membrane','saddle arm','crossing','tension pad','open pore','seam'],'''
 ix,iy,u,v,g=frames(x,y,28,25,seed,.29,.12);j=hash01(ix,iy,seed+61)
 f=u*v*5+.2*np.sin(u*7)
 lab=np.zeros(x.shape,np.int32);lab[f>.07]=1;lab[f<-.22]=2
 lab[(abs(u)>.25)&(abs(v)>.23)]=3
 lab[(abs(u)<.17)&(abs(v)<.18)]=4;lab[(abs(f)<.14)&(v>.09)]=5
 a=.5+.5*np.sin(f*5);b=.5+.5*np.cos((u-v)*5)
''')

add('SURFS UP','pipeline_royale','Pipeline Royale','Turquoise barrel curls, creamy broken lips and deep-blue backwash.',
 'Dense open surf-barrel spirals swept into hooked foam lips, wedge troughs and spray shoulders.',
 ['backwash','barrel','foam lip','spray shoulder','trough','return curl'],'''
 ix,iy,u,v,g=frames(x,y,32,29,seed,-.22,.47);j=hash01(ix,iy,seed+131)
 d=np.hypot(u+.12,v-.02);ang=np.arctan2(v-.02,u+.12)
 f=d-.2-.07*ang
 lab=np.zeros(x.shape,np.int32);lab[(f<.18)&(f>-.06)]=1
 lab[(abs(f-.14)<.1)&(v>.0)]=2;lab[(u>.17)&(v>.13)]=3
 lab[(v<-.2)&(u<.1)]=4;lab[(d<.22)&(u<-.02)]=5
 a=np.clip(1-abs(f)*2,0,1);b=.5+.5*np.sin(ang)
''','12314c 039eae f2e6bd b6ece9 103e70 17c9b0')
add('SURFS UP','reef_cathedral','Reef Cathedral','Rose coral fans and turquoise polyps set into warm reef stone.',
 'Five-finger asymmetric coral crowns rise from branching stems with fleshy sockets and sand pockets.',
 ['reef stone','coral crown','finger','stem','polyp socket','sand pocket'],'''
 ix,iy,u,v,g=frames(x,y,30,32,seed,.07,.5);j=hash01(ix,iy,seed+171)
 d=np.hypot(u,v-.06);ang=np.arctan2(v-.06,u)
 r=.26+.1*np.cos(5*ang+.6*g)
 lab=np.zeros(x.shape,np.int32);lab[d<r]=1;lab[(d<r)&(d>r-.12)]=2
 lab[(abs(u)<.13)&(v<.08)]=3;lab[d<.15]=4
 lab[(u>.22)&(v<-.19)]=5
 a=np.clip(1-d*1.4,0,1);b=.5+.5*np.cos(ang*3)
''','184c54 e78883 f3c3aa 3eb0a9 614ca2 e6cd95')
add('SURFS UP','tidal_lace','Tidal Lacework','Pearl-white foam walls enclose aquamarine water pockets.',
 'Offset irregular rounded polygon foam chambers with double walls, triangular junctions and collapsed openings.',
 ['water pocket','foam wall','wet wall','junction','collapsed opening','foam raft'],'''
 ix,iy,u,v,g=frames(x,y,31,27,seed,-.14,.5);j=hash01(ix,iy,seed+143)
 u+=.12*(g-.5);v+=.1*(j-.5)
 d=(abs(u)**3+abs(v)**3)**(1/3)
 lab=np.zeros(x.shape,np.int32);lab[d>.29]=1;lab[(d>.2)&(d<.31)]=2
 lab[(abs(u)+abs(v))>.67]=3;lab[(u>.2)&(v<-.09)]=4
 lab[(u<-.14)&(v>.14)&(d<.37)]=5
 a=np.clip(d*2,0,1);b=.5+.5*np.sin((u+v)*7)
''','0b736f eaf6de 82cdb8 fffff0 176984 cbe8a1')
add('SURFS UP','surf_wax_ritual','Surf Wax Ritual','Mint wax crumbs, chalky scrape fans and sun-yellow resin scars.',
 'Broken comb-scraped wax platelets, staggered trapezoid crumbs and cross-cut application scars.',
 ['resin bed','wax platelet','scrape','crumb','wax crown','cross cut'],'''
 ix,iy,u,v,g=frames(x,y,21,29,seed,.36,.27);j=hash01(ix,iy,seed+173)
 f=v+.18*abs(u)+.14*(g-.5)
 lab=np.zeros(x.shape,np.int32);lab[(f>-.27)&(f<.25)]=1
 lab[(abs(u+.12)<.15)&(v>-.18)]=2;lab[(u>.14)&(v<-.11)]=3
 lab[(f>.1)&(f<.36)]=4;lab[(abs(v+.19)<.13)&(u<0)]=5
 a=.5+.5*np.cos(f*7);b=.5+.5*np.sin(u*6)
''','a07838 e5efb6 76c5ab f6deb0 f8ffdb 568e86')
add('SURFS UP','wipeout_paisley','Wipeout Paisley','Coral-red surf drops curl through pale aqua resin.',
 'Leaning teardrop wakes with off-centre eyelets, beaked noses and bifurcated tails.',
 ['resin','surf drop','eyelet','beak','tail','wake rim'],'''
 ix,iy,u,v,g=frames(x,y,27,31,seed,-.27,.5);j=hash01(ix,iy,seed+153)
 d=np.hypot((u+.4*v)*1.15,v+.05)
 f=d+.22*v
 lab=np.zeros(x.shape,np.int32);lab[f<.36]=1
 lab[((u+.04)**2+(v+.12)**2)<.025]=2
 lab[(u>.08)&(v>.11)&(u+v<.5)]=3
 lab[(abs(u+.25*v)<.14)&(v>.15)]=4;lab[(f>.24)&(f<.39)&(u<0)]=5
 a=np.clip(1-f*1.5,0,1);b=.5+.5*np.sin((u+v)*6)
''','8ccdcc ee7366 285786 f4c492 d63d73 d9ead6')
add('SURFS UP','kelp_couture','Kelp Couture','Sea-green kelp blades and amber floats trail through cobalt water.',
 'Alternating lanceolate fronds branch from offset stems; broad axils cradle oval buoyancy bladders.',
 ['water','frond','stem','bladder','axil','frond tip'],'''
 ix,iy,u,v,g=frames(x,y,28,32,seed,.24,.0);j=hash01(ix,iy,seed+183)
 f=abs(u)-.45*abs(v)-.05
 lab=np.zeros(x.shape,np.int32);lab[(f<.19)&(f>-.06)]=1
 lab[abs(u)<.13]=2;lab[((u-.22)**2+(v+.17)**2)<.027]=3
 lab[(abs(v)<.14)&(u<-.1)]=4;lab[(f>.07)&(abs(v)>.24)]=5
 a=.5+.5*np.cos(f*10);b=v+.5
''','0d4660 22ae80 548b47 e7b951 117776 94d592')
add('SURFS UP','boardwalk_pinlines','Boardwalk Pinlines','Vintage surfboard pinlines in sea-glass, cream, orange and plum.',
 'Staggered pointed mini-stringers with asymmetrical paired rails, fin sockets and chopped tail blocks.',
 ['deck','left rail','right rail','stringer','fin socket','tail block'],'''
 ix,iy,u,v,g=frames(x,y,26,32,seed,-.1,.5);j=hash01(ix,iy,seed+193)
 f=abs(u)+.4*abs(v)
 lab=np.zeros(x.shape,np.int32);lab[(f<.46)&(u<0)]=1
 lab[(f<.46)&(u>=0)]=2;lab[(abs(u)<.14)&(abs(v)<.35)]=3
 lab[(u>.03)&(v>.15)&(u<.33)]=4;lab[(v<-.22)&(f<.4)]=5
 a=np.clip(1-f,0,1);b=.5+.5*np.cos(v*5)
''','f1d2a0 339d9e ed864f e9edc7 804871 c97f38')
add('SURFS UP','volcanic_break','Volcanic Break','Obsidian reef steps meet glowing copper cracks and teal tide pools.',
 'Angular fractured lava shelves with rectangular shear steps, triangular tide pools and mineral-filled fault shoulders.',
 ['lava','shelf','fault','tide pool','shear step','mineral crust'],'''
 ix,iy,u,v,g=frames(x,y,29,24,seed,.38,.2);j=hash01(ix,iy,seed+163)
 f=u+.32*v+.12*(g-.5);q=v-.25*abs(u)
 lab=np.zeros(x.shape,np.int32);lab[(f>-.3)&(q<.24)]=1
 lab[abs(f-.1)<.14]=2;lab[(f<-.07)&(q>.02)]=3
 lab[(u>.13)&(v<-.18)]=4;lab[(q>.17)&(q<.39)]=5
 a=.5+.5*np.sin(f*7+q*2);b=np.clip(q+.5,0,1)
''','153040 343b59 d99255 24b4b4 796c99 8de0ce')
add('SURFS UP','abyssal_lanterns','Abyssal Lanterns','Cobalt comb-jelly bells with turquoise cilia and rose internal lobes.',
 'Compressed jelly bells with diverging ciliary meridians, paired gastric lobes and separated skirt flaps.',
 ['abyss','bell','cilia','gastric lobe','skirt','oral channel'],'''
 ix,iy,u,v,g=frames(x,y,32,28,seed,.03,.5);j=hash01(ix,iy,seed+203)
 d=np.sqrt((u*1.18)**2+(v*.83)**2);ang=np.arctan2(v,u)
 lab=np.zeros(x.shape,np.int32);lab[(d<.43)&(v<.31)]=1
 lab[(abs(u)-.22*abs(v)>.12)&(d<.43)]=2
 lab[(abs(u)<.23)&(abs(v)<.2)]=3
 lab[(v>.14)&(abs(u)>.13)&(d<.47)]=4;lab[(abs(u)<.13)&(v>.03)]=5
 a=np.clip(1-d*1.5,0,1);b=.5+.5*np.cos(ang*2)
''','142657 277ab1 78edeb dd77b7 706aca eed5be')
add('SURFS UP','sea_glass_confessional','Sea Glass Confessional','Tumbled aqua, lime and pink sea-glass chips in warm beach mineral.',
 'Dense mixed quadrilateral and scalene shards with diagonal cleavage planes, frosted shoulders and embedded pebbles.',
 ['sand mineral','glass face','cleavage','frosted shoulder','pebble','tumbled tip'],'''
 ix,iy,u,v,g=frames(x,y,23,27,seed,.17,.36);j=hash01(ix,iy,seed+213)
 f=np.maximum(abs(u+.35*v),abs(v-.19*u))
 lab=np.zeros(x.shape,np.int32);lab[f<.4]=1;lab[(f<.4)&(u-v>.02)]=2
 lab[(f>.27)&(f<.43)&(u<.04)]=3
 lab[((u+.22)**2+(v-.24)**2)<.025]=4;lab[(v<-.19)&(u>.0)&(f<.43)]=5
 a=np.clip(1-f*1.3,0,1);b=.5+.5*np.sin((u+v)*4)
''','beaa79 57c7bf 8dc963 d7eed7 db95ac 6393c3')

add('MAD SCIENTIST','cytokinesis_candy','Cytokinesis Candy','Dividing candy cells, pinched membranes and prismatic daughter nuclei.',
 'Paired asymmetric cell lobes joined by pinched waists, with eccentric daughter nuclei and cleavage furrows.',
 ['matrix','daughter cell','membrane','nucleus','cleavage furrow','waist'],'''
 ix,iy,u,v,g=frames(x,y,32,25,seed,.12,.5);j=hash01(ix,iy,seed+301)
 d=np.minimum(np.hypot(u-.18,v),np.hypot(u+.18,v*.9))
 lab=np.zeros(x.shape,np.int32);lab[d<.31]=1;lab[(d>.2)&(d<.34)]=2
 lab[((abs(u)-.18)**2+(v+.04)**2)<.019]=3
 lab[(abs(u)<.13)&(abs(v)>.1)]=4;lab[(abs(u)<.16)&(abs(v)<.16)]=5
 a=np.clip(1-d*2,0,1);b=.5+.5*np.sin((u+v)*4)
''')
add('MAD SCIENTIST','quantum_petri','Quantum Petri Carnival','Reaction fronts bloom around off-centre nuclei in a chromatic growth medium.',
 'Irregular nested reaction fronts with kidney-shaped cores, open colony margins and broad diffusion bridges.',
 ['medium','reaction front','colony core','margin','bridge','daughter bud'],'''
 ix,iy,u,v,g=frames(x,y,31,32,seed,-.18,.5);j=hash01(ix,iy,seed+311)
 d=np.hypot(u+.1*np.sin(v*7),v);a0=np.arctan2(v,u)
 f=d+.05*np.cos(a0*3)
 lab=np.zeros(x.shape,np.int32);lab[f<.43]=1;lab[f<.22]=2
 lab[(f>.28)&(f<.43)&(u>.03)]=3
 lab[(abs(v)<.13)&(u<.12)]=4;lab[((u-.18)**2+(v+.19)**2)<.024]=5
 a=np.clip(f*2,0,1);b=.5+.5*np.sin(u*5-v*3)
''')
add('MAD SCIENTIST','chromosome_riot','Chromosome Riot','Split chromosome arms flash contrasting candy-metal materials.',
 'Unequal bent X-chromatids with central constrictions, forked telomeres and detached spindle plates.',
 ['cytoplasm','chromatid','centromere','telomere','spindle','split arm'],'''
 ix,iy,u,v,g=frames(x,y,28,31,seed,.26,.35);j=hash01(ix,iy,seed+321)
 f=abs(abs(u)-.56*abs(v)-.025)
 lab=np.zeros(x.shape,np.int32);lab[f<.15]=1
 lab[(abs(u)<.18)&(abs(v)<.16)]=2
 lab[(f<.18)&(abs(v)>.25)]=3;lab[(abs(u)>.25)&(abs(v)<.17)]=4
 lab[(u>.03)&(v<-.12)&(f<.18)]=5
 a=np.clip(1-f*2.6,0,1);b=.5+.5*np.sin((u-v)*4.5)
''')
add('MAD SCIENTIST','plasma_sutures','Plasma Sutures','Stitched plasma channels cut through a chemically stained ceramic skin.',
 'Jagged branched discharge channels tied by alternating broad staples and asymmetrical molten pools.',
 ['ceramic skin','discharge','staple','pool','branch','slag'],'''
 ix,iy,u,v,g=frames(x,y,25,32,seed,-.39,.0);j=hash01(ix,iy,seed+331)
 f=u-.24*np.sin(v*6.3)
 lab=np.zeros(x.shape,np.int32);lab[abs(f)<.15]=1
 lab[(abs(v+.13)<.13)&(u>-.27)]=2;lab[((u-.2)**2+(v-.2)**2)<.04]=3
 lab[(abs(u+v*.7)<.15)&(v>.01)]=4;lab[(u<-.22)&(v<-.13)]=5
 a=.5+.5*np.cos(f*8);b=v+.5
''')
add('MAD SCIENTIST','bismuth_delirium','Bismuth Delirium','Hopper crystal stairs stack into impossible candy-metal courtyards.',
 'Off-centre orthogonal hopper terraces, broken square corners and broad ascending stair treads.',
 ['courtyard','outer terrace','inner terrace','stair','broken corner','seed'],'''
 ix,iy,u,v,g=frames(x,y,32,32,seed,0,.19);j=hash01(ix,iy,seed+341)
 d=np.maximum(abs(u+.07),abs(v-.04))
 lab=np.zeros(x.shape,np.int32);lab[d>.32]=1;lab[(d>.17)&(d<=.32)]=2
 lab[(u>.0)&(abs(v)<.14)]=3;lab[(u<-.19)&(v>.12)]=4
 lab[(abs(u+.07)<.14)&(abs(v-.04)<.14)]=5
 a=np.clip(d*1.7,0,1);b=.5+.5*np.sin(u*4+v*3)
''')
add('MAD SCIENTIST','strange_attractor','Strange Attractor','Folded orbital traces and bifurcation lobes fill a chaotic micro-reactor.',
 'Asymmetric figure-eight return maps with bifurcating inner tongues, saddle crossings and isolated capture pockets.',
 ['reactor','return lobe','tongue','saddle','capture pocket','fold'],'''
 ix,iy,u,v,g=frames(x,y,31,26,seed,-.07,.5);j=hash01(ix,iy,seed+351)
 f=(u*u+v*v)**2-.12*(u*u-v*v)
 lab=np.zeros(x.shape,np.int32);lab[f<.014]=1;lab[(f<.004)&(u>0)]=2
 lab[(abs(u)<.15)&(abs(v)<.18)]=3
 lab[((u+.27)**2+(v+.16)**2)<.024]=4;lab[(f>.006)&(f<.026)&(v>.02)]=5
 a=.5+.5*np.sin((u*u-v*v)*16);b=.5+.5*np.sin(u*4+v*6)
''')
add('MAD SCIENTIST','neuron_carnival','Neuron Carnival','Chromatic synapses exchange polished pulses through branching axons.',
 'Three-way asymmetric neuron branches, triangular soma, flat synaptic terminals and offset axon collars.',
 ['substrate','axon','soma','terminal','collar','dendrite'],'''
 ix,iy,u,v,g=frames(x,y,32,29,seed,.14,.5);j=hash01(ix,iy,seed+361)
 d=np.minimum(abs(u-.43*v),abs(v+.22))
 lab=np.zeros(x.shape,np.int32);lab[d<.12]=1
 lab[(abs(u)*1.2+abs(v+.08))<.29]=2
 lab[(u>.19)&(v<-.12)]=3;lab[(abs(u+.13)<.13)&(v>.12)]=4
 lab[(abs(u+.63*v)<.12)&(v>.01)]=5
 a=.5+.5*np.cos(d*8);b=.5+.5*np.sin((u+v)*5)
''')
add('MAD SCIENTIST','xenobot_orchard','Xenobot Orchard','Soft robotic lobes, ciliated pads and candy-coloured artificial organelles.',
 'Four-lobed soft robotic bodies with unequal cilia pads, rectangular contractile seams and split organelles.',
 ['bath','soft body','cilia pad','organelle','seam','bud'],'''
 ix,iy,u,v,g=frames(x,y,29,31,seed,.31,.22);j=hash01(ix,iy,seed+371)
 d=np.hypot(u,v);ang=np.arctan2(v,u);r=.3+.085*np.sin(4*ang+.8)
 lab=np.zeros(x.shape,np.int32);lab[d<r]=1;lab[(d<r+.04)&(d>r-.1)]=2
 lab[(abs(u)<.14)&(v<.13)&(v>-.25)]=3
 lab[(abs(v-.08)<.13)&(u>.0)]=4;lab[((u+.24)**2+(v-.2)**2)<.024]=5
 a=np.clip(1-d*1.3,0,1);b=.5+.5*np.sin(ang*.8+d*3)
''')
add('MAD SCIENTIST','fermion_foundry','Fermion Foundry','Interlocking chemical necks and metallic saddle walls form a prismatic foundry.',
 'Alternating truncated hexagonal cavities meet broad T-neck walls, bevel terraces and central dielectric plugs.',
 ['cavity','hex wall','neck','bevel','plug','junction'],'''
 ix,iy,u,v,g=frames(x,y,30,26,seed,.0,.5);j=hash01(ix,iy,seed+381)
 d=np.maximum(abs(v),abs(u)*.866+abs(v)*.5)
 lab=np.zeros(x.shape,np.int32);lab[d>.3]=1
 lab[(abs(u)<.14)&(v>.08)]=2;lab[(d>.17)&(d<.31)]=3
 lab[(abs(u)<.16)&(abs(v)<.15)]=4;lab[(u<-.19)&(v<-.1)]=5
 a=np.clip(d*1.8,0,1);b=.5+.5*np.sin(u*5-v*3)
''')
add('MAD SCIENTIST','chromatic_centrifuge','Chromatic Centrifuge','Laboratory rotor crescents separate prismatic phases around eccentric hubs.',
 'Two sweeping crescent rotor scoops surround an offset rectangular axle and a pair of broad discharge mouths.',
 ['rotor bath','scoop','phase rim','axle','discharge','collector'],'''
 ix,iy,u,v,g=frames(x,y,32,27,seed,-.26,.32);j=hash01(ix,iy,seed+391)
 d=np.hypot(u,v);ang=np.arctan2(v,u);f=np.sin(2*ang+7*d+.3)
 lab=np.zeros(x.shape,np.int32);lab[(f>-.05)&(d<.48)]=1
 lab[(f>.7)&(d>.18)&(d<.48)]=2
 lab[(abs(u+.04)<.15)&(abs(v)<.17)]=3
 lab[(f<-.55)&(d>.23)]=4;lab[(u>.18)&(v>.13)]=5
 a=.5+.5*f;b=np.clip(d*1.6,0,1)
''')

add('FUTURE SHOXX','causal_origami','Causal Origami','Folded silver membranes reveal violet undersides and ion-blue hinge cuts.',
 'Oblique accordion facets terminate in clipped triangular tabs and unequal raised valley hinges.',
 ['underside','mountain fold','valley fold','hinge','tab','clipped corner'],'''
 ix,iy,u,v,g=frames(x,y,32,22,seed,.51,.0);j=hash01(ix,iy,seed+411)
 f=u+.35*abs(v)
 lab=np.zeros(x.shape,np.int32);lab[(f>-.27)&(f<.09)]=1
 lab[(f>.09)&(f<.4)]=2;lab[(abs(v)<.14)&(u<.16)]=3
 lab[(u<-.17)&(v>.13)]=4;lab[(u>.14)&(v<-.17)]=5
 a=.5+.5*np.cos(f*7);b=v+.5
''','393253 bcdde4 816bab 2fcfc6 e4b28c 657ba5')
add('FUTURE SHOXX','photonic_switchboard','Photonic Switchboard','Crimson optical buses, ivory detector pads and lime split prisms on dark ceramic.',
 'Open T-couplers with broad comb teeth, triangular split prisms and isolated detector pads. No closed frame or orbital enclosure.',
 ['ceramic board','bus waveguide','comb tooth','split prism','detector pad','isolation gate'],'''
 ix,iy,u,v,g=frames(x,y,27,25,seed,.08,.37);j=hash01(ix,iy,seed+421)
 f=v+.09*np.sin(u*5)
 lab=np.zeros(x.shape,np.int32);lab[abs(f)<.16]=1
 lab[(u<-.12)&(u>-.42)&(v>.01)&(v<.42)]=2
 lab[(abs(u+.01)+abs(v+.03)*.7)<.22]=3
 lab[(u>.14)&(u<.46)&(v<-.07)&(v>-.4)]=4
 lab[(u>.09)&(u<.39)&(v>.2)]=5
 a=.5+.5*np.cos(f*6);b=.5+.5*np.sin(u*5+v*3)
''','131a22 ea4847 e7f0d8 9be337 715874 9fd5bf')
add('FUTURE SHOXX','negative_space_engine','Negative Space Engine','Copper hourglass struts frame dark apertures and ice-silver capture plates.',
 'Re-entrant hourglass cavities divided by broad saddle struts, asymmetric jaw plates and diagonal return braces.',
 ['aperture','strut','jaw plate','return brace','saddle','clamp'],'''
 ix,iy,u,v,g=frames(x,y,29,32,seed,-.17,.18);j=hash01(ix,iy,seed+431)
 f=abs(u)-.54*abs(v)
 lab=np.zeros(x.shape,np.int32);lab[(f>-.04)&(f<.19)]=1
 lab[(abs(v)>.25)&(abs(u)<.31)]=2
 lab[(abs(u+v*.6)<.14)&(u<0)]=3
 lab[(abs(u)<.16)&(abs(v)<.15)]=4;lab[(u>.21)&(abs(v)<.2)]=5
 a=.5+.5*np.cos(f*8);b=.5+.5*np.sin(v*5)
''','0d1f3c cc815c c1e5e3 7e87b4 309eac edc69b')
add('FUTURE SHOXX','temporal_braille','Temporal Braille','Raised silver code pads and plum recesses form a tactile future inscription.',
 'Irregular L-shaped tactile code pads, paired rectangular stops and embossed semicircular data sockets.',
 ['recess','code pad','stop','socket','connector','chamfer'],'''
 ix,iy,u,v,g=frames(x,y,25,31,seed,.09,.33);j=hash01(ix,iy,seed+441)
 lab=np.zeros(x.shape,np.int32)
 lab[((abs(u+.15)<.15)&(v>-.3))|((abs(v+.18)<.15)&(u<.28))]=1
 lab[(u>.1)&(v>.1)&(v<.41)]=2
 d=np.hypot(u-.12,v+.04);lab[(d<.23)&(u>-.02)]=3
 lab[(abs(v-.11)<.13)&(u<.11)]=4;lab[(u<-.17)&(v>.22)]=5
 a=np.clip(1-d*1.3,0,1);b=.5+.5*np.cos(u*6+v*2)
''','453252 b8d1cc e7ac6c 787ec6 66bab6 e4e4c1')
add('FUTURE SHOXX','klein_circuit','Klein Circuit','Continuous platinum return channels fold through violet buried tunnels.',
 'Quadratic return tracks cross broad underpasses and split into squared side pockets, never simple concentric arcs.',
 ['substrate','return track','underpass','side pocket','crossover','terminal'],'''
 ix,iy,u,v,g=frames(x,y,32,28,seed,-.3,.5);j=hash01(ix,iy,seed+451)
 f=v-.8*u*u+.19;q=u+.5*v*v
 lab=np.zeros(x.shape,np.int32);lab[abs(f)<.14]=1;lab[abs(q)<.14]=2
 lab[(u>.14)&(v>.11)]=3;lab[(abs(f)<.19)&(abs(q)<.18)]=4
 lab[(u<-.18)&(v<-.14)]=5
 a=.5+.5*np.cos(f*8);b=.5+.5*np.sin(q*6)
''','26353f c5d7d7 946fa2 2d9cb7 f4cf96 77c2ad')
add('FUTURE SHOXX','auxetic_exoskin','Auxetic Exoskin','Re-entrant metal links open into teal cavities with orange hinge clamps.',
 'Inward-pointing hexagonal struts form anti-honeycomb waist openings, paired ribs and flat hinge shoes.',
 ['cavity','reentrant strut','rib','hinge shoe','joint','return notch'],'''
 ix,iy,u,v,g=frames(x,y,32,26,seed,.04,.5);j=hash01(ix,iy,seed+461)
 f=abs(u)+.57*abs(v)-.3
 lab=np.zeros(x.shape,np.int32);lab[abs(f)<.12]=1
 lab[(abs(u)>.27)&(abs(v)<.21)]=2
 lab[(abs(v)>.22)&(abs(u)<.2)]=3
 lab[(abs(u)<.16)&(abs(v)<.16)]=4;lab[(u<-.16)&(v>.08)]=5
 a=.5+.5*np.cos(f*9);b=.5+.5*np.sin((u-v)*4)
''','145869 a6bdbf 65579c ee995c 49c9b3 dbdfb3')
add('FUTURE SHOXX','memory_metal_zipper','Memory Metal Zipper','Rose metal locking teeth and sapphire flexures knit a programmable seam.',
 'Opposed staggered rectangular teeth interdigitate through broad serpentine necks and separate locking sockets.',
 ['flexure','upper tooth','lower tooth','neck','socket','locking lip'],'''
 ix,iy,u,v,g=frames(x,y,28,25,seed,.32,.5);j=hash01(ix,iy,seed+471)
 lab=np.zeros(x.shape,np.int32)
 lab[(u<.03)&(v>-.1)]=1;lab[(u>-.02)&(v<.16)]=2
 lab[(abs(v+.2*np.sin(u*5))<.13)]=3
 lab[(u<-.17)&(v<-.17)]=4;lab[(u>.14)&(v>.19)]=5
 a=.5+.5*np.cos((u-v)*4);b=.5+.5*np.sin(u*6+v*2)
''','294971 dfa99c b9d9d4 7368a7 153949 f3d0a6')
add('FUTURE SHOXX','orbitless_navigation','Orbitless Navigation','Silver compass kites navigate bronze bridges and deep indigo route wells.',
 'Nested offset diamond waypoints with asymmetric route bridges, clipped compass tips and central rectangular wells.',
 ['route bed','waypoint','bridge','well','compass tip','clipped wing'],'''
 ix,iy,u,v,g=frames(x,y,31,31,seed,-.21,.36);j=hash01(ix,iy,seed+481)
 d=abs(u+.05)+abs(v-.03)*.85
 lab=np.zeros(x.shape,np.int32);lab[(d>.2)&(d<.48)]=1
 lab[(abs(v-.03)<.13)&(u>.02)]=2
 lab[(abs(u+.05)<.14)&(abs(v-.03)<.15)]=3
 lab[(v<-.14)&(d<.49)]=4;lab[(u<-.2)&(v>.06)]=5
 a=np.clip(1-d,0,1);b=.5+.5*np.sin(u*4-v*5)
''','2c3c60 b4e0e1 d1a763 5a5095 72a4cd b6c08c')
add('FUTURE SHOXX','tachyon_feather','Tachyon Feather','Iridescent quill plates and ice-blue barbs form a future flight surface.',
 'Offset feather quills support asymmetric swept barbs, broad root sockets and detached triangular barbules.',
 ['underwing','barb','quill','root socket','barbule','tip'],'''
 ix,iy,u,v,g=frames(x,y,26,32,seed,-.37,.22);j=hash01(ix,iy,seed+491)
 f=v+.55*abs(u)
 lab=np.zeros(x.shape,np.int32);lab[(f>-.24)&(f<.14)]=1
 lab[(abs(u)<.14)&(v<.34)]=2
 lab[(abs(u)<.23)&(v<-.18)]=3;lab[(u>.16)&(v>.05)]=4
 lab[(v>.14)&(abs(u)<.24)]=5
 a=.5+.5*np.cos(f*7);b=.5+.5*np.sin(u*6-v*2)
''','293d55 64cabd d5bb86 6958a2 a1dfe0 e9c1d3')
add('FUTURE SHOXX','programmable_matter','Programmable Matter','Cooperative ceramic blocks switch between teal joints and bright metal faces.',
 'Interlocking stepped polyomino plates alternate hooked corner lugs, recessed square memory cells and diagonal face cuts.',
 ['joint','polyomino face','corner lug','memory cell','face cut','latch'],'''
 ix,iy,u,v,g=frames(x,y,30,29,seed,.0,.31);j=hash01(ix,iy,seed+501)
 lab=np.zeros(x.shape,np.int32)
 lab[((u>-.31)&(u<.14))|((v>-.13)&(v<.28))]=1
 lab[(u>.12)&(v>.08)]=2;lab[(abs(u+.11)<.14)&(abs(v+.1)<.14)]=3
 lab[(u+v>.15)&(u<.29)&(v<.33)]=4
 lab[(u<-.17)&(v>.15)]=5
 a=.5+.5*np.sin(u*4+v*3);b=.5+.5*np.cos(u*5-v*4)
''','1f5967 bbd3ce d7a573 515385 6cbebf e8b6c0')

def main():
    DEST.mkdir(exist_ok=True)
    flips=[
      ('e94234 357cfa f95b57 5195ff e12b36 2463db','Scarlet lacquer against electric cobalt metal.'),
      ('ff831c 16e5e5 ffaf30 57ffff e85912 04b3ce','Tangerine enamel hooks against brilliant cyan metal troughs.'),
      ('eb27b5 9be529 ff64d6 bdf54a b51b8e 78c522','Hot magenta shutters against acid-lime reflective hinges.'),
      ('833fef f5dd28 ae73ff fff272 6521c8 d5b60c','Ultraviolet service beds against solar-yellow conductive routes.'),
      ('ea3434 b8f3fa ff6860 edffff c5162d 6adfe8','Scarlet satin wakes against ice-white blue rotor vanes.'),
      ('1ae593 ff8739 58ffd1 ffb979 06ae7b ed581c','Electric emerald prisms against vivid orange mirrored facets.'),
      ('2863ed f15bba 6897ff ff9bd6 143cca d83197','Royal-blue enamel recesses against bubblegum-pink metallic rivets.'),
      ('eed93a 255fdc fffa87 548fff cab31b 173cbf','Lemon lacquer return cuts against royal-blue fork tines.'),
      ('cfc7ff bff522 f4eaff e3ff67 937fe0 88c512','Lilac-white under-skin against fluorescent-chartreuse arrow scales.'),
      ('20cbba f24636 7af7e2 ff8b5f 06a19e c6202b','Turquoise saddle membranes against vermilion reflective tension arms.')]
    for n,r in enumerate(RECIPES):
        fid='astra_'+r['slug'];lane=r['lane']
        if lane=='COLOR SHOXX':
            r['colors'],r['idea']=flips[n]
            r['name']={1:'Chromatic Undertow',2:'Spectrum Guillotine',4:'Bipolar Cyclone',6:'Dichroic Rivets',7:'Switchblade Chevron'}.get(n,r['name'])
        # W3 visual rejection: ordered organic motifs read as stamped wallpaper.
        # These growth/particle subjects now have irregular nearest-site
        # territories and finish-specific orientation, density and geometry.
        scattered={1:(23,26,.7),4:(28,26,5.2),5:(24,26,1.8),6:(24,26,4.4),9:(25,24,2.2),
          10:(28,27,1.4),11:(26,29,4.8),12:(25,24,3.4),13:(21,27,2.4),14:(25,28,3.7),15:(25,29,1.1),
          17:(26,24,2.8),18:(28,26,2.3),19:(23,24,4.2),20:(29,24,5.7),21:(27,29,4.7),22:(25,28,3.8),
          23:(24,28,2.1),24:(29,28,1.7),25:(28,24,4.3),26:(29,26,2.9),27:(26,28,5.8),28:(27,24,2.2),29:(29,24,4.8),
          31:(25,24,.7),32:(27,29,.8),33:(24,28,1.2),37:(28,28,2.0),38:(24,29,1.4)}
        if n in scattered:
            import re
            px,py,tilt=scattered[n]
            r['code']=re.sub(r'frames\(x,y,[^\n;]+\)',f'sites(x,y,{px},{py},seed+{701+n*79},{tilt})',r['code'],count=1)
            r['grammar']='Irregular growth-site placement (no stamped rows). '+r['grammar']
        colors=r['colors'] or ('e94234 357cfa f95b57 5195ff e12b36 2463db' if lane=='COLOR SHOXX' else 'e868a4 58ccbd a79aef f0c85d 6994ef e7af98')
        # Each role is mapped individually, not a single blanket spec field.
        # Named role centres differ for every construction. Variations have
        # different physical jobs (foam vs glass vs metal vs soft membrane).
        state_sets=[
         [(11,153,27),(145,42,25),(16,214,239),(53,87,73),(205,114,147),(89,196,202)],
         [(32,187,193),(183,93,65),(227,38,219),(69,163,124),(131,231,29),(10,119,247)],
         [(7,63,26),(28,205,229),(156,119,91),(228,174,179),(60,231,144),(197,44,47)],
         [(128,91,36),(16,226,222),(73,159,112),(216,72,181),(169,195,245),(239,26,77)],
         [(19,75,23),(195,94,204),(51,222,137),(231,35,71),(109,183,242),(171,136,28)],
         [(4,103,41),(149,67,142),(218,135,233),(62,221,79),(195,28,21),(96,176,188)],
         [(38,189,144),(221,49,215),(131,122,28),(13,223,94),(193,87,244),(72,163,177)],
         [(53,229,206),(182,96,133),(237,27,44),(16,74,24),(108,165,237),(217,198,90)],
         [(12,137,185),(138,72,36),(241,35,226),(87,221,91),(196,118,247),(41,184,26)],
         [(27,203,133),(175,44,29),(228,86,218),(71,156,79),(122,233,243),(211,117,178)],
         [(17,199,178),(211,66,39),(118,136,235),(237,28,109),(56,224,65),(174,95,210)],
         [(31,174,56),(195,43,223),(68,211,124),(242,102,31),(152,151,187),(104,231,246)],
         [(9,228,212),(233,32,71),(145,127,27),(56,181,238),(196,81,161),(97,212,108)],
         [(40,188,96),(225,75,242),(91,138,42),(179,223,188),(248,32,127),(17,108,27)],
         [(23,213,231),(201,39,138),(142,92,29),(240,173,67),(69,237,179),(112,125,247)],
         [(15,176,68),(237,56,203),(98,134,143),(175,225,33),(221,93,242),(60,214,113)],
         [(47,224,131),(183,69,26),(231,122,226),(104,36,177),(19,193,246),(149,164,82)],
         [(29,187,222),(159,88,59),(227,26,149),(61,223,196),(198,116,24),(112,157,241)],
         [(8,123,178),(216,45,235),(102,202,69),(245,90,27),(54,234,119),(174,148,211)],
         [(36,232,93),(197,62,28),(239,124,185),(81,172,247),(142,28,139),(20,207,55)],
         [(25,218,184),(228,31,49),(164,119,219),(62,183,114),(205,72,27),(98,237,246)],
         [(14,166,237),(208,57,123),(243,113,24),(67,228,192),(130,142,81),(182,24,216)],
         [(31,215,72),(194,39,232),(236,128,144),(96,185,25),(12,98,207),(158,228,105)],
         [(55,196,209),(221,83,41),(116,137,173),(186,27,244),(21,223,98),(243,158,25)],
         [(18,231,136),(239,34,88),(156,91,238),(44,172,24),(203,126,181),(109,205,63)],
         [(37,193,247),(178,73,123),(228,143,41),(85,225,197),(240,27,85),(13,120,28)],
         [(10,168,162),(207,38,27),(244,108,227),(94,219,106),(167,144,245),(52,88,68)],
         [(26,222,78),(231,52,197),(123,128,244),(76,173,31),(191,26,127),(17,213,209)],
         [(51,182,232),(214,44,73),(163,125,26),(13,238,171),(242,98,218),(98,167,117)],
         [(16,209,118),(188,61,238),(237,142,52),(73,232,190),(126,109,27),(220,28,144)]]
        states=state_sets[max(0,n-10)]
        if lane=='COLOR SHOXX':
            # Red matte/diffuse vs blue narrow-lobe conductor. Reverse four
            # experiments so either pigment can own the reflection population.
            states=[(12,183,236),(247,27,230),(30,218,184),(231,59,201),(57,143,90),(204,92,150)]
            if n in (2,4,6,9): states=[(246,29,237),(15,185,239),(227,68,183),(41,223,178),(195,99,145),(68,148,92)]
        if lane=='COLOR SHOXX':
            binding='; '.join(f'{mark}: M{st[0]} / R{st[1]} / Cc{st[2]} priors, eight per-object tiers and local relief' for mark,st in zip(r['marks'],states))
            binding+='; pigment value follows local material relief plus its object brightness and facet relief, with hue-preserving gamut compression. Roughness then follows that exact pigment value; conductor/dielectric populations remain separate.'
        elif lane=='MAD SCIENTIST':
            binding='Local pigment-concentration coordinates drive 82% of each material coordinate; 18% is the named role prior. M=4+251u, R/Cc=16+239u. '
            binding+='; '.join(f'{mark}: concentration prior {st}, continuous within-feature chroma and material gradients spanning more than eight shades' for mark,st in zip(r['marks'],states))
        else:
            binding='; '.join(f'{mark}: M{st[0]} and Cc{st[2]} priors with eight per-object material tiers' for mark,st in zip(r['marks'],states))
            binding+='; roughness follows actual feature pigment value: R=clamp((255*(0.21+0.59*(1-Ypaint))-0.2126*M-0.0722*Cc)/0.7152,16,255). No unrelated decorative spec field.'
        if lane!='MAD SCIENTIST':binding+=' Clearcoat combines 25% role prior with 75% independent per-object coat tier, plus local relief.'
        binding+=' Final monotonic levels span M4–255 / R16–255 / Cc16–255 after reconstruction, preserving each feature silhouette.'
        old_neighbors=['meteorite_royal','event_horizon','sovereign_nacre','gravity_loom','magnetic_regalia','quasicrystal_crown','chronograph_gold','cryogenic_bloom','sovereign_nacre','velvet_supernova',
          'event_horizon','velvet_supernova','magnetic_regalia','meteorite_royal','event_horizon','cryogenic_bloom','sovereign_nacre','phoenix_ceramic','magnetic_regalia','quasicrystal_crown',
          'magnetic_regalia','event_horizon','gravity_loom','phoenix_ceramic','quasicrystal_crown','chronograph_gold','cryogenic_bloom','velvet_supernova','sovereign_nacre','event_horizon',
          'meteorite_royal','gravity_loom','quasicrystal_crown','sovereign_nacre','chronograph_gold','gravity_loom','meteorite_royal','quasicrystal_crown','cryogenic_bloom','sovereign_nacre']
        near_new=[30,10,39,31,29,19,18,35,16,32,1,27,28,38,20,26,8,23,6,5,14,10,26,17,39,34,15,11,12,4,0,3,9,36,25,7,33,5,13,24]
        neighbors=[('astra_'+RECIPES[near_new[n]]['slug'],'Different construction: '+RECIPES[near_new[n]]['grammar']),
          ('astra_'+old_neighbors[n],'Replace that related material reference with this independent construction: '+r['grammar'])]
        text=f'''"""SPB-105 / ASTRA W1. Owner: 'more diverse designs'. M7: new -> pending native evidence."""
import sys
import numpy as np
from .materials import grid,frames,sites,hash01,palette,pack,bind_wave,contract
FID={fid!r}
NAME={r['name']!r}
LANE={lane!r}
DESCRIPTION={r['idea']!r}
SWATCH={'#'+colors.split()[1]!r}
IDENTITY_CONTRACT=contract(FID,NAME,DESCRIPTION,{r['grammar']!r},
 {[(m.replace(' ','_'),m+' forms the named '+r['name']+' structure') for m in r['marks']]!r},
 {binding!r},{neighbors!r},
 'https://www.pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory')
def build(shape,seed):
    x,y=grid(shape)
{textwrap.indent(r['code'],'    ')}
    return pack(shape,lab,a,b,g,j,palette(*{colors.split()!r}),{states!r},{n},mad={lane=='MAD SCIENTIST'},flip={lane=='COLOR SHOXX'},brightness={.56 if n==6 else .32})
paint,spec=bind_wave(sys.modules[__name__])
'''
        (DEST/(r['slug']+'.py')).write_text(text,encoding='utf-8')
    mods=','.join(r['slug'] for r in RECIPES)
    (DEST/'__init__.py').write_text('"""Forty independent ASTRA expansion constructions. SPB-105 / W1."""\nfrom . import ('+mods+')\nMODULES=('+mods+',)\nBY_ID={m.FID:m for m in MODULES}\n',encoding='utf-8')
    (ROOT/'_astra40_work/identities.json').write_text(json.dumps(RECIPES,indent=2))
    print('Authored',len(RECIPES),'independent modules and pre-render identity contracts')
if __name__=='__main__':main()
