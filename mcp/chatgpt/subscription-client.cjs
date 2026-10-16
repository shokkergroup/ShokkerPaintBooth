'use strict';
// Private launcher policy. Codex owns authentication; SPB never reads its tokens.
function cleanEnvironment(input) {
  const removed = new Set(['OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL','OPENAI_API_BASE','CODEX_ACCESS_TOKEN']);
  return Object.fromEntries(Object.entries(input).filter(([key])=>!removed.has(key.toUpperCase())));
}
function execArguments({isolated=false,overrides=[],model,config,prompt}) {
  const args=['exec',...overrides,'--json','--sandbox','read-only','--skip-git-repo-check'];
  if(isolated)args.push('--ignore-user-config','--ephemeral');
  // Caller must first verify login status, without enforcing an auth restriction
  // that could log an API-authenticated customer out.
  args.push('-c','forced_login_method="chatgpt"','-c','model_provider="openai"');
  if(model)args.push('--model',model);
  args.push('-c',config,prompt);
  return args;
}
module.exports={cleanEnvironment,execArguments};
