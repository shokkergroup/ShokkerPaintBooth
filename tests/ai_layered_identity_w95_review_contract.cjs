'use strict';
// W95: source-format boundary review across loader, server adapter, and the
// saved-owner durable-source gate. All sources are immutable candidates.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const oraclePath='_easy_claude_work/ai14h_w95_review/fresh-oracle.json';
const canvasPath='_easy_claude_work/ai14h_generation3_candidate/integration12/paint-booth-3-canvas.js';
const serverPath='_easy_claude_work/ai14h_w83_review/candidate/server.py';
const routePath='_easy_claude_work/ai14h_w83_review/candidate/server_routes/psd_import_routes.py';
const importPath='server_routes/ora_import.py',xcfPath='server_routes/xcf_import.py';
const controllerPath='_easy_claude_work/ai14h_w89_review/candidate/spb-pro-ai.js';
const expected={oracle:'88761b3231eeb40a644ca4c440763dcfc331487d69efb935a39a4d695dc6bb6c',canvas:'cb4cc4679f69cbe206e02dd512c7f197f971482b6bdb088e5b78a2f397d3cdc9',server:'a845f7ee1cd96b9f87fe1af85d42a1b86dd2059e2a5893e47006a08d773ac2ce',routes:'6a0fce336fc5ef54eb80ef92a220abc0d81e5b22107b2bf3a4e3b0872f51a95d',ora:'189b2943e584c960ae984b45e4318e675e20bb840710d814bf25a66fd0eacf4e',xcf:'5a6b2b01be492611b153badd71b44bc47307031e34023e2093c14f95b168c3fe',controller:'fa51053ad77409aa677a9e2d8ef633fd6d6bcd20e5dcdf5628af40c65b37dc59'};
const h=b=>crypto.createHash('sha256').update(b).digest('hex');
const files={};for(const [k,p] of Object.entries({oracle:oraclePath,canvas:canvasPath,server:serverPath,routes:routePath,ora:importPath,xcf:xcfPath,controller:controllerPath})){files[k]=fs.readFileSync(path.join(root,p),'utf8');assert.equal(h(Buffer.from(files[k])),expected[k],`pinned ${k} source changed`);}
const oracle=JSON.parse(files.oracle);assert.equal(oracle.case_count,7);
function slice(s,a,b){const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,`slice ${a}`);return s.slice(i,j);}
const fingerprintSrc=slice(files.canvas,'function _spbLayeredSourceFingerprint(data, compositeFingerprint) {','function _spbDecodeImage(');
const dctx={};vm.createContext(dctx);vm.runInContext(fingerprintSrc,dctx);const fingerprint=dctx._spbLayeredSourceFingerprint;
const digest='a'.repeat(64), composite='b'.repeat(64), fnv='fnv1a32-ab12cd34-42';
const durableSrc=slice(files.controller,'    function durablePartMemorySourceIdentityCurrent(kind, fingerprint) {','    function partMemorySource(');
const mctx={};vm.createContext(mctx);vm.runInContext(durableSrc+'\nthis.check=durablePartMemorySourceIdentityCurrent;',mctx);const durable=mctx.check;
const validator=slice(files.routes,'    def _validate_psd_path(',"    @app.route('/api/psd-import'");
assert(validator.includes("('.psd', '.ora', '.xcf')"),'backend must keep the exact supported-format gate');
assert(files.server.includes("if psd_path.lower().endswith('.ora')"));assert(files.server.includes("elif psd_path.lower().endswith('.xcf')"));
assert(files.server.includes('if source_fingerprint is not None and is_psd:'),'digest snapshot parser path exists');
assert(files.ora.includes('zipfile.ZipFile(path)'),'ORA remains path-backed');assert(files.xcf.includes('GimpDocument(str(path))'),'XCF remains path-backed');
const rows=[];
for(const ext of ['psd','PSD']){assert.equal(fingerprint({psd_path:'C:/car.'+ext,sourceBytesSha256:digest}),`file-sha256:${digest}`);rows.push({id:'psd-byte-attested',pass:true,ext});}
for(const ext of ['ora','XCF']){assert.equal(fingerprint({psd_path:'C:/car.'+ext,sourceBytesSha256:digest},composite),`composite-sha256:${composite}`);assert.equal(fingerprint({psd_path:'C:/car.'+ext,sourceBytesSha256:digest},fnv),`composite-fnv1a32:${fnv}`);assert.equal(durable('layered',`composite-sha256:${composite}`),false);assert.equal(durable('layered',`composite-fnv1a32:${fnv}`),false);rows.push({id:'session-only-composite-identity',ext,pass:true});}
assert.equal(fingerprint({psd_path:'C:/car.ora',sourceBytesSha256:digest},null),'');assert.equal(fingerprint({psd_path:'C:/car.xcf',sourceBytesSha256:digest},null),'');rows.push({id:'missing-ora-xcf-composite-identity',pass:true});
assert.equal(durable('layered',`file-sha256:${digest}`),true);assert.equal(durable('layered',`composite-sha256:${composite}`),false);rows.push({id:'durable-gate',pass:true});
// PSB helper behavior is intentionally recorded as unreachable: the actual W83
// endpoint rejects it, so this synthetic adapter result cannot be a committed load.
assert.equal(fingerprint({psd_path:'C:/car.psb',sourceBytesSha256:digest}),`file-sha256:${digest}`);assert(!validator.includes("'.psb'"));rows.push({id:'psb-helper-versus-loader-boundary',pass:true,helperWouldClassify:'file-sha256',route:'rejects extension'});
assert(!validator.includes("'.unknown'"));rows.push({id:'unknown-format',pass:true,route:'rejects extension before import'});
assert(files.canvas.includes("_spbBeginSourceLoad(normalizedPath, 'layered')"));assert(files.canvas.includes('info.sourceKind||tx.kind||_spbCommittedSourceKind'));rows.push({id:'committed-kind-propagation',pass:true,kind:'layered'});
const report={work_item:'W95 independent source-format boundary review',date:'2026-10-04',status:'PASS_WITH_LIMITS',oracle:{path:oraclePath,sha256:expected.oracle,cases:7,frozenBeforeReportAndSource:true},sources:{canvas:{path:canvasPath,sha256:expected.canvas},server:{path:serverPath,sha256:expected.server},routes:{path:routePath,sha256:expected.routes},oraAdapter:{path:importPath,sha256:expected.ora},xcfAdapter:{path:xcfPath,sha256:expected.xcf},partMemoryController:{path:controllerPath,sha256:expected.controller}},counts:{executableAssertions:rows.length,passed:rows.length,failed:0,providers:0,native:0},rows,findings:['W94 identity mapping is correctly session-only for .ora/.xcf: the browser ignores their sourceBytesSha256 for durable identity and uses composite-sha256 or legacy composite-fnv1a32. The saved-owner gate accepts file-sha256 for layered sources only.','W83 parser branches are format-bounded: PSD parser input is copied/hashed from the exact snapshot; ORA opens ZipFile(path), XCF opens GimpDocument(path). ORA/XCF compatibility is preserved, but ABA byte attestation is not provided for those adapters.','W94’s PSB assertion is unreachable through this actual loader: W83 _validate_psd_path accepts only .psd/.ora/.xcf. The helper would map a synthetic .psb+digest to file-sha256, but no supported source load commits it. Avoid presenting PSB as verified by this route until route/parser support is evidenced.','The loader starts all three supported formats with kind layered and source-result settlement preserves tx.kind. Durable checks consult current transaction kind, so a claimed nonlayered kind is not derived from the filename in the tested route.'],limits:['W94’s eight-case function test and W83’s prior real Flask/PSD/OpenRaster tests are separately reported; this review did not rerun their heavy import suite. W83 report says XCF path dispatch only, with no real XCF raster fixture.','The present review executes actual identity and durable-gate functions, but not a complete import→rasterize→canvas-commit or project save/reopen.','No native, provider, browser, server mutation, or production edit.']};
const out=path.join(root,'docs/handoff_reports/AI_HELPER_14H_LAYERED_IDENTITY_W95_REVIEW_2026-10-04.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
