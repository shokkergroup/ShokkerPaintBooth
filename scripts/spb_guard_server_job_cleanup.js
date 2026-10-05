const fs = require('fs');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

function fail(message) {
  console.error(`[spb_guard_server_job_cleanup] ${message}`);
  process.exit(1);
}

const server = read('server.py');
const moduleText = read('server_routes/job_cleanup.py');

if (!moduleText.includes('def cleanup_old_job_dirs(')) {
  fail('job_cleanup.py must own cleanup_old_job_dirs().');
}

if (!moduleText.includes('def cleanup_old_temp_entries(')) {
  fail('job_cleanup.py must own cleanup_old_temp_entries().');
}

if (!moduleText.includes('def start_background_janitor(')) {
  fail('job_cleanup.py must own start_background_janitor().');
}

if (/def\s+_spb_background_janitor\s*\(/.test(server)) {
  fail('server.py must not re-grow the inline janitor loop.');
}

if (/threading\.Thread\(target=_spb_background_janitor/.test(server)) {
  fail('server.py must start cleanup through server_routes.job_cleanup.');
}

if (!server.includes('from server_routes.job_cleanup import auto_cleanup_old_jobs, start_background_janitor')) {
  fail('server.py must import the extracted job cleanup bridge.');
}

if (!server.includes('auto_cleanup_old_jobs=auto_cleanup_old_jobs') || !server.includes('output_folder=OUTPUT_FOLDER')) {
  fail('server.py must inject startup cleanup and OUTPUT_FOLDER into the bootstrap bridge.');
}

const bootstrapPath = 'server_routes/server_bootstrap.py';
if (fs.existsSync(bootstrapPath)) {
  const bootstrap = read(bootstrapPath);
  if (!bootstrap.includes('auto_cleanup_old_jobs(output_folder, max_age_hours=24, logger=logger)')) {
    fail('server_bootstrap.py must run startup cleanup with injected output folder and logger.');
  }
} else if (!server.includes('auto_cleanup_old_jobs(OUTPUT_FOLDER, max_age_hours=24, logger=logger)')) {
  fail('server.py startup cleanup must inject OUTPUT_FOLDER and logger.');
}

console.log('[spb_guard_server_job_cleanup] OK');
