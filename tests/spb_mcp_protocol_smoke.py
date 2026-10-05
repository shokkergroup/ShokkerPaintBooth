"""Real MCP stdio client against the real SPB audit server; no desktop controls.
Run directly to avoid unrelated renderer pytest startup: python tests/spb_mcp_protocol_smoke.py
"""
import asyncio
import json
import sys
import io
import zipfile
import time
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_tools_simplification_work' / 'mcp'
OUT.mkdir(parents=True,exist_ok=True)


def fixture():
    layers=[]
    for name,color,box in [('Numbers',(245,230,40,255),(50,70,190,200)),('Base',(30,60,110,255),(0,0,512,512))]:
        im=Image.new('RGBA',(512,512))
        ImageDraw.Draw(im).rectangle(box,fill=color)
        data=io.BytesIO();im.save(data,format='PNG')
        layers.append((name,data.getvalue()))
    dest=OUT/'mcp-fixture.ora'
    with zipfile.ZipFile(dest,'w') as z:
        z.writestr('mimetype','image/openraster')
        z.writestr('stack.xml','<image w="512" h="512" name="MCP test"><stack>'+''.join(
            f'<layer name="{n}" src="data/{i}.png" x="0" y="0" opacity="1" visibility="visible" composite-op="svg:src-over"/>' for i,(n,_) in enumerate(layers))+'</stack></image>')
        for i,(_,data) in enumerate(layers):z.writestr(f'data/{i}.png',data)
    return str(dest)


