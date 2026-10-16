"""Actual ChatGPT subscription result versus the independently proven native result."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'_codex_mcp_work/chatgpt-dev/59910'
P=ROOT/'_release_evidence/chatgpt-dev/59910/projects'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def state(receipt):
    return json.loads(next(c['text'] for c in receipt['calls'] if c['tool']=='spb_get_state'))


def main():
    probe_name='context-session-probe-2026-10-10T06-18-28-098Z.json'
    probe=read(E/probe_name)
    assert probe['authentication']=='ChatGPT' and probe['apiFallback'] is False
    assert probe['exitCode']==0 and not probe['errors']
    edits=[c for c in probe['calls'] if c['tool']=='spb_edit_layer']
    assert len(edits)==1 and edits[0]['arguments']=={'layer':'psd_23','source_colour':'#ff0000','colour':'#b39a58','replace_tolerance':40}
    assert not any(c['tool'] in ('spb_do','spb_add_zone','spb_undo') for c in probe['calls'])
    names=[probe['fixtureReceipt'],'paint-online-source-colour-after-2026-10-10T06-20-23-073Z.json','paint-online-source-colour-undo-2026-10-10T06-21-55-108Z.json']
    records=[read(E/n) for n in names]
    states=[state(r) for r in records]
    assert len(states[0]['layers'])==42 and len(states[0]['zones'])==5
    for s in states[1:]:
        assert s['layers']==states[0]['layers'] and s['zones']==states[0]['zones']
    for original in records[0]['images']:
        assert any(i['name']==original['name'] and i['sha256']==original['sha256'] for i in records[2]['images'])
    specs=[next(i['sha256'] for i in r['images'] if i['name']=='spec_map') for r in records]
    assert len(set(specs))==1
    pairs=[('ARCA native source colour after - private59910.spbproj','ARCA ChatGPT source colour after - private59910.spbproj'),
           ('ARCA native source colour Undo - private59910.spbproj','ARCA ChatGPT source colour Undo - private59910.spbproj')]
    hashes={}
    for reference,actual in pairs:
        a,b=read(P/reference),read(P/actual)
        assert len(a['layers'])==42 and a['layers']==b['layers']
        hashes[actual]=hashlib.sha256((P/actual).read_bytes()).hexdigest()
    for reference,actual in [('helper-native-colour-after.png','online-source-colour-after.png'),
                             ('helper-native-colour-before.png','online-source-colour-undo.png')]:
        assert (E/reference).read_bytes()==(E/actual).read_bytes()
    prior=read(E/'native-helper-replace-saved.json')
    assert prior['pass'] and prior['source_kernel_max_error']==0
    result={'pass':True,'probe':probe_name,'receipts':names,'authentication':'ChatGPT','apiFallback':False,
            'one_scoped_source_colour_edit':True,'all_42_saved_layer_payloads_equal_proven_native_after_and_undo':True,
            'all_42_metadata_records_five_zones_and_spec_preserved':True,'native_after_and_undo_png_byte_equal':True,
            'saved_project_sha256':hashes,
            'automated_app_report':'not_measured; model disclosed this; independent full-raster/preview comparison supplies evidence',
            'scope':'Actual one-message ChatGPT subscription edit through SPB AI box plus native Save/Undo/Save. Same exact source result as proven Offline operation. No Claude inference parity, broader schemes, full export, packaged delivery or persistent listener lifecycle claim.'}
    (E/'online-source-colour.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()
