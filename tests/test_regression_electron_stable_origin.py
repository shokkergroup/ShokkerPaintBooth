"""Offline regressions for Electron's stable-origin server ownership policy."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "electron-app" / "main.js").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", MAIN)
    assert match, name
    start, depth, index = match.start(), 0, match.start()
    while index < len(MAIN):
        if MAIN[index] == "{":
            depth += 1
        elif MAIN[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return MAIN[start : index + 1]
        index += 1
    raise AssertionError(name)


def _run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_stable_holder_classifier_requires_health_pid_process_and_true_orphan():
    source = "\n".join(
        _function_source(name)
        for name in (
            "_sameStableOriginPath",
            "_classifyStablePortHolder",
        )
    )
    script = r"""
const path = require('path');
const SPB_BUILD_IDENTITY = 'Shokker Engine V5 - Modular Architecture';
""" + source + r"""
const expectedDir = 'C:\\SPB\\server';
const identity = {
  status:'running',engine:'Shokker Engine V5 - Modular Architecture',
  port:59876,pid:321,server_dir:'c:/spb/server'
};
const processInfo = {
  pid:321,parentPid:111,parentAlive:false,
  executablePath:'C:\\SPB\\server\\python\\python.exe',
  commandLine:'"C:\\SPB\\server\\python\\python.exe" server_v5.py'
};
function classify(patch){return _classifyStablePortHolder(Object.assign({
  port:59876,expectedServerDir:expectedDir,pids:[321],identity,processInfo
},patch||{}));}
const cases = {
  verified:classify(),
  wrongHealth:classify({identity:Object.assign({},identity,{engine:'Other service'})}),
  wrongPid:classify({pids:[999]}),
  wrongProcess:classify({processInfo:Object.assign({},processInfo,{commandLine:'python unrelated.py'})}),
  liveParent:classify({processInfo:Object.assign({},processInfo,{parentAlive:true})}),
  multipleHolders:classify({pids:[321,654]}),
  wrongDirectory:classify({identity:Object.assign({},identity,{server_dir:'C:/Other/server'})})
};
console.log(JSON.stringify(cases));
"""
    cases = _run_node(script)
    assert cases["verified"]["kind"] == "verified_spb_orphan"
    for name in (
        "wrongHealth",
        "wrongPid",
        "wrongProcess",
        "liveParent",
        "multipleHolders",
        "wrongDirectory",
    ):
        assert cases[name]["kind"] == "blocked", (name, cases[name])


def test_stable_port_reclaim_kills_only_the_exact_verified_orphan_with_mocks():
    source = "\n".join(
        _function_source(name)
        for name in (
            "_sameStableOriginPath",
            "_classifyStablePortHolder",
            "ensureStableServerPortAvailable",
        )
    )
    script = r"""
const path = require('path');
const SPB_BUILD_IDENTITY = 'Shokker Engine V5 - Modular Architecture';
function debugLog(){}
""" + source + r"""
const expectedDir = 'C:\\SPB\\server';
const identity = {status:'running',engine:'Shokker Engine V5 - Modular Architecture',port:59876,pid:321,server_dir:expectedDir};
const processInfo = {pid:321,parentPid:111,parentAlive:false,executablePath:'C:\\Python\\python.exe',commandLine:'python server_v5.py'};
async function run(patch){
  const killed=[];
  const deps=Object.assign({
    isPortFree:async()=>false,
    getPidsOnPort:()=>[321],
    probeIdentity:async()=>identity,
    getProcessInfo:()=>processInfo,
    getServerDir:()=>expectedDir,
    killPid:async(pid)=>{killed.push(pid);},
    waitForPortFree:async()=>true
  },patch||{});
  try { return {result:await ensureStableServerPortAvailable(59876,deps),killed}; }
  catch(error){return {error:error.message,killed};}
}
(async()=>{
  const free=await run({isPortFree:async()=>true,killPid:async()=>{throw new Error('must not kill');}});
  const verified=await run();
  const unrelated=await run({probeIdentity:async()=>Object.assign({},identity,{engine:'Other'})});
  const parentAlive=await run({getProcessInfo:()=>Object.assign({},processInfo,{parentAlive:true})});
  let ownerReads=0;
  const ownershipChanged=await run({getPidsOnPort:()=>++ownerReads===1?[321]:[999]});
  const stuck=await run({waitForPortFree:async()=>false});
  console.log(JSON.stringify({free,verified,unrelated,parentAlive,ownershipChanged,stuck}));
})();
"""
    payload = _run_node(script)
    assert payload["free"]["result"]["reclaimed"] is False
    assert payload["free"]["killed"] == []
    assert payload["verified"]["result"] == {"port": 59876, "reclaimed": True, "pid": 321}
    assert payload["verified"]["killed"] == [321]
    assert payload["unrelated"]["killed"] == [] and "stable" in payload["unrelated"]["error"].lower()
    assert payload["parentAlive"]["killed"] == []
    assert payload["ownershipChanged"]["killed"] == []
    assert "changed ownership" in payload["ownershipChanged"]["error"].lower()
    assert payload["stuck"]["killed"] == [321] and "release" in payload["stuck"]["error"].lower()


def test_identity_probe_and_started_child_gate_use_only_mocked_http():
    source = "\n".join(
        _function_source(name)
        for name in (
            "_sameStableOriginPath",
            "probeSpbServerIdentity",
            "_isExpectedStartedChildIdentity",
        )
    )
    script = r"""
