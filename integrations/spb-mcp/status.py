"""Check the background MCP service without opening a paint document or showing its token."""
import argparse
import asyncio
import json
from pathlib import Path
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def check(endpoint, token_file):
    token=token_file.read_text(encoding='utf-8').strip()
    async with streamablehttp_client(endpoint,headers={'Authorization':'Bearer '+token}) as (read,write,_):
        async with ClientSession(read,write) as client:
            init=await client.initialize()
            tools=await client.list_tools()
            guide=await client.read_resource('spb://guide')
            return {'ready':True,'server':init.serverInfo.name,'protocol':init.protocolVersion,
                    'tools':len(tools.tools),'operatingGuide':bool(guide.contents),'endpoint':endpoint}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--endpoint',default='http://127.0.0.1:59890/mcp')
    p.add_argument('--token-file',type=Path,default=Path(__file__).with_name('data')/'http-token.txt')
    args=p.parse_args()
    print(json.dumps(asyncio.run(check(args.endpoint,args.token_file))))
