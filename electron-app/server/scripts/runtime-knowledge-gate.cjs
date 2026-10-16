'use strict';
// Proposed canonical scripts/runtime-knowledge-gate.cjs; run after tree preparation.
const fs = require('node:fs'), path = require('node:path'), {spawnSync} = require('node:child_process');
function run(root, runner=spawnSync) {
  root = fs.realpathSync(root);
  const plan = path.join(__dirname,'runtime-knowledge-plan.json');
  const builder = path.join(__dirname,'build-runtime-manifest.cjs');
  const manifest = path.join(root,'mcp/runtime-knowledge-manifest.json');
  const entry = JSON.parse(fs.readFileSync(plan,'utf8')).roles.entry;
  const steps = [
    ['generate', [builder,'--server-root',root,'--plan',plan,'--output',manifest]],
    ['deterministic-check', [builder,'--server-root',root,'--plan',plan,'--output',manifest,'--check']],
    ['knowledge-health', [path.join(root,'mcp/server/knowledge-health.cjs'),path.join(root,'mcp')]],
    ['entry-syntax', ['--check',path.join(root,entry)]]
  ];
  for (const [name,args] of steps) {
    const result = runner(process.execPath,args,{cwd:root,encoding:'utf8',windowsHide:true,maxBuffer:1024*1024,env:{...process.env,ELECTRON_RUN_AS_NODE:'1'}});
    if (result.error || result.status !== 0) throw Error('Knowledge gate failed at '+name+': '+String(result.error?.message || result.stderr || result.stdout || 'nonzero exit').slice(0,800));
  }
  return {pass:true,steps:steps.map(s=>s[0]),scope:'prepared runtime knowledge/context integrity and entry syntax; provider and action acceptance remain separate'};
}
if(require.main===module){try{if(process.argv.length!==3)throw Error('Usage: runtime-knowledge-gate.cjs PREPARED_SERVER');console.log(JSON.stringify(run(process.argv[2])));}catch(e){console.error(e.message);process.exitCode=1;}}
module.exports={run};
