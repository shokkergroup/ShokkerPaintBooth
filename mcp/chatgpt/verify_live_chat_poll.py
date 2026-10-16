"""Private live relay timing check; ephemeral synthetic messages, no model or paint calls."""
from pathlib import Path
import json
import time
import urllib.request
import uuid

E = Path(__file__).resolve().parents[2] / '_codex_mcp_work/chatgpt-dev/59910'
BASE = 'http://127.0.0.1:59910'
runtime = json.loads((E / 'server.json').read_text(encoding='utf-8'))
assert runtime['port'] == 59910 and runtime['host'] == '127.0.0.1'

def call(route, body=None):
    req = urllib.request.Request(BASE + route, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type':'application/json','Origin':BASE})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)

status = call('/api/mcp/status')
assert status['pending'] == status['inbox'] == status['inflight'] == 0
assert not status['listening'], 'Do not run during an active assistant session'
page = str(uuid.uuid4())
def scope(epoch):
    return call('/api/mcp/document', {'page':page,'epoch':epoch})['document_scope']
def send(doc, helper):
    return call('/api/mcp/inbox', {'text':'Private relay timing test. No paint action requested.','helper':helper,'document_scope':doc})['seq']
def poll(doc):
    start=time.monotonic()
    result=call('/api/mcp/chat?after=0&wait=0.2&helper=chatgpt&document_scope='+doc)
    return result, time.monotonic()-start

evidence={'private_pid':runtime['pid'],'model_inference':False,'paint_calls':False}
try:
    a=scope(0);send(a,'chatgpt');b=scope(1);send(b,'claude')
    for name,doc in [('retired_document',a),('other_provider',b)]:
        result,elapsed=poll(doc)
        assert result['entries']==[]
        assert elapsed>=0.18, (name,elapsed,'empty filtered poll returned immediately')
        evidence[name]={'elapsed_seconds':round(elapsed,3),'entries':0}
    seq=send(b,'chatgpt');result,elapsed=poll(b)
    assert any(e['seq']==seq for e in result['entries'])
    evidence['matching_message']={'elapsed_seconds':round(elapsed,3),'delivered':True}
finally:
    scope(2)  # Clear synthetic inbox/inflight; next real page registers its own scope.
evidence['pass']=True
(E/'live-chat-poll-acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
print(json.dumps(evidence))