async def main():
    params = StdioServerParameters(command=sys.executable,args=[str(ROOT/'integrations/spb-mcp/spb_mcp_server.py'),
        '--url','http://localhost:59880/','--artifacts',str(OUT/'artifacts')])
    with (OUT/'protocol-stderr.log').open('w',encoding='utf-8') as errlog:
        async with stdio_client(params,errlog=errlog) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=45)) as client:
                init = await client.initialize()
                tools = await client.list_tools()
                print(json.dumps({'protocol':init.protocolVersion,'tools':len(tools.tools)}),flush=True)
                guide = await client.read_resource('spb://guide')
                assert 'spb_gesture' in guide.contents[0].text

                async def call(tool,**args):
                    with (OUT/'progress.log').open('a',encoding='utf-8') as f: f.write(str(time.time())+' '+tool+'\n')
                    result = await client.call_tool(tool,args)
                    assert not result.isError, (tool,result.content)
                    if result.structuredContent is not None:
                        return result.structuredContent
                    return json.loads(result.content[0].text)

                opened = await call('spb_open_session')
                sid = opened['session']
                state = await call('spb_state',session=sid)
                controls = await call('spb_controls',session=sid,search='import',include_hidden=True)
                (OUT/'discovery.json').write_text(json.dumps({'state':state,'controls':controls},indent=2),encoding='utf-8')
                print(json.dumps({'discoveredImportControls':controls['total']}),flush=True)
                invite=await call('spb_controls',session=sid,search='No thanks')
                if invite['controls']:
                    await call('spb_act',session=sid,actions=[{'kind':'click','target':'ref:'+invite['controls'][0]['ref']}])
                imp=next(c for c in controls['controls'] if c['label']=='Import layered PSD, XCF, or ORA file' and c['visible'])
                response=await call('spb_upload',session=sid,target='ref:'+imp['ref'],files=[fixture()])
                assert response['submitted'],response
                for _ in range(20):
                    state=await call('spb_state',session=sid)
                    if state.get('layerCount')==2:break
                    await asyncio.sleep(.5)
                assert state.get('layerCount')==2,state
                ready=await call('spb_act',session=sid,actions=[{'kind':'wait','target':'#btnRender:not([disabled])','timeout_ms':15000}])
                assert not ready['error'],ready
                # Wait for the import overlay/loading phase to leave before selecting tools.
                await asyncio.sleep(1)
                ui=await call('spb_controls',session=sid,search='brush')
                (OUT/'imported.json').write_text(json.dumps({'state':state,'brush':ui},indent=2),encoding='utf-8')
                response=await call('spb_act',session=sid,actions=[
                    {'kind':'click','target':'#btnToolbarModeLayer'},
                    {'kind':'click','target':'#layerThumb_psd_1'},
                    {'kind':'click','target':'#vtModeBrush'}])
                assert not response['error'],response
                assert response['state']['editTarget']=='layer',response
                baseline=await call('spb_checkpoint',session=sid,name='before',target='#paintCanvas')
                gesture=await call('spb_gesture',session=sid,target='#paintCanvas',space='canvas',
                    points=[[80,100],[110,115],[140,130],[160,145]],duration_ms=200)
                changed=await call('spb_checkpoint',session=sid,name='stroke',target='#paintCanvas',compare_to='before')
                assert not changed['pixelsExact'],changed
                await call('spb_act',session=sid,actions=[{'kind':'key','value':'Control+z'}])
                undo=await call('spb_checkpoint',session=sid,name='undo',target='#paintCanvas',compare_to='before')
                assert undo['pixelsExact'],undo
                image=await client.call_tool('spb_screenshot',{'session':sid,'target':'#paintCanvas'})
                assert not image.isError and image.content[0].type=='image'
                renames=await call('spb_controls',session=sid,search='rename')
                (OUT/'rename-controls.json').write_text(json.dumps(renames,indent=2),encoding='utf-8')
                print(json.dumps({'brushChanged':True,'undoExact':True,'renameControls':[{k:c.get(k) for k in ['ref','id','label']} for c in renames['controls']]}),flush=True)
                direct=await call('spb_app_script',session=sid,function='() => ({layer:getSelectedLayer().name,mode:canvasMode})')
                assert direct['result']['layer']=='Numbers',direct
                rename=renames['controls'][0]
                response=await call('spb_act',session=sid,actions=[
                    {'kind':'click','target':'ref:'+rename['ref']},
                    {'kind':'fill','target':'input[aria-label="Rename layer Numbers"]','value':'MCP Numbers'},
                    {'kind':'press','target':'input[aria-label="Rename layer Numbers"]','value':'Enter'}])
                assert not response['error'],response
                assert response['state']['selectedLayer']['name']=='MCP Numbers',response
                # Save through the normal project UI on the isolated Projects server.
                await call('spb_act',session=sid,actions=[{'kind':'click','target':'#spbProjectsButton'},
                    {'kind':'wait','target':'#spbProjectsModal','timeout_ms':15000}])
                save=await call('spb_controls',session=sid,search='Save this exact workflow')
                assert save['controls'],save
                project_name='SPB MCP acceptance '+str(int(time.time()))
                response=await call('spb_act',session=sid,actions=[
                    {'kind':'click','target':'ref:'+save['controls'][0]['ref']},
                    {'kind':'fill','target':'#spbProjectNameInput','value':project_name},
                    {'kind':'press','target':'#spbProjectNameInput','value':'Enter'}])
                assert not response['error'],response
                # The controller is asynchronous; verify a real saved v2 project, not just its toast.
                saved=None
                for _ in range(30):
                    listing=await call('spb_app_script',session=sid,argument=project_name,function='''async name => {
                        const r=await fetch('/api/projects/list',{headers:{'X-Shokker-Internal':'1'}});
                        const out=await r.json();return (out.projects||[]).find(p=>p.name===name)||null;
                    }''')
                    saved=listing.get('result')
                    if saved: break
                    await asyncio.sleep(.2)
                assert saved,listing
                assert saved['schemaVersion']==2 and saved['layerCount']==2,saved
                project=json.loads((ROOT/'_release_evidence/isolated_output/tool_project_audit'/saved['file']).read_text())
                assert project['canvas']=={'width':512,'height':512}
                assert [layer['name'] for layer in project['layers']]==['Base','MCP Numbers']
                (OUT/'saved-project-result.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
                # Browser-native prompt: handled across two MCP requests, not by desktop UI.
                prompt=await call('spb_app_script',session=sid,function='() => ({answer:prompt("MCP test prompt", "")})')
                assert not prompt['done'],prompt
                status=await call('spb_state',session=sid)
                assert status['pendingDialog']['type']=='prompt',status
                await call('spb_dialog',session=sid,accept=True,text='MCP response')
                result=await call('spb_operation',session=sid,operation=prompt['operation'],wait_ms=1000)
                assert result['result']['answer']=='MCP response',result
                # Export actual source pixels through the full app scripting surface and browser download.
                await call('spb_app_script',session=sid,function='''async () => {
                    const c=document.getElementById('paintCanvas');
                    const blob=await new Promise(r=>c.toBlob(r,'image/png'));
                    const url=URL.createObjectURL(blob), a=document.createElement('a');
                    a.href=url;a.download='mcp-source.png';a.click();
                    setTimeout(()=>URL.revokeObjectURL(url),5000);return {width:c.width,height:c.height};
                }''')
                for _ in range(20):
                    exported=await call('spb_state',session=sid)
                    if exported['downloads']:break
                    await asyncio.sleep(.1)
                assert exported['downloads'],exported
                png=Path(exported['downloads'][0]['path'])
                assert Image.open(png).size==(512,512),png
                expected=Image.new('RGBA',(512,512),(30,60,110,255))
                ImageDraw.Draw(expected).rectangle((50,70,190,200),fill=(245,230,40,255))
                assert Image.open(png).convert('RGBA').tobytes()==expected.tobytes()
                long=await call('spb_app_script',session=sid,function='async () => {await new Promise(r=>setTimeout(r,2200));return {completed:true}}')
                assert not long['done'],long
                result=await call('spb_operation',session=sid,operation=long['operation'],wait_ms=1000)
                assert result['done'] and result['result']['completed'],result
                bad=await call('spb_act',session=sid,actions=[{'kind':'click','target':'#no-such-control'},{'kind':'click','target':'#vtModeErase'}])
                assert bad['completed']==0 and bad['partial'] and bad['error'],bad
                (OUT/'stdio-report.json').write_text(json.dumps({'passed':True,'protocol':init.protocolVersion,
                    'tools':len(tools.tools),'layersImported':2,'brush':gesture,'brushChanged':True,'undoExact':True,
                    'mcpImage':True,'directAppAccess':True,'rename':True,'projectSaved':True,
                    'nativePrompt':True,'downloadPng512':True,'longOperation':True,'partialBatchStops':True,
                    'desktopFocusUsed':False},indent=2),encoding='utf-8')
                await call('spb_close_session',session=sid)


if __name__ == '__main__': asyncio.run(main())
