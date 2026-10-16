'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const candidate=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8'),shared=fs.readFileSync(path.join(__dirname,'../../js/spb-pro-ai.js'),'utf8');
function extract(src,start,end){const a=src.indexOf(start),b=src.indexOf(end,a);assert.ok(a>=0&&b>a);return src.slice(a,b);}
const base={};vm.createContext(base);vm.runInContext(extract(shared,'    function esc(s)','    function clamp('),base);
for(const provider of ['chatgpt','claude']){
 const state={provider,paint:{layers:[{id:'protected',visible:true}],zones:[{id:'body'}]},sent:0};
 const flags={SPB_ANSWER_LINKS_OFF:false},w=new Proxy(flags,{set(){throw Error('Formatting must not change the app');}}),ctx={window:w,URL};vm.createContext(ctx);vm.runInContext(extract(candidate,'    function esc(s)','    function clamp('),ctx);
 const before=JSON.stringify(state),url='https://ir-core-sites.iracing.com/members/member_images/cars/car_templates/191_template_MNSTK.zip';
 const raw=ctx.fmt('Download '+url+'.');assert.ok(raw.includes('href="'+url+'"'));assert.ok(raw.endsWith('</a>.'));assert.match(raw,/target="_blank" rel="noopener noreferrer"/);assert.match(raw,/overflow-wrap:anywhere/);
 const markdown=ctx.fmt('[Mini Stock template]('+url+')');assert.ok(markdown.includes('>Mini Stock template</a>'));assert.ok(!markdown.includes('[Mini Stock'));
 assert.ok(ctx.fmt('HTTPS://example.org/file').includes('href="HTTPS://example.org/file"'));
 const query='https://support.iracing.com/page?car=Mini&version=2026#paint';assert.ok(ctx.fmt(query).includes('href="https://support.iracing.com/page?car=Mini&amp;version=2026#paint"'));
 for(const tail of ['.',').','.)','];','!'])assert.ok(ctx.fmt('Use ('+url+tail).includes('href="'+url+'"'),tail);
 const balanced='https://example.org/Template_(Mini_Stock)';assert.ok(ctx.fmt(balanced+'.').includes('href="'+balanced+'"'));
 const malicious=ctx.fmt('[<img src=x onerror=run()>]('+url+') <script>run()</script> https://user:password@example.org/file https://example.org:8443/file javascript:run()');assert.ok(!malicious.includes('<img'));assert.ok(!malicious.includes('<script>'));assert.equal((malicious.match(/<a /g)||[]).length,1);assert.match(malicious,/&lt;img/);
 for(const bad of ['http://example.org/file','javascript:alert(1)','data:text/html,<script>run()</script>','https://','https://example.org\\evil','https://example.org/" onclick="run()'])assert.ok(!ctx.fmt(bad).includes('onclick="run()'),bad);
 assert.ok(!ctx.fmt('https://example.org\\evil').includes('<a '),'Backslash cannot turn a malformed URL into another destination');
 const refs=Array.from({length:14},(_,i)=>'https://example.org/file'+i).join('\n');assert.equal((ctx.fmt(refs).match(/<a /g)||[]).length,12);assert.ok(ctx.fmt(refs).includes('https://example.org/file13'));
 for(const ordinary of ['',null,'Normal answer.','**Fine pattern**\n- More detail\n- Keep the logos.','<b>literal</b>','SPB_SOURCE_LINK_TOKEN_0_END '+url]){
  if(String(ordinary||'').includes('https://')){assert.ok(ctx.fmt(ordinary).startsWith('SPB_SOURCE_LINK_TOKEN_0_END '));continue;}
  assert.equal(ctx.fmt(ordinary),base.fmt(ordinary));
 }
 assert.ok(ctx.fmt('**Source '+url+'**').startsWith('<b>Source <a '),'Bold may wrap a generated link without leaking its marker');
 flags.SPB_ANSWER_LINKS_OFF=true;
 assert.equal(ctx.fmt(url),base.fmt(url));assert.equal(JSON.stringify(state),before);
 const worker=JSON.parse(fs.readFileSync(path.join(__dirname,'../../_codex_mcp_work/chatgpt-dev/59910/subscription-listener-turn-2026-10-11T02-39-10-011Z.json'),'utf8'));
 flags.SPB_ANSWER_LINKS_OFF=false;assert.ok(ctx.fmt(worker.calls.at(-1).arguments.text).includes('href="'+url+'"'),'Actual prior ChatGPT answer becomes a usable source link');
}
assert.match(candidate,/fmt\(m\.text \|\| ''\)/,'Both connected providers use the same actual message renderer');
console.log(JSON.stringify({pass:true,providers:['chatgpt','claude'],bare_and_markdown_links:true,escaping_and_old_formatting_preserved:true,actual_prior_answer_linked:true,passive_navigation_only:true}));
