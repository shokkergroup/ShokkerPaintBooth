const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const support = fs.readFileSync('server_routes/paint_recolor_support.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  'engine.hsv_to_rgb_vec(new_h, new_s, new_v)',
  'engine.write_tga_24bit(recolored_path, recolored)',
  'Recolor mask decode failed',
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns recolor implementation: ${needle}`);
});

[
  'from server_routes.paint_recolor_support import apply_paint_recolor_impl',
  'def apply_paint_recolor(',
  'return apply_paint_recolor_impl(',
  'engine=engine',
  'logger=logger',
  'decode_spatial_mask_payload=_decode_spatial_mask_payload',
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  'def apply_paint_recolor_impl(',
  'mask_has_include=False',
  'decode_spatial_mask_payload(',
  'expected_shape=(h, w)',
  'engine.hsv_to_rgb_vec(new_h, new_s, new_v)',
  'engine.write_tga_24bit(recolored_path, recolored)',
].forEach((needle) => {
  if (!support.includes(needle)) failures.push(`paint_recolor_support.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/paint_recolor_support.py"')) {
  failures.push('runtime manifest missing paint_recolor_support.py');
}
if (!targets.includes('"server-paint-recolor-support"')) {
  failures.push('context target missing server-paint-recolor-support');
}

if (failures.length) {
  console.error('[spb_guard_server_paint_recolor_support] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_paint_recolor_support] OK');