const {EventEmitter} = require('events');
const http = {get(){throw new Error('real HTTP must not be used');}};
const SPB_BUILD_IDENTITY = 'Shokker Engine V5 - Modular Architecture';
""" + source + r"""
function clientFor(body,statusCode){return {get(options,callback){
  const request=new EventEmitter();
  request.setTimeout=function(){};
  request.destroy=function(){};
  process.nextTick(()=>{
    const response=new EventEmitter(); response.statusCode=statusCode; response.setEncoding=function(){};
    callback(response); response.emit('data',body); response.emit('end');
  });
  clientFor.lastOptions=options;
  return request;
}};}
(async()=>{
  const payload={status:'running',engine:'Shokker Engine V5 - Modular Architecture',port:59876,pid:77,server_dir:'C:/SPB/server'};
  const valid=await probeSpbServerIdentity(59876,{httpClient:clientFor(JSON.stringify(payload),200),timeoutMs:25});
  const invalid=await probeSpbServerIdentity(59876,{httpClient:clientFor('{bad json',200),timeoutMs:25});
  console.log(JSON.stringify({
    path:clientFor.lastOptions.path,
    host:clientFor.lastOptions.hostname,
    internal:clientFor.lastOptions.headers['X-Shokker-Internal'],
    validChild:_isExpectedStartedChildIdentity(valid,59876,77,'c:\\spb\\server'),
    wrongChild:_isExpectedStartedChildIdentity(valid,59876,78,'C:/SPB/server'),
    invalid:invalid===null
  }));
})();
"""
    payload = _run_node(script)
    assert payload == {
        "path": "/build-check",
        "host": "127.0.0.1",
        "internal": "1",
        "validChild": True,
        "wrongChild": False,
        "invalid": True,
    }


def test_production_port_policy_has_no_silent_fallback_or_broad_process_kill():
    picker = _function_source("pickServerPort")
    starter = _function_source("startServer")
    restart = _function_source("restartServer")
    shutdown = _function_source("gracefulShutdown")
    assert "STABLE_SERVER_PORT" in MAIN
    assert "ensureStableServerPortAvailable" in picker
    assert "tryOrder" not in picker and "ephemeral" not in picker
    assert "59877" not in picker and "60876" not in picker
    assert "probeSpbServerIdentity" in starter
    assert "child.pid" in starter and "server_dir" in MAIN
    assert "if (serverRestartPromise)" in restart
    assert "_waitForStablePortRelease(serverPort, 4000)" in restart
    assert "ensureStableServerPortAvailable(serverPort)" in restart
    assert "killPortHolders" not in MAIN
    assert "taskkill /F /IM" not in shutdown
    assert "serverProcess.pid" in shutdown


def test_port_picker_uses_fixed_default_and_only_explicit_dev_origin_with_mocks():
    source = _function_source("pickServerPort")
    script = r"""
const STABLE_SERVER_PORT = 59876;
function debugLog(){}
async function ensureStableServerPortAvailable(){throw new Error('real ensure must not run');}
""" + source + r"""
(async()=>{
  const calls=[];
  const ensure=async(port)=>{calls.push(port);};
  const stable=await pickServerPort({devPortRaw:null,ensureStableServerPortAvailable:ensure});
  const dev=await pickServerPort({devPortRaw:'61234',ensureStableServerPortAvailable:ensure});
  let invalid='';
  try { await pickServerPort({devPortRaw:'bad',ensureStableServerPortAvailable:ensure}); }
  catch(error){invalid=error.message;}
  console.log(JSON.stringify({stable,dev,calls,invalid}));
})();
"""
    payload = _run_node(script)
    assert payload["stable"] == 59876
    assert payload["dev"] == 61234
    assert payload["calls"] == [59876, 61234]
    assert "invalid" in payload["invalid"].lower()
