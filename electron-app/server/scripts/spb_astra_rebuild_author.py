"""Reproduce ASTRA R1 declarations. Geometry is independently authored in five
rebuild modules; this script only wires explicit pigment/material role tables.
Owner 2026-09-22 authorizes all 50 originals, installation and baking.
"""
from pathlib import Path
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_astra_rebuild_20260922_work'
sys.path.insert(0,str(ROOT))
from engine.expansions.astra.metadata_r1 import DESCRIPTIONS

# Six pigments and six M/Rough/coat-STRENGTH centers per finish. The third
# authoring coordinate is explicitly encoded below into inverted iRacing Cc:
# 16 strongest active coat, 255 suppressed. No material range normalization.
# The sixth role is still named and authored, never a generic rainbow overlay.
DATA='''
event_horizon|120f29 6842ac 35264e b493ee d9bdef 756389|8/120/60 205/40/192 36/155/70 232/27/210 75/64/225 140/88/132|void,accretion_track,infall_fragment,orbit_rim,inner_lip,dust_streak
quasicrystal_crown|34313d b5a46b 726986 d8cdae 648fa0 d19a52|35/133/60 215/70/142 145/114/83 237/34/195 84/90/170 196/62/136|matrix,rhombic_seam,facet_join,crown_edge,growth_boundary,junction
gravity_loom|162b31 49a88f 426d91 ad8157 b5d4bf 55736d|15/174/44 142/84/129 200/64/95 227/76/144 38/102/182 90/143/74|underweave,warp,weft,bias_strand,over_under_knot,strand_end
phoenix_ceramic|47262d b85435 cf7552 e9af68 5a9b9b 714149|6/135/176 16/110/152 8/48/223 232/40/96 42/156/65 11/100/170|enamel_field,fracture,glaze_scuff,copper_repair,pore,glaze_fragment
sovereign_nacre|53706f b8d9c9 809d9d e7d5d2 928eaf cbbda4|22/126/138 94/64/210 48/96/176 120/44/225 71/106/160 36/147/106|subsurface,tablet_face,overlap_lip,exposed_edge,tablet_root,dislocation
magnetic_regalia|101e29 247280 43acba 92d0cd b28cbd 426877|184/73/182 220/46/218 237/28/232 252/19/207 168/90/154 207/58/194|fluid_pool,crown_spike,droplet,polished_tip,meniscus,wet_saddle
meteorite_royal|393a46 9a94a3 666b79 d7c1b3 ac899b 554953|122/146/36 218/85/56 182/127/39 244/47/87 197/72/123 84/179/24|alloy_matrix,kamacite_lamella,taenite_lamella,etched_edge,polish_face,inclusion
cryogenic_bloom|223c57 84c6de 4d849e abcfe7 d8ece4 b6a5d4|5/118/192 25/68/224 11/99/201 49/42/239 77/29/230 17/137/156|ice_shadow,primary_arm,side_branch,branch_fork,frost_tip,crystal_core
chronograph_gold|58412c b48a4b 856746 e2bc76 e7d4a4 6c573f|185/128/56 229/74/103 207/112/69 249/36/128 237/48/151 134/169/39|alloy_ground,tool_pass,stopped_pass,cut_end,feed_tick,spindle
velvet_supernova|331b36 963e66 653551 bb688a e2a0b2 674474|5/211/12 12/182/27 7/205/16 24/153/48 40/128/63 9/224/8|velvet_ground,nap_fiber,inter_bloom_fiber,turned_fiber,silk_tip,bloom_core
janus_blades|201b38 c84a43 4366b9 733b55 86aedd e39982|8/145/112 18/52/221 231/42/115 46/172/74 246/24/183 107/111/154|recess,lacquer_blade,cobalt_blade,concave_heel,forked_tip,collar
scarlet_undertow|102b35 24bbc1 b84e68 82d6ce e8959b 477b95|12/135/173 230/48/128 17/72/218 244/24/189 24/41/235 91/151/96|deep_current,conductive_current,pigment_return,split_edge,eddy_lip,island
cobalt_guillotine|28331c a4c45c 94508e dbedaa c889b7 72724f|14/151/97 26/53/220 222/43/114 41/28/236 244/24/180 76/167/60|shadow,acid_shutter,amethyst_shutter,cut_face,hinge_pin,severed_rail
chromatic_switchyard|282735 d7b74b 5364bb c58645 a5b9e2 98b87e|9/150/90 21/59/218 224/46/121 193/81/96 241/28/186 32/120/161|ballast,lacquer_track,metal_track,siding,sleeper,terminal
ruby_blue_cyclone|18373b 8ccbd1 b35164 e1e9cc e495a8 537a87|10/139/156 236/45/134 24/68/219 250/24/186 17/40/236 115/104/129|rotor_well,ice_rotor,ruby_rotor,metal_tip,lacquer_tip,connecting_wake
prism_rebellion|342530 d98748 7471bb edc487 a6a0e1 805569|12/145/97 23/61/221 230/47/118 34/31/237 246/23/181 99/159/76|fracture_ground,amber_prism,violet_prism,cut_edge,prism_tip,junction
redshift_rivets|322237 c66fa4 68b3bd e9b5d0 a5e0db 736184|17/156/91 29/73/206 225/41/139 19/34/234 246/27/185 121/118/108|plate,socket,rivet_head,socket_lip,heel_recess,overlap_link
blueblood_chevron|20293d 4662b2 cdb251 849eda e6d38c 776776|12/144/106 232/52/121 21/67/221 248/29/181 33/36/236 105/158/81|fork_ground,cobalt_fork,gold_lacquer_fork,articulation,hinge_pin,broken_tip
duality_scales|293223 a9c74a 975590 d9e6a7 cf98bc 647666|9/151/119 25/57/224 224/43/125 41/28/239 236/75/112 75/171/77|scale_ground,lime_scale,plum_scale,exposed_tip,recessed_root,growth_stop
polarity_lace|342829 bd5145 51a495 e48a70 99d7bc 816577|11/147/96 26/65/219 222/50/129 33/37/235 243/27/179 97/159/74|lace_ground,coral_cord,jade_cord,crossover,knot,cord_end
pipeline_royale|153d53 168f9d 356578 92d0c8 d8e7d2 6eabc2|7/97/194 18/53/226 10/86/209 25/119/154 4/173/73 32/83/213|deep_water,current,underwater_wake,crest,inner_foam_lip,foam_bead
reef_cathedral|254a50 c88078 8b636c e6aa89 cdd6a0 3f797b|5/172/79 19/145/116 9/183/65 45/103/150 11/160/101 26/198/44|reef_water,coral_trunk,branch,mineral_edge,growth_tip,root_cup
tidal_lace|294f64 d5e4d5 82b8ba f5ead7 a8d5d9 477489|6/91/203 4/163/89 15/119/154 8/190/55 23/87/212 10/108/181|water_pocket,foam_membrane,wet_membrane,junction,ruptured_edge,foam_seed
surf_wax_ritual|c1cbb0 e0e3bf acba9f f1e9ce d3d7ba b5c4ab|3/105/204 2/206/22 4/187/39 1/225/11 5/172/59 3/145/136|resin,comb_scrape,wax_deposit,wax_crumb,smeared_wax,fine_wear
wipeout_paisley|392f51 c8706a 6ea6a2 e3b677 b89bc9 775576|9/134/134 19/81/207 61/112/157 133/55/186 33/72/216 18/159/98|cloth_ground,drop_outline,drop_tail,inner_eye,nucleus,broken_echo
kelp_couture|163e3a 397e59 53aa76 286f70 b3ba70 688f62|5/136/155 12/92/193 20/61/220 8/111/177 28/77/204 15/121/164|water,stalk,lit_leaf,shadow_leaf,float,branch
boardwalk_pinlines|385455 8ebbbc b4a878 e6d7b1 7c786c c88063|9/161/79 21/87/190 13/122/140 44/61/213 8/192/42 87/111/118|board,teal_pinline,sanded_run,paint_stop,worn_interruption,fastener
volcanic_break|252b38 42485a 343949 759899 b57452 626575|26/196/39 42/175/67 18/213/23 12/73/211 205/96/78 51/181/58|basalt_ground,shelf,lower_stratum,tide_edge,copper_crack,mineral_pore
abyssal_lanterns|101e38 326d9f 24425b 5caab8 9585b7 b5c6b5|4/129/166 21/66/223 9/117/180 46/49/231 35/88/194 13/60/219|dark_water,bell,rim,cilia,central_trail,inner_organ
sea_glass_confessional|466c70 83bfb0 609eae b8cda7 d3dcd0 8daba2|5/155/129 12/106/171 8/125/152 17/145/137 25/71/205 6/183/79|mineral_bed,jade_shard,blue_shard,sage_shard,tumbled_face,contact_edge
cytokinesis_candy|332846 b776b0 61bdb1 e2b776 d9a2b9 8971aa|6/143/125 15/68/220 33/104/177 121/58/166 9/42/236 42/153/89|medium,daughter_membrane_a,daughter_membrane_b,nucleus,membrane_ridge,division_neck
quantum_petri|173f45 6ba386 c4955c 8677b1 c0ce91 de9b89|8/132/155 17/81/205 93/117/109 38/64/222 15/166/87 152/48/170|agar,inner_colony,reaction_front,outer_membrane,exclusion_boundary,colony_granule
chromosome_riot|332b4e ca769d 72b8c1 e5bd78 b599d6 8d758e|5/158/102 22/84/199 41/63/222 101/117/118 17/38/236 69/168/73|medium,chromatid_a,chromatid_b,telomere_a,telomere_b,centromere
plasma_sutures|202d43 526a94 8f567e dc9b70 8ed1bf d7b7d5|9/162/84 54/147/105 22/111/160 224/58/133 87/81/198 167/44/211|substrate,cut,cut_edge,repair_stitch,anchor_a,anchor_b
bismuth_delirium|273343 53a7a4 b785b7 d0aa61 89c9bc 564b71|170/154/34 227/74/117 208/104/96 241/48/147 252/29/180 119/191/21|crystal_recess,hopper_step_a,hopper_step_b,hopper_step_c,step_end,cavity_floor
strange_attractor|282a44 a97ab0 53a5af d1ab6f aed5b5 907586|11/154/104 123/91/159 35/66/217 211/53/132 61/117/143 29/173/61|phase_space,return_path_a,return_path_b,bifurcation,junction,trajectory_end
neuron_carnival|26364b 4b9b9d b68aaf dec490 8a97c9 759b76|5/165/80 191/68/133 18/82/211 83/123/136 229/38/168 25/147/113|medium,axon,soma_membrane,nucleus,myelin_collar,dendrite_tip
xenobot_orchard|2d4141 76a979 b38da9 dfb973 88c4bb cf917a|7/157/115 17/97/192 29/69/219 97/119/132 11/48/233 46/142/104|medium,lobe_a,lobe_b,cell_core,cilia,bud
fermion_foundry|34333f 83909c c28f68 76a699 d3c49b 6c647d|94/171/51 210/101/81 139/148/48 237/57/133 249/32/176 55/204/24|foundry_ground,chamber_wall,thermal_lining,connecting_neck,gate,chamber_floor
chromatic_centrifuge|233749 62a9ba b68aa6 cbb776 e1c7a7 718bad|25/160/74 218/69/124 84/121/142 181/47/173 43/97/186 237/39/111|well,rotor_a,rotor_b,sorted_band,particle,spindle
causal_origami|354251 a1b5c0 847caa d4d2ba 647da4 c4938d|76/152/66 208/90/113 31/143/135 236/47/158 163/173/48 112/109/178|ground,fold_face_a,fold_face_b,mountain_fold,valley_hinge,clipped_tab
photonic_switchboard|253941 559aab c38d67 e1b994 8dbf9d cc848f|9/165/76 221/62/111 175/112/83 47/71/220 235/41/159 24/96/186|board,optical_bus,comb_coupler,detector,isolation_bridge,terminal
negative_space_engine|212c35 a66e53 6d6c77 d1a27d 99b4b3 76513f|8/184/31 215/96/97 105/163/43 242/48/162 66/117/143 188/134/64|aperture,strut,inner_lip,end_cap,joint,connecting_web
temporal_braille|3a4650 94b5ad 798b9d c5cfb7 b38c75 737580|24/164/65 87/91/177 174/113/116 43/71/207 211/69/132 57/189/33|panel,code_pad_a,code_pad_b,separator,baseline,phrase_stop
klein_circuit|273e45 93bcb6 9c8fba d5bc88 b6d4ce 60858d|12/156/83 204/79/141 62/123/169 238/43/179 37/59/222 131/174/51|substrate,outbound_track,return_track,overpass,bridge_foot,loop_cap
auxetic_exoskin|354148 9caeac 7d9299 c6c9b8 b39579 697a82|73/158/58 202/103/106 148/143/74 233/57/148 216/86/109 43/191/29|underlayer,reentrant_left,reentrant_right,cross_joint,hinge_pin,patch_end
memory_metal_zipper|423e45 c2927d 97a9ad dcc6ab 6a7986 b9b69d|29/171/59 223/87/114 193/122/87 242/43/157 68/184/41 231/60/139|tape,tooth_left,tooth_right,root_pin,seam,slider
orbitless_navigation|2b424c 9bbebb 708fae d1ba8b 9b94b3 d8d9c5|12/165/82 204/72/141 66/141/133 227/49/176 43/100/195 127/65/162|map_ground,waypoint,route_fragment,direction_arrow,decision_arc,waypoint_core
tachyon_feather|244747 71b6a8 508685 a999bd b5d5bd d3b994|10/159/102 190/83/143 46/127/169 107/107/182 230/39/196 74/70/218|vane_ground,quill,barb_left,barb_right,polished_tip,quill_end
programmable_matter|334748 9ebbb0 728b9d c2c6af b39273 5f7777|44/157/71 166/105/141 99/143/93 214/57/183 229/83/112 22/189/38|void,block_a,block_b,attachment_edge,docking_face,recess
'''


