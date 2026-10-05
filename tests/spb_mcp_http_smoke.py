"""Authenticated Streamable HTTP and cross-client MCP session interoperability."""
import asyncio
import json
import secrets
import subprocess
import sys
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_tools_simplification_work'/'mcp'
OUT.mkdir(parents=True,exist_ok=True)


async def main():
    token=secrets.token_urlsafe(32)
    token_file=OUT/'test-http-token.txt'
    token_file.write_text(token,encoding='utf-8')
    endpoint='http://127.0.0.1:59891/mcp'
    flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
    with (OUT/'http-stderr.log').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen([sys.executable,str(ROOT/'integrations/spb-mcp/spb_mcp_server.py'),
            '--transport','streamable-http','--port','59891','--url','http://localhost:59880/',
            '--artifacts',str(OUT/'http-artifacts'),'--token-file',str(token_file)],
            stdout=log,stderr=log,creationflags=flags)
        try:
            async with httpx.AsyncClient() as http:
                for _ in range(40):
                    try:
                        rejected=await http.post(endpoint,json={},timeout=1)
                        break
                    except (httpx.ConnectError,httpx.ConnectTimeout):
                        assert proc.poll() is None,'HTTP server exited during startup'
                        await asyncio.sleep(.1)
                else: raise AssertionError('HTTP server did not start')
                assert rejected.status_code==401,rejected.status_code
                wrong=await http.post(endpoint,json={},headers={'Authorization':'Bearer wrong'})
                assert wrong.status_code==401,wrong.status_code
            headers={'Authorization':'Bearer '+token}
            async with streamablehttp_client(endpoint,headers=headers) as (read,write,_):
                async with ClientSession(read,write) as first:
                    init=await first.initialize()
                    first_tools=await first.list_tools()
                    opened=await first.call_tool('spb_open_session',{})
                    assert not opened.isError,opened
                    sid=(opened.structuredContent or json.loads(opened.content[0].text))['session']
                    # Independent MCP host/session can address the same explicit SPB document.
                    async with streamablehttp_client(endpoint,headers=headers) as (r2,w2,_):
                        async with ClientSession(r2,w2) as second:
                            await second.initialize()
                            second_tools=await second.list_tools()
                            assert [t.name for t in first_tools.tools]==[t.name for t in second_tools.tools]
                            state=await second.call_tool('spb_state',{'session':sid})
                            assert not state.isError,state
                            assert (state.structuredContent or json.loads(state.content[0].text))['session']==sid
                            await second.call_tool('spb_close_session',{'session':sid})
            report={'passed':True,'transport':'Streamable HTTP','protocol':init.protocolVersion,
                'tools':len(first_tools.tools),'unauthenticatedRejected':True,'wrongTokenRejected':True,
                'twoIndependentClients':True,'sharedExplicitSession':True,'desktopFocusUsed':False}
            (OUT/'http-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report))
        finally:
            proc.terminate()
            try: proc.wait(timeout=10)
            except subprocess.TimeoutExpired: proc.kill();proc.wait()
            token_file.unlink(missing_ok=True)


if __name__=='__main__': asyncio.run(main())
