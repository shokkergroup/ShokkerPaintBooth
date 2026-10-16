"""Private59910 static data overlay; never changes a shared runtime file."""
from pathlib import Path
import hashlib,json
NAMES=('js/spb-ai-knowledge.js','js/spb-encyclopedia-data.js',
       'js/spb-support-answers.js','js/spb-offline-answer.js','js/spb-intent-offline-frame.js',
       'data/encyclopedia/spec.json','data/encyclopedia/zones.json','data/encyclopedia/layers.json',
       'data/encyclopedia/pages/help_howto_1.json','data/encyclopedia/pages/help_howto_3.json')

def load(port):
    if port!=59910:raise ValueError('Fresh knowledge overlay is private59910 only')
    lane=Path(__file__).resolve().parent/'fresh-install/native'
    root=lane/'review-install/resources/server'
    manifest_file=root/'mcp/runtime-knowledge-manifest.json'
    proof=json.loads((lane/'stage-proof.json').read_bytes())
    raw=manifest_file.read_bytes()
    if not proof['pass'] or hashlib.sha256(raw).hexdigest()!=proof['runtime_manifest_sha256']:
        raise ValueError('Unverified knowledge overlay manifest')
    files={x['path']:x for x in json.loads(raw)['files']}
    result={}
    for relative in NAMES:
        item=files[relative];path=root/relative;raw=path.read_bytes()
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('Changed knowledge overlay: '+relative)
        result['/'+relative]={'path':path,'sha256':item['sha256'],'bytes':raw}
    return result