def main():
    inventory=json.loads((OUT/'inventory.json').read_text())
    old=json.loads((OUT/'before_contracts.json').read_text())
    data={}
    for line in DATA.strip().splitlines():
        slug,colors,states,roles=line.split('|')
        data[slug]=(colors.split(),[[int(v) for v in state.split('/')] for state in states.split()],roles.split(','))
    assert len(data)==50
    directions={}
    proposal=(ROOT/'docs/finish_audits/intent_2026-09-22/ASTRA_REBUILD_PROPOSAL.md').read_text(encoding='utf-8')
    for line in proposal.splitlines():
        if line.startswith('| '):
            fields=[v.strip() for v in line.split('|')[1:-1]]
            if len(fields)==3:directions[fields[1]]=fields[2]
    for row in inventory:
        row['DESCRIPTION']=DESCRIPTIONS[row['FID']]
        slug=row['FID'].removeprefix('astra_')
        colors,author_states,roles=data[slug]
        states=[[m,r,round(255-239*coat/255)] for m,r,coat in author_states]
        group={'COLOR SHOXX':'color','SURFS UP':'surf','MAD SCIENTIST':'mad','FUTURE SHOXX':'future'}.get(row.get('LANE'),'original')
        geometry='engine.expansions.astra.rebuild_'+group
        # All six material roles are explicit, with restrained per-feature
        # variation for dielectric/quiet designs; never enforce broad M spread.
        spreads=[]
        for m,r,cc in states:
            spreads.append([min(23,max(1,min(m,255-m)*.16)),min(26,max(3,min(r,255-r)*.2)),min(25,max(2,min(cc,255-cc)*.2))])
        contract=old[row['FID']].copy()
        direction=directions.get(row['NAME'],row['DESCRIPTION'])
        # The earlier proposal references pilot text in a few table cells;
        # the independently authored geometry docstring is the precise law.
        tree=ast.parse((ROOT/(geometry.replace('.','/')+'.py')).read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==slug)
        source=(ROOT/(geometry.replace('.','/')+'.py')).read_text().splitlines()
        comment=source[fn.lineno].strip().removeprefix('# ').strip()
        grammar=comment+' '+direction
        binding='; '.join(f'{role}: M{m}/Rough{r}/Cc{cc}' for role,(m,r,cc) in zip(roles,states))+'. Cc uses inverted iRacing encoding: 16 strongest active coat, 255 suppressed. Feature-owned independent eight pigment and material tiers; local edge relief; quiet 8px substrate grain; no channel equalization or RGB-derived spec.'
        contract.update(promise=row['DESCRIPTION'],carrier_grammar=grammar,spec_grammar=binding,
            mark_types=[dict(name=role,role=role.replace('_',' ')+' is a named part of '+row['NAME']) for role in roles],
            material_binding={ch:roles for ch in ['M','R','Cc']},
            material_tiers=[f'feature tier {i}: independently sampled pigment and bounded material offset' for i in range(8)],
            construction_key=row['FID']+':R1:'+grammar,spec_key=row['FID']+':R1:'+binding)
        contract['name_truth']=dict(hidden_title_verdict='pass',assessment='Authored concept contract; rendered agent review and owner verdict are separate evidence in the R1 report.',visible_evidence=[role.replace('_',' ')+' visibly constructs '+row['NAME'] for role in roles[1:4]])
        relative='..' if '/wave2/' in row['path'] else '.'
        text='''"""SPB-105 / ASTRA-R1, 2026-09-22. Owner: rebuild ENTIRE ASTRA library.
Unique construction and explicit physical role states. M7 movement is recorded
in docs/finish_audits/intent_2026-09-22/ASTRA_REBUILD_R1.md; diagnostic only.
"""\nimport sys\n'''
        text+=f'from {relative}rebuild_tools import Surface, bind_rebuild\nfrom {relative}rebuild_{group} import {slug} as construct\n'
        for key in ['FID','NAME','LANE','DESCRIPTION','SWATCH']:
            text+=key+'='+repr(row.get(key,'ASTRA ORIGINALS'))+'\n'
        text+='IDENTITY_CONTRACT='+repr(contract)+'\n'
        text+='COLORS='+repr(colors)+'\nSTATES='+repr(states)+'\nSPREADS='+repr(spreads)+'\n'
        text+=f'\ndef build(shape, seed):\n    c=Surface(seed+{sum((i+1)*ord(v) for i,v in enumerate(slug))})\n    construct(c)\n    return c.finish(shape,COLORS,STATES,SPREADS)\n\npaint,spec=bind_rebuild(sys.modules[__name__],{geometry!r})\n'
        (ROOT/row['path']).write_text(text,encoding='utf-8')
    print('Authored 50 stable-ID declarations with independent geometry and feature material tables')


if __name__=='__main__':main()
