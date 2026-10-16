"""Bounded local probe used by the reviewed Codex setup candidate."""
import json
import os
from pathlib import Path
import subprocess

def knowledge_status(mcp_dir, runtime, runtime_env=None):
    unavailable=lambda code,message: {'schema':'spb-knowledge-readiness/1','ready':False,'status':'unavailable','code':code,'message':message,'read_only':True}
    if not runtime:
        return unavailable('runtime_missing','SPB needs an available local runtime before it can check AI knowledge.')
    probe=Path(mcp_dir)/'server'/'knowledge-health.cjs'
    if not probe.is_file():
        return unavailable('knowledge_checker_missing','SPB’s AI knowledge files need an update. Update or repair SPB, then reconnect.')
    env={**os.environ,**(runtime_env or {}),'NODE_OPTIONS':'','NODE_PATH':''}
    try:
        process=subprocess.run([str(runtime),str(probe),str(Path(mcp_dir).resolve())],capture_output=True,
            text=True,encoding='utf-8',errors='replace',env=env,timeout=8,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if len(process.stdout)>32768:raise ValueError('Oversized knowledge result')
        result=json.loads(process.stdout)
        if result.get('schema')!='spb-knowledge-readiness/1' or not isinstance(result.get('ready'),bool):raise ValueError('Invalid knowledge result')
        if (process.returncode==0)!=result['ready']:raise ValueError('Contradictory knowledge result')
        if result['ready']:
            # Validate parsing with the same binary/env; --check executes no app code.
            syntax=subprocess.run([str(runtime),'--check',str(Path(mcp_dir)/'server'/'index.js')],
                capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=5,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if syntax.returncode!=0:
                return unavailable('mcp_entry_invalid','SPB’s connection files could not be validated. Repair or update SPB.')
            result['entry_syntax_checked']=True
        return result
    except subprocess.TimeoutExpired:
        return unavailable('knowledge_check_timeout','SPB’s AI knowledge check took too long. Restart SPB and try again.')
    except (OSError,ValueError):
        return unavailable('knowledge_check_failed','SPB’s AI knowledge check could not finish. Repair or update SPB.')
