// Load paint-booth-0-finish-data.js in a vm sandbox to catch RUNTIME breakage that
// `node --check` (syntax only) misses — e.g. a top-level reference to a deleted const
// (the 2026-06-03 MC_DEFS brick). Exit 0 if the module evaluates AND validateFinishData
// is defined (proves the catalog finished building); exit 2 otherwise.
// Usage: node scripts/check_finish_data_loads.js <path-to-finish-data.js>
const fs = require("fs"), vm = require("vm");
const FD = process.argv[2];
if (!FD || !fs.existsSync(FD)) { console.log("FAIL: file not found: " + FD); process.exit(2); }
const src = fs.readFileSync(FD, "utf8");
const sb = {
  console: { log() {}, warn() {}, error() {}, info() {} },
  window: {}, navigator: { userAgent: "" }, location: { href: "" },
  document: { addEventListener() {}, getElementById() { return null; }, querySelector() { return null; },
              querySelectorAll() { return []; }, createElement() { return { style: {}, appendChild() {} }; } },
  module: { exports: {} }, exports: {}, require: () => ({}), setTimeout() {}, clearTimeout() {},
  process: { env: {}, platform: "win32", versions: { node: "22" }, argv: [] }, Buffer: { from: () => ({}) },
};
sb.global = sb; sb.globalThis = sb;
vm.createContext(sb);
try {
  vm.runInContext(src, sb, { filename: FD });
  const g = (k) => (sb[k] !== undefined ? sb[k] : (sb.window && sb.window[k]));
  if (typeof g("validateFinishData") !== "function") {
    console.log("FAIL: validateFinishData not defined — module aborted before the catalog built (runtime error before its declaration)");
    process.exit(2);
  }
  g("validateFinishData")();
  console.log("OK: finish-data evaluates + catalog builds (validateFinishData present)");
  process.exit(0);
} catch (e) {
  console.log("FAIL: finish-data threw at load: " + e.message);
  process.exit(2);
}
