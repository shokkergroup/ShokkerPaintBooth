"""Fresh app boot and real controls over MCP; no manual handler installation."""
import asyncio, json, sys, uuid
from pathlib import Path
from PIL import Image
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '_tools_simplification_work/mcp-review'

def fresh_fixture():
    target=OUT/('pattern-fixture-'+uuid.uuid4().hex+'.png')
    Image.new('RGB',(512,512),(190,55,12)).save(target)
    return target

async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'integrations/spb-mcp/spb_mcp_server.py'), '--url', 'http://localhost:59880/'])
    async with stdio_client(params) as (r,w):
      async with ClientSession(r,w) as client:
        await client.initialize()
        async def call(name, **args):
          result = await client.call_tool(name, args)
          if result.isError and 'Native dialog pending' in str(result.content):
            await client.call_tool('spb_dialog', {'session':sid,'accept':False})
            result = await client.call_tool(name, args)
          assert not result.isError, result.content
          data = result.structuredContent or json.loads(result.content[0].text)
          if name == 'spb_act': assert not data.get('error'), data
          return data
        sid = (await call('spb_open_session'))['session']
        async def script(fn):
          data = await call('spb_app_script', session=sid, function=fn)
          attempts=0
          while not data.get('done', True):
            attempts+=1
            assert attempts<30, ('App script timed out',fn)
            state=await call('spb_state',session=sid)
            if state.get('pendingDialog'):
              print('Dismiss test dialog:',state['pendingDialog']['message'][:100],flush=True)
              await call('spb_dialog',session=sid,accept=False)
            data = await call('spb_operation', session=sid, operation=data['operation'], wait_ms=1000)
          return data.get('result')
        async def act(*actions): return await call('spb_act',session=sid,actions=list(actions))
        try:
          await act(dict(kind='click',target='#spbModeProBtn'))
          await act(dict(kind='fill',target='#paintFile',value=str(fresh_fixture())),
                    dict(kind='press',target='#paintFile',value='Enter'))
          await act(dict(kind='wait',target='#btnRender:not([disabled])',timeout_ms=15000))
          await asyncio.sleep(.5)
          setup=await script("""() => {
            window.__patternAudit={errors:[],requests:[]};
            addEventListener('error',e=>__patternAudit.errors.push(e.message));
            const originalFetch=window.fetch;
            window.fetch=function(url,options) {
              if(String(url).includes('preview-render') && options?.body) {
                try {__patternAudit.requests.push(JSON.parse(options.body).zones?.[0]);}catch(e){}
              }
              return originalFetch.apply(this,arguments);
            };
            zones[0].color='remaining'; zones[0].colorMode='remaining';
            setZoneBase(0,'fs_core_crimson');setZonePattern(0,'decade_90s_sega_blast');selectZone(0);renderZoneDetail(0);
            return {setter:typeof setPatternMaterialControl,step:typeof stepPatternMaterialControl};
          }""")
          assert setup=={'setter':'function','step':'function'},setup
          print('Fresh boot ready',flush=True)
          # Native focus/keyboard range changes run the real inline input handlers.
          for key,value in [('hue',120),('saturation',-100),('spec',50)]:
            await asyncio.sleep(.25)
            before=await script('() => window._spbGetZoneConfigHash()')
            await act(dict(kind='range',target=f'[data-pattern-material-control="0:-1:{key}"] input',value=value))
            await asyncio.sleep(.25)
            assert await script('() => window._spbGetZoneConfigHash()') != before, (key,'preview hash did not change')
          observed=await script("() => ({hue:zones[0].patternHueShift,saturation:zones[0].patternSaturation,spec:zones[0].patternSpecOpacity,errors:__patternAudit.errors})")
          assert observed==dict(hue=120,saturation=-100,spec=50,errors=[]),observed
          print('Primary sliders pass',flush=True)
          await act(dict(kind='click',target='[aria-label="Reset Pattern hue"]'))
          assert await script('() => zones[0].patternHueShift')==0
          await asyncio.sleep(.25)
          before=await script('() => window._spbGetZoneConfigHash()')
          await act(dict(kind='select',target='#detPatMode0',value='blend'))
          await asyncio.sleep(.25)
          assert await script('() => window._spbGetZoneConfigHash()') != before,'Blend preview hash did not change'
          blend=await script("() => ({mode:zones[0].patternPaintMode,hueDisabled:document.querySelector('[data-pattern-material-control=\"0:-1:hue\"] input').disabled,specDisabled:document.querySelector('[data-pattern-material-control=\"0:-1:spec\"] input').disabled})")
          assert blend==dict(mode='blend',hueDisabled=True,specDisabled=False),blend
          print('Blend controls pass',flush=True)
          await asyncio.sleep(2)
          requests=await script('() => __patternAudit.requests')
          assert any(z and z.get('pattern_paint_mode')=='blend' and z.get('pattern_spec_opacity')==.5 for z in requests),requests
          await act(dict(kind='click',target='#zoneEditorFloat .pattern-none-btn'))
          none=await script("() => ({pattern:zones[0].pattern,pickerOpen:document.getElementById('swatchPopup').classList.contains('active'),removeButtons:document.querySelectorAll('#zoneEditorFloat .pattern-none-btn').length,errors:__patternAudit.errors})")
          assert none==dict(pattern='none',pickerOpen=False,removeButtons=0,errors=[]),none
          print('None pass',flush=True)
          await script('() => undoZoneChange()')
          assert await script('() => zones[0].pattern')=='decade_90s_sega_blast'
          # Additional pattern controls use the same boot-installed functions.
          await script("() => {addPatternLayer(0);zones[0].patternStack[0].id='decade_80s_leg_warmer';setZonePatternPaintMode(0,'overlay');renderZoneDetail(0);}")
          await act(dict(kind='range',target='[data-pattern-material-control="0:0:spec"] input',value=75))
          assert await script('() => zones[0].patternStack[0].specOpacity')==75
          report=dict(boot=setup,primary=observed,blend=blend,none=none,previewTransport=True,noneUndo=True,stackSpec=75)
          (OUT/'bug-browser-pass.json').write_text(json.dumps(report,indent=2))
          print(json.dumps(report),flush=True)
        finally:
          await call('spb_close_session',session=sid)

if __name__=='__main__': asyncio.run(main())
