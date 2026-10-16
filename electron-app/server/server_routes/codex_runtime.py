"""Review candidate only: select and version-probe an MCP runtime, no config writes.

Electron candidates require an exact installed-layout path and enabled v1
RunAsNode fuse before the hidden, time-bounded --version process can run.
No SPB application entrypoint, server, bridge, download or model is started.
"""
from pathlib import Path
import hashlib, os, re, shutil, subprocess

SENTINEL=b'dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX'
MINIMUM_NODE_MAJOR=18

def _inspect_fuse(binary):
    binary=Path(binary).resolve(); offset=0; tail=b''; location=None; digest=hashlib.sha256()
    with binary.open('rb') as stream:
        while block:=stream.read(4*1024*1024):
            digest.update(block); buffer=tail+block
            index=buffer.find(SENTINEL)
            if location is None and index>=0: location=offset-len(tail)+index
            tail=buffer[-len(SENTINEL):];offset+=len(block)
    if location is None: return {'enabled':False,'reason':'Fuse sentinel absent','sha256':digest.hexdigest()}
    with binary.open('rb') as stream:
        stream.seek(location+len(SENTINEL));header=stream.read(2)
        if len(header)!=2:return {'enabled':False,'reason':'Truncated fuse header','sha256':digest.hexdigest()}
        version,length=header;states=list(stream.read(length))
    return {'enabled':version==1 and len(states)==length and length>0 and states[0]==0x31,
            'version':version,'states':states,'sha256':digest.hexdigest(),'bytes':binary.stat().st_size}

def inspect_fuse(binary):
    try:return _inspect_fuse(binary)
    except OSError as error:return {'enabled':False,'reason':'Binary unavailable during fuse inspection','error':type(error).__name__}

def windows_node_console(binary):
    """Reject PATH GUI binaries/wrappers before any Windows version launch."""
    if os.name!='nt':return True
    p=Path(binary)
    if p.name.lower()!='node.exe':return False
    with p.open('rb') as stream:
        header=stream.read(64)
        if len(header)!=64 or header[:2]!=b'MZ':return False
        offset=int.from_bytes(header[60:64],'little')
        if not 64<=offset<=1024*1024:return False
        stream.seek(offset);pe=stream.read(94)
        return (len(pe)==94 and pe[:4]==b'PE\x00\x00' and
                int.from_bytes(pe[24:26],'little') in (0x10b,0x20b) and
                int.from_bytes(pe[92:94],'little')==3)

def probe_version(binary, electron=False, timeout=5, runner=subprocess.run):
    env=dict(os.environ)
    # Clear external code injection into a version-only process.
    env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None)
    env['ELECTRON_RUN_AS_NODE']='1' if electron else '0'
    try:
        result=runner([str(binary),'--version'],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',
                      timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired) as error:
        return {'ok':False,'reason':type(error).__name__}
    output=result.stdout.strip();match=re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)',output)
    ok=result.returncode==0 and match is not None and int(match.group(1))>=MINIMUM_NODE_MAJOR
    return {'ok':ok,'version':output[:80],'exit_code':result.returncode,
            'stderr':result.stderr[:300],'reason':None if ok else 'Unsupported or unverified Node version'}

def _resolve_runtime(mcp_dir, packaged_executable=None, path_node=None, runner=subprocess.run):
    mcp_dir=Path(mcp_dir).resolve();server_root=mcp_dir.parent; app_root=server_root.parent.parent
    expected_resources=(server_root.parent.name.lower()=='resources' and server_root.name.lower()=='server' and mcp_dir.name.lower()=='mcp')
    attempts=[];candidates=[]
    bundled=server_root/'node'/'node.exe'
    if expected_resources and bundled.is_file():candidates.append(('bundled-node',bundled,False))
    if packaged_executable:
        binary=Path(packaged_executable).resolve()
        if not expected_resources or binary.parent!=app_root or binary.suffix.lower()!='.exe':
            attempts.append({'kind':'packaged-electron','ok':False,'reason':'Executable is outside exact installed app root'})
        elif not binary.is_file():attempts.append({'kind':'packaged-electron','ok':False,'reason':'Executable absent'})
        else:candidates.append(('packaged-electron',binary,True))
    node=path_node if path_node is not None else shutil.which('node')
    if node:candidates.append(('path-node',Path(node).resolve(),False))
    for kind,binary,electron in candidates:
        try:
            fuse=inspect_fuse(binary) if electron else None
            if not electron and not windows_node_console(binary):
                attempts.append({'kind':kind,'command':str(binary),'ok':False,'reason':'Not a Windows console node.exe'})
                continue
        except OSError as error:
            attempts.append({'kind':kind,'command':str(binary),'ok':False,'reason':'Runtime inspection unavailable','error':type(error).__name__})
            continue
        if electron and not fuse['enabled']:
            attempts.append({'kind':kind,'command':str(binary),'ok':False,'reason':'RunAsNode fuse unavailable or disabled','fuse':fuse})
            continue
        proof=probe_version(binary,electron,runner=runner)
        attempt={'kind':kind,'command':str(binary),**proof}
        if fuse:attempt['fuse']=fuse
        attempts.append(attempt)
        if proof['ok']:
            return {'ready':True,'kind':kind,'command':str(binary),'args':[str(mcp_dir/'server'/'index.js')],
                    'env':{'ELECTRON_RUN_AS_NODE':'1' if electron else '0','NODE_OPTIONS':'','NODE_PATH':''},
                    'node_version':proof['version'],'attempts':attempts,
                    'knowledge_readiness_required_separately':True}
    return {'ready':False,'kind':None,'command':None,'attempts':attempts,'knowledge_readiness_required_separately':True}

def resolve_runtime(mcp_dir, packaged_executable=None, path_node=None, runner=subprocess.run):
    try:return _resolve_runtime(mcp_dir,packaged_executable,path_node,runner)
    except (OSError,RuntimeError,ValueError) as error:
        return {'ready':False,'kind':None,'command':None,
                'attempts':[{'ok':False,'reason':'Runtime path unavailable','error':type(error).__name__}],
                'knowledge_readiness_required_separately':True}
