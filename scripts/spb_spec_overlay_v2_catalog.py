"""Synchronize authored construction modules, identity records and the live UI catalog.
This creates no geometry: each named function owns its feature masks/materials.
Existing reviewed name verdicts are preserved; new constructions start pending.
"""
from pathlib import Path
import ast,json,pprint,sys
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'engine/spec_overlay_v2'
FAMILIES={'machine':'machine','weave':'weave','crystal':'crystal','skin':'skin','liquid':'liquid','crack':'crack','optical':'optical','engraved':'engraved','track':'track','experimental':'experimental'}
REFERENCES={
 'machine':'https://videos.sandvik.coromant.com/machining-guide-step-7-specify',
 'weave':'https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf',
 'crystal':'https://www.nist.gov/itl/math/visualization-dendritic-growth',
 'skin':'https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/',
 'liquid':'https://www.nature.com/articles/nature10344',
 'crack':'https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/',
 'optical':'https://support.iracing.com/support/solutions/articles/31000153524-paint-textures',
 'engraved':'https://www.breguet.com/en/guilloche-according-breguet',
 'track':'https://support.iracing.com/support/solutions/articles/31000153524-paint-textures',
 'experimental':'https://arxiv.org/abs/2303.10798'}

def main():
    catalog=json.loads((BASE/'catalog.json').read_text());items={p['id']:p for p in catalog['items']}
    for module,family in FAMILIES.items():
        path=BASE/(module+'_designs.py')
        if not path.exists():continue
        source=path.read_text(encoding='utf-8');tree=ast.parse(source)
        for fn in tree.body:
            if not isinstance(fn,ast.FunctionDef):continue
            slug=fn.name;pid='spov2_'+slug;name=slug.replace('_',' ').title()
            marks=[node for node in ast.walk(fn) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='mark']
            names=[ast.literal_eval(m.args[0]) for m in marks];assert len(names)>=5
            words=[n.replace('_',' ') for n in names]
            promise=name+' assembles '+', '.join(words[:-1])+' and '+words[-1]+'.'
            neighbors=[p for p in catalog['items'] if p['family']==family and p['id']!=pid][:2]
            if len(neighbors)<2:neighbors+=[p for p in catalog['items'] if p['family']!=family][:2-len(neighbors)]
            old=BASE/'designs'/(slug+'.py');verdict='pending';old_contract=None
            if old.exists():
                for node in ast.parse(old.read_text(encoding='utf-8')).body:
                    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IDENTITY_CONTRACT' for t in node.targets):
                        old_contract=ast.literal_eval(node.value);verdict=old_contract['name_truth']['hidden_title_verdict']
            contract={'schema':'spb-finish-identity/1','finish_id':pid,'display_name':name+' - spec overlay','promise':promise,
              'paint_policy':'Preserve source paint bytes; no color profile is generated.',
              'reference_physics':{'mechanism':'Decorative interpretation of '+family+' surface processes; the authored masks and material tiers are an artistic construction, not a measured physical simulation.','sources':[REFERENCES[family]]},
              'carrier_grammar':promise+' Geometry is independently authored in '+path.name+':'+slug+'.',
              'spec_grammar':'Named feature masks bind independent M/R/Cc intervals to '+', '.join(words)+'.',
              'native_scale_px':[8,32],
              'mark_types':[{'name':names[i],'role':words[i].capitalize()+' use M/R/Cc intervals '+str([ast.literal_eval(a) for a in m.args[2:5]])+' in their own geometry.'} for i,m in enumerate(marks)],
              'material_binding':{k:names for k in ('M','R','Cc')},
              'material_tiers':['substrate','recess','satin','polish','coat break','coat pool','transition lip','crest'],
              'nearest_neighbors':[{'finish_id':p['id'],'difference':name+' must visibly separate through '+', '.join(words[:3])+' and the remaining named marks, not color or parameter changes.'} for p in neighbors],
              'name_truth':{'visible_evidence':[w+' construction' for w in words],'hidden_title_verdict':verdict},
              'construction_key':'spec-v2/'+slug+'/independent-feature-carrier','spec_key':'spec-v2/'+slug+'/named-material-bindings'}
            if old_contract and [m['name'] for m in old_contract['mark_types']]==names:
                contract['name_truth']=old_contract['name_truth']
            text='"""SPB-105 v2 tick 6: '+name+'. Identity declared before rendering/scoring."""\nfrom ..'+module+'_designs import '+slug+'\nfrom ..renderer import build_renderer\n\nIDENTITY_CONTRACT = '+pprint.pformat(contract,width=105,sort_dicts=False)+'\n\nrender = build_renderer('+slug+', IDENTITY_CONTRACT)\n'
            old.write_text(text,encoding='utf-8')
            items[pid]={'id':pid,'name':name,'desc':promise,'family':family,'defaults':{},'defaultOpacity':100,'defaultBlendMode':'normal','defaultRange':40,'defaultChannels':'MRC','render_version':2,'seed':42,'surfaceIntent':'spec_driven','legacy':False}
    # Proof modules own their prose; keep the served description on that contract.
    for path in (BASE/'designs').glob('*.py'):
        source=path.read_text(encoding='utf-8')
        if 'from ..proof_designs import ' not in source:continue
        for node in ast.parse(source).body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IDENTITY_CONTRACT' for t in node.targets):
                contract=ast.literal_eval(node.value);items[contract['finish_id']]['desc']=contract['promise']
    catalog['items']=list(items.values());catalog['version']='2026-09-06-v2'
    (BASE/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    (ROOT/'js/spec-overlays/catalog-data.js').write_text('/* Generated from the canonical overlay catalog. */\nglobalThis.SPB_SPEC_OVERLAY_V2 = '+json.dumps(catalog,ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
    print('Live catalog:',len(items),'independently authored constructions')
if __name__=='__main__':main()
