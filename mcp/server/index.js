#!/usr/bin/env node
/* Shokker Paint Booth — MCP server (SPB-AI 2026-09-30)
 *
 * Lets Claude Desktop / Claude Code or Codex use the buyer's own assistant plan to design iRacing paints.
 * Pure Node, ZERO dependencies: a minimal MCP implementation (JSON-RPC 2.0 over stdio, newline-delimited).
 *
 *   Claude / Codex <--stdio MCP--> this process --HTTP 127.0.0.1:59876/api/mcp/call (pairing token)--> Shokker server --long-poll--> app page
 *
 * The app must be open (Pro mode) with "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth" switched ON in the AI panel settings.
 * Env: SPB_PORT (default 59876), SPB_MCP_TOKEN_FILE (default %APPDATA%/ShokkerPaintBooth/mcp/token.txt).
 */
'use strict';
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

// CX2 2026-10-09 (lane CODEX-INTEGRATE; from the ChatGPT/Codex agent's candidate, mcp/chatgpt/REPORT.md, reviewed + adapted): spb_assistant_context = ONE bounded READ-ONLY call that starts / resumes a design
// conversation (this assistant's recent chat turns, the tools it really has now, relevant encyclopedia excerpts, optionally the open paint's status + state). The module lives NEXT TO this file
// (server/assistant-context.cjs, packed by scripts/build_mcpb.py) - never ../chatgpt (a dev harness that must not ship). KILL SWITCH: env SPB_CX2_OFF=1 hides the tool and restores the old instruction text.
const CX2 = !process.env.SPB_CX2_OFF;
let ASSISTANT_CONTEXT = null;
if (CX2) { try { ASSISTANT_CONTEXT = require('../chatgpt/assistant-context.cjs'); } catch (e) { /* module missing (old bundle): run without the tool */ } }
// CX3 2026-10-09 (lane CODEX-INTEGRATE-2; from the ChatGPT/Codex agent's candidate mcp/chatgpt/candidates/index.js.patch, reviewed + adapted). (1) spb_edit_layer takes a strict-hex `colour` (+ `colour_opacity` 0-100) = the app's native layer colour
// overlay for an ENTIRE paint layer (not a whole-car zone). (2) advice-only gate: while the buyer's newest app-chat message is advice-only ("advice only", "do not apply", "would X work"), every tool that is not read-only is refused until they ask for an
// edit. Both modules live NEXT TO this file (native-layer-colour.cjs, design-intent.cjs; pack them in scripts/build_mcpb.py) - never ../chatgpt. KILL SWITCH: env SPB_CX3_OFF=1.
const CX3 = !process.env.SPB_CX3_OFF;
let NATIVE_LAYER_COLOUR = null, DESIGN_INTENT = null, APP_CHAT_ADVICE = false, APP_CHAT_ADVICE_AT = 0;
if (CX3) { try { NATIVE_LAYER_COLOUR = require('./native-layer-colour.cjs'); } catch (e) { /* old bundle */ } try { DESIGN_INTENT = require('./design-intent.cjs'); } catch (e) { /* old bundle */ } }
const CX3_LAYER_NOTE = '\nFor an entire paint-layer colour-only change, use spb_edit_layer with the exact current group/layer (or ID) and colour #RRGGBB. This uses the native layer colour effect and preserves layers above it. It is not a whole-car zone. Read colour_overlay in current STATE. Before recolouring an unfamiliar layer, use spb_inspect_layer: empty pixels cannot produce a visible recolour, and a full opaque multi-colour layout needs region choices rather than a solid overlay if its design is to survive. For exact source-RGB replacement inside one paint layer use source_colour and colour with spb_edit_layer (optional replace_tolerance, default40); this edits source pixels through native Color Replace and chat Undo restores them. Material/finish changes use their scoped tools; do not apply paint colour to spec/alpha map layers.';

// ONLINE-AI 2026-10-09 (lane ONLINE-AI, _easy_claude_work/eval/online_ai/CAUSES.md): tool-side fixes for the 9 failures of the 52-scenario Claude run: per-kind graphic sizes (spb_tweak scale / rotation re-draw the
// RIGHT parameter, with the original put back when a re-draw fails), spb_tweak scale on a finish zone = direct edit_zone on the siblings that show (no planner re-stack that exposed the base colour), working zone =
// the zone of that write that shows most, part-name synonyms (bonnet, driver side...) in the unknown-part guard, dark-colour hue nudges that do not go brown, spec-only / undo / iRacing-folder notes, flames + per-kind
// size text in the add_graphic description. KILL SWITCH: env SPB_ONLINE_AI_OFF=1 restores the 1.4.1 behaviour and descriptions exactly.
const OAI = !process.env.SPB_ONLINE_AI_OFF;
// OA3 2026-10-10 (lane ONLINE-AI-3): colour_source_note on spb_tweak (a brightness / hue / saturation / colour tweak that lands on a colour-source zone cannot show) + the refinish wording in the spb_do text.
// Bank M-T01 t3 (put carbon fiber on the roof -> make the pattern smaller -> now a bit brighter): 1.4.4 baseline FAIL (brightness 25 applied to the "Carbon roof" colour-source zone, nothing_visible, the model reported it as done) -> target PASS. KILL SWITCH: env SPB_OA3_OFF=1.
const OA3 = !process.env.SPB_OA3_OFF;
// OA2 2026-10-10 (lane ONLINE-AI-2): spb_kit = online Claude drives the Sponsor Kit, Number Kit, Spec Doctor and Spec Autopilot of the app page (js/spb-online-kits.js). KILL SWITCH: env SPB_ONLINE_KITS_OFF=1 removes the tool and its instruction line.
const KITS = !process.env.SPB_ONLINE_KITS_OFF;
// MCP-KNOW 2026-10-10 (lane MCP-KNOW, _easy_claude_work/mcp_know/PROGRESS.md): a fresh-install Claude must know the app. APP-IQ exam (eval/app_iq): MCP-only Sonnet 119/180; Claude Code keeps only the first
// 2,048 chars of these instructions, and the skill was never invoked without a pointer. app-knowledge.cjs (next to this file, packed by scripts/build_mcpb.py) = a new instruction head (restraint short form,
// spec map, zone order, crush = scale, skill pointer), must-know sentences in tool descriptions, the app briefing + encyclopedia topic map once per session (first spb_status / spb_get_state / spb_encyclopedia),
// code-verified facts on spb_encyclopedia results and one note per read-only tool. KILL SWITCH: env SPB_MCPKNOW_OFF=1 = the 1.4.6 texts and results exactly.
const FRESH_KNOWLEDGE = require("../chatgpt/fresh-install/delivery/review/fresh-knowledge-v2.cjs");
let MK = null;
if (!process.env.SPB_MCPKNOW_OFF) { try { MK = require('./app-knowledge.cjs'); } catch (e) { /* old bundle: run without it */ } }
const VERSION = '11.0.3'; // [11.0.3 hover TLS fix 2026-10-17, Claude] follows the app version (no bridge behaviour change). Was 11.0.2: follows the app version (no bridge behaviour change). Was 11.0.1: follows the app version (picker-bake hotfix; no bridge behaviour change). MCP-KNOW 2026-10-10: app-knowledge.cjs (instruction head, description facts, briefing, verified facts; kill switch SPB_MCPKNOW_OFF). Was 1.4.6: OA4 2026-10-10 (ONLINE-AI-4): no server behaviour change; pairs with page js/spb-online-kits.js ok1.4, whose spb_kit place result now lists every named-but-unplaced part in not_placed + not_placed_note (bank KO-07 + probes KP-01..06: 5 of 5 silent drops on 1.4.5); page kill switch window.SPB_KIT_NOTPLACED_OFF. Was 1.4.5: OA3 2026-10-10 (ONLINE-AI-3): spb_kit remove honours the named parts (page ok1.3; found by bank item KO-15: remove took every sponsor kit), kit Undo obeys the BUSY + lease guards, colour_source_note on spb_tweak (brightness on a colour-source zone cannot show), spb_do finish-on-a-part = refinish keep_colour, no 2048 square for every template claim; kill switch env SPB_OA3_OFF=1 (page window.SPB_KIT_REMOVE_SCOPE_OFF / SPB_KIT_UNDO_GUARD_OFF). Was 1.4.4: // OA2 2026-10-10: CX3 merge (layer colour overlay, advice-only gate) + spb_kit (sponsor / number / spec kits). Was 1.4.3: // ONLINE-AI 2026-10-09 (2): render after the LAST change of a buyer request again (owner: "build yourself a way to render the car for me when you make those changes"; page P7 fixed in js/spb-intent-report.js, kill switch SPB_P7_OFF); was 1.4.2 (render only on request) and 1.4.1 (CX2 2026-10-09: spb_assistant_context + design-conversation instruction + render only after an authorized change (server: per-assistant chat routing); was 1.4.0)
//   // 1.4.0 APPCHAT 2026-10-09: spb_wait_for_message / spb_reply relay the in-app chat box to this assistant (+ wait-inbox.js wake-up for Claude Code); was 1.3.5
//   // W1MCP2 2026-10-09: spb_tweak re-draws a drawn graphic at a new size, hue tweak rotates solid colours (toward), 2 instruction sentences; was 1.3.4
//   // 2026-10-08 AITER: spb_tweak (iterate on ONE zone), unknown-part honesty guard (SPB_MCP_NOPARTGUARD), working_zone tracking (SPB_MCP_NOTWEAK); was 1.3.3
const VERSION_PREV = '1.3.3';   // 2026-10-08 R9: multi-turn: undo/back-to-original = spb_undo (guard SPB_MCP_NOUNDOGUARD), relative tweaks, delegation words; was 1.3.2
// (prev)   // 2026-10-08 R4: typo/terse orders = concrete, plain whole-car recolour = spb_do body (not apply_scheme), named classic livery = confirm, finish families (carbon) before find_finishes; was 1.3.1 (M3)
//   // 2026-10-07 M3: over-asking fixes (effect / shade on a named part = concrete, two candidates -> most prominent), how-to -> spb_encyclopedia, page-freeze root fix in zone-kit; was 1.3.0 (M2)
//   // 2026-10-07 M2: ask-first gate, slim tool texts, measured block everywhere (build_mcpb.py VERSION); was 1.2.0 (S8)
const PORT = Number(process.env.SPB_PORT) || 59876;
const SUPPORTED = ['2025-06-18', '2025-03-26', '2024-11-05'];
function log(...a) { try { process.stderr.write('[spb-mcp] ' + a.join(' ') + '\n'); } catch (e) { /* ignore */ } }

// ------------------------------------------------------------------ tools (descriptions + schemas come from the app itself: tools.json is generated by scripts/build_mcpb.py)
const SERVER_DIR = __dirname;
let GENERATED = [];
try { GENERATED = JSON.parse(fs.readFileSync(path.join(SERVER_DIR, 'tools.json'), 'utf8')); } catch (e) { log('tools.json missing: using the built-in minimal tool list'); }

const PRIVATE_LAYER_COLOUR = require('../chatgpt/native-layer-colour.js');
const CAR_KNOWLEDGE = require('../chatgpt/car-knowledge/lookup.cjs');
const READ_ONLY = new Set(['spb_inspect_layer', 'spb_car_knowledge', 'spb_assistant_context', 'spb_wait_for_message', 'spb_status', 'spb_encyclopedia', 'spb_get_state', 'spb_get_zones', 'spb_get_car_map', 'spb_preview', 'spb_design_recipes', 'spb_find_finishes', 'spb_suggest_finishes', 'spb_finish_details', 'spb_compare_finishes',
  'spb_browse_catalog', 'spb_find_patterns', 'spb_find_spec_patterns', 'spb_manual', 'spb_check_setup', 'spb_describe_paint', 'spb_look_at_paint', 'spb_check']);
const NAME_MAP = { // MCP tool name -> app tool name
  spb_inspect_layer: 'inspect_layer', spb_status: 'status', spb_get_state: 'get_state', spb_get_zones: 'zones', spb_get_car_map: 'get_car_map', spb_preview: 'preview', spb_request_parts: 'request_parts',
  spb_design_recipes: 'design_recipes', spb_apply_scheme: 'apply_scheme', spb_render: 'render', spb_reset_zones: 'reset_zones', spb_add_zone: 'add_zone', spb_edit_zone: 'edit_zone', spb_duplicate_zone: 'duplicate_zone', spb_edit_layer: 'edit_layer',
  spb_undo: 'undo', spb_suggest_finishes: 'suggest_finishes', spb_find_finishes: 'find_finishes', spb_finish_details: 'finish_details', spb_compare_finishes: 'compare_finishes', spb_browse_catalog: 'browse_catalog',
  spb_find_patterns: 'find_patterns', spb_find_spec_patterns: 'find_spec_patterns', spb_manual: 'get_help', spb_check_setup: 'check_setup', spb_add_graphic: 'add_graphic', spb_describe_paint: 'describe_paint', spb_refinish: 'refinish', spb_look_at_paint: 'look_at_paint', spb_mark_elements: 'mark_elements', spb_do: 'do', spb_check: 'check', spb_kit: 'kit', // HELPER V3 S8 2026-10-06: frame tools (js/spb-mcp-frames.js in the app page)
};
const TWEAK_TOOL = { name: 'spb_tweak', description: 'THE tool for iterating on the zone you just made / changed ("smaller", "bigger", "rotate it", "brighter", "darker", "more shiny", "less intense", "change the pink to blue"). Works on the working_zone (the zone the last write touched) unless zone_name / zone_id names another. One property moves, nothing else: change = scale (pattern / texture size; direction down = smaller / finer) | rotation | brightness | hue | saturation | shine | metal | opacity (pattern strength) | intensity (finish strength) | colour (needs to_colour #hex). direction up|down; amount a_bit | normal | a_lot, or degrees for rotation. Returns before / after of that property and the measured block. Pass buyer_said = the buyers words verbatim.',
  inputSchema: { type: 'object', properties: { buyer_said: { type: 'string', description: 'REQUIRED: the buyer words, verbatim' }, change: { type: 'string', enum: ['scale', 'rotation', 'brightness', 'hue', 'saturation', 'shine', 'metal', 'opacity', 'intensity', 'colour'] }, direction: { type: 'string', enum: ['up', 'down'] }, amount: { description: 'a_bit | normal | a_lot, or degrees (rotation)' }, to_colour: { type: 'string', description: '#rrggbb for change=colour (you resolve the colour word)' }, toward: { type: 'string', description: 'change=hue only: the colour word the buyer wants MORE of ("a bit more orange" -> orange); hue then moves toward it' }, zone_name: { type: 'string' }, zone_id: { type: 'string' } }, required: ['buyer_said', 'change'] } };
// APPCHAT 2026-10-09 (owner: "I type into the chatbox in the app and you make the changes, and I can also chat with you here"): the buyer’s in-app chat box relays to this assistant.
const CHAT_TOOLS = [
  { name: 'spb_wait_for_message', description: 'APP CHAT: wait for the buyer to type in the Shokker app’s own chat box. Blocks until they send a message (or timeout_s passes, default 170): returns messages [{text}] = the BUYER’S OWN WORDS (use them verbatim as buyer_said), or none:true on timeout (just call it again while the buyer wants app chat). After you act, answer with spb_reply, then wait again. Stop when the buyer says they are done or switches back to this chat.', inputSchema: { type: 'object', properties: { timeout_s: { type: 'number', description: 'seconds to wait (10-590, default 170)' } } } },
  { name: 'spb_reply', description: 'APP CHAT: show your answer to the buyer in the Shokker app’s chat box (plain short sentences, what changed and what you chose). Use after every message that came from spb_wait_for_message.', inputSchema: { type: 'object', properties: { text: { type: 'string' }, reply_to: {type:'integer',description:'Copy the seq of the latest buyer message returned by spb_wait_for_message. Required for document-scoped app chat; an earlier paint reply is refused.'}, finishes: { type: 'array', description: 'when you suggest finishes: 2-8 catalogue keys from spb_suggest_finishes / spb_find_finishes, as "base::gloss" or {key, colour (#hex you propose), why}. The app shows each as a thumbnail card with Use this + Show me more (both come back to you as the buyer’s next message).', items: {} }, use_on: { type: 'string', description: 'the part the cards apply to, e.g. "the base" (default the body)' } }, required: ['text'] } },
];
// OA2 2026-10-10: the kit tool. One tool, three kits, so the surface stays small. Only on an explicit request; honest + measured results (the page builds them).
const KIT_TOOL = { name: 'spb_kit', description: 'The buyer\'s Sponsor Kit, Number Kit and Spec tools, driven for real. ONLY when the buyer asks for it in words ("my logo on both doors in chrome foil", "number 32 on the doors and roof", "check my spec"); never to improve a paint unasked. Pass buyer_said VERBATIM. ' // 2026-10-10 orchestrator: description trimmed 2,184 -> <2,048 chars (Claude Code cuts the tail); wording only
  + 'kit "sponsor" (action place | remove): ONE logo on the named parts, same real size on each, turned to read right, optionally in a material (chrome foil, gold leaf, gold foil, matte / gloss vinyl). Logo = a layer holding it (logo_layer, from spb_status) or a file path the buyer gave (logo_file). '
  + 'kit "number" (place | remove): a car number (1 to 4 digits or letters) on left door / right door / roof, with fill, outline, font, material; anything the buyer did not say stays the app default (the result lists the style used). Numbers already on the paint: the tool asks replace vs alongside (existing), changing nothing until answered. '
  + 'kit "spec": action check = Spec Doctor report (read-only; renders the spec map once, 20-120 s); fix = apply ONE Doctor fix (finding key + fix id) the buyer asked for; propose = Spec Autopilot proposal, one material per layer (read-only, assigns nothing); apply = give the proposed materials to the layers, ONLY after the buyer saw the proposal and agreed (buyer_agreed:true; apply changes spec only, never artwork, zones or colours). '
  + 'action undo takes the newest kit change back (spb_undo does it too, as one step). Results say what changed (layers, parts, real size in cm, spec M / R / C, pixel counts on the part), what was NOT changed, and undo_with: relay those numbers, never invent one. A kit needs the car\'s layers and named parts; a flat picture is refused, nothing changes.'
  + (OA3 ? ' REMOVE takes off ONLY the kit on the parts you name in parts ("take the logo off the left door" = parts ["left door"]); with several kits and no parts the tool asks which one; a kit that also covers other parts is not split: the tool asks and names the parts to name for the whole kit. Never say "nothing else was lost" without reading removed_layers.' : ''),
  inputSchema: { type: 'object', properties: {
    buyer_said: { type: 'string', description: 'the buyer\'s words, verbatim, on EVERY call (required for place / remove / fix / apply)' },
    kit: { type: 'string', enum: ['sponsor', 'number', 'spec'] },
    action: { type: 'string', enum: ['place', 'remove', 'undo', 'check', 'fix', 'propose', 'apply'], description: 'sponsor / number: place (default) or remove; spec: check, fix, propose, apply; undo: the newest kit change' },
    logo_layer: { type: 'string', description: 'sponsor: the name or id of the layer that holds the logo' },
    logo_file: { type: 'string', description: 'sponsor: absolute path of a PNG / JPG / SVG logo file the buyer gave (instead of logo_layer)' },
    parts: { type: 'array', items: { type: 'string' }, description: 'sponsor: ONLY the parts the buyer named: left door, right door, both doors, hood, trunk, left rear quarter, right rear quarter, left tv panel, right tv panel, left roof rail, right roof rail, roof rails' },
    size: { type: 'number', description: 'sponsor / number: percent of the default size (sponsor 20-300, number 20-160); only when the buyer asked for bigger / smaller' },
    size_cm: { type: 'number', description: 'sponsor: wanted real width of the logo in cm (the same on every part)' },
    material: { type: 'string', enum: ['none', 'chrome', 'gold', 'goldfoil', 'matte', 'gloss', 'satin'], description: 'sponsor: none | chrome (chrome foil) | gold (gold leaf) | goldfoil (solid gold) | matte | gloss; number: none | chrome | gloss | matte | satin. Only if the buyer asked.' },
    extra_turn: { type: 'number', description: 'sponsor: extra quarter turn in degrees (90, 180, 270) if the buyer asked' },
    number: { type: 'string', description: 'number: the digits / letters, 1 to 4' },
    places: { type: 'array', items: { type: 'string' }, description: 'number: left door, right door, both doors, roof' },
    fill: { type: 'string', description: 'number: fill colour #RRGGBB' },
    outline: { description: 'number: first outline {color:#RRGGBB, width: percent of the number size 0-25}' },
    outline2: { description: 'number: second outline, same shape' },
    shadow: { description: 'number: false = no shadow, or {color, alpha, dist, soft}' },
    font: { type: 'string' }, bold: { type: 'boolean' }, italic: { type: 'boolean' }, slant: { type: 'number' }, spacing: { type: 'number' },
    roof_from: { type: 'string', enum: ['driver', 'passenger'] },
    existing: { type: 'string', enum: ['replace', 'alongside'], description: 'number: what to do with numbers already on the paint (only after the buyer said)' },
    finding: { type: 'string', description: 'spec fix: the finding key from the last check' }, fix: { type: 'string', description: 'spec fix: the fix id offered for that finding' },
    buyer_agreed: { type: 'boolean', description: 'spec apply: true only when the buyer saw the proposal and agreed' },
    only_layers: { type: 'array', items: { type: 'string' }, description: 'spec apply: apply only these layers of the proposal' },
    style: { type: 'number', description: 'spec propose / apply: 0 showroom (glossy) .. 1 race-worn; default 0.5' }
  }, required: ['kit', 'action'] } };
const STATIC_TOOLS = [
  TWEAK_TOOL,
  ...CHAT_TOOLS,
  ...(KITS ? [KIT_TOOL] : []),
  // MCP-RENDER 2026-10-09 (owner: "Build yourself a way to Render the car for me when you make those changes")
  { name: 'spb_render', description: 'RENDER the car for real (the app’s RENDER button): builds the final paint + spec files and saves them to the car’s iRacing folder. Call it ONCE when a buyer request is finished (not after every tool call). Takes about 10-60 s. Returns seconds, zones, files_saved; rendered:false + app_said when the app would not start it (e.g. nothing changed since the last render).', inputSchema: { type: 'object', properties: {} } },
  // RESET-ZONES 2026-10-09 (owner: "wouldn't it be easier to RESET ALL ZONES? Then just add purple instead of muting so many of the other zones")
  { name: 'spb_reset_zones', description: 'START FRESH in ONE call: removes every zone except the catch-all (Everything Else) and the zones in keep; one undo step (spb_undo brings them all back). Use it instead of muting zones one by one when the buyer wants a new base look over most of the car or to start over; then edit the catch-all for the new base and stack extra looks in kept zones. Needs buyer_said + confirm:true.', inputSchema: { type: 'object', properties: { buyer_said: { type: 'string', description: 'REQUIRED: the buyer words, verbatim' }, confirm: { type: 'boolean' }, keep: { type: 'array', items: { type: 'string' }, description: 'zone ids or exact zone names to keep' } }, required: ['buyer_said'] } },
  { name: 'spb_status', description: 'FIRST CALL. Connected? The car, its NAMED PARTS (position, front end, roof-line), key_parts_missing, PSD layers, zone count.', inputSchema: { type: 'object', properties: {} } },
  { name: 'spb_get_zones', description: 'Every zone: what it covers, visible_pct it really wins, its look. LOWER index wins overlaps.', inputSchema: { type: 'object', properties: {} } },
  { name: 'spb_preview', description: 'Live preview image of the flat car sheet + measured colour shares. spec=true adds the spec map (red metal, teal matte, black gloss); parts=false skips the parts map.', inputSchema: { type: 'object', properties: { spec: { type: 'boolean' }, parts: { type: 'boolean' } } } },
  { name: 'spb_request_parts', description: 'When key_parts_missing is not empty: asks the BUYER to box each part in the Shokker AI panel (once per car). Tell them, then re-check spb_get_car_map.', inputSchema: { type: 'object', properties: { parts: { type: 'array', items: { type: 'string' }, description: 'e.g. ["left side","right side","hood","roof"]' } } } },
  { name: 'spb_undo', description: 'Undo the last change(s) made through this bridge on the loaded paint. steps default 1. "Undo that" = 1; "undo both" = 2; "back to how it was / the original" = the number of changes made to that part in this chat (all of them). ALWAYS use this for undo / revert / back-to-original: never re-set a colour by hand.', inputSchema: { type: 'object', properties: { steps: { type: 'number' } } } },
  // ONLINE_GROUNDING 2026-10-04: the SPB Encyclopedia (the same articles the offline helper and the in-app online AI answer from), read straight from the server: works without the app page
  { name: 'spb_encyclopedia', description: (MK && !process.env.SPB_FRESH_KNOWLEDGE_OFF ? 'SPB Encyclopedia (buttons, sliders, workflows, spec maps, troubleshooting, iRacing / Trading Paints). Retrieve relevant articles for how-to questions. Bundled verified facts and current measured capabilities override conflicting historical article text; cite supported article titles. confident=false = weak match. Works with no paint open.' : 'SPB Encyclopedia (every button, slider, workflow, spec maps, troubleshooting, iRacing / Trading Paints). Use FIRST for any how-to / why / what-is question; answer from the articles (their labels and numbers), never contradict them. confident=false = weak match. Works with no paint open.'), inputSchema: { type: 'object', properties: { query: { type: 'string', description: 'the question in plain words' }, k: { type: 'integer', description: 'how many articles (1-8, default 4)' } }, required: ['query'] } },
];
// ONLINE-AI 2026-10-09: description add-ons. tools.json is generated from the app page (js/spb-mcp-texts.js) and can lag it (the shipped 1.4.1 file had no flames line: B-0045 asked for flames and Claude drew
// a different graphic); the per-kind size table is what the model needs to draw / re-size a graphic without guessing (checker has size, not n). Each add-on is skipped when the text already says it.
const DESC_ADD = {
  spb_add_graphic: (d) => d
    + (/flames \{/i.test(d) ? '' : ' FLAMES: kind flames {style: hotrod | tribal | ghost | truefire, colours, length 0.2..1 (0.9+ on the long sides; the default stops at about 40%), licks, curl, scale}; the licks start at the nose end of the part.')
    + (/SIZE PARAMS/.test(d) ? '' : ' SIZE PARAMS by kind (fractions of the part height): checker {size 0.07, u0,u1,v0,v1 = the block it fills (default: the whole part, or the rear fifth when the buyer asks for a band / edge); colours [A, B] draws BOTH colours as a real checkerboard (a checkered flag = ["#ffffff", "#000000"])}; dots {spacing, size}; stripes {n, w, gap, angle}; waves {n, w, spacing, amp, wavelength}; chevrons {n, w, depth}; speed_lines {n, wmin, wmax, lenmin, lenmax, angle}; rings {n, r0, r1, w0, w1}; rays {n, duty}. n is a COUNT, never a size. Later "smaller / bigger / rotate" = spb_tweak, not a new graphic.'),
  spb_render: (d) => d + ' Call it ONCE, after the LAST change of a buyer request that changed the paint (not after every tool call of one request). Never for a complaint, question or advice that changed nothing: with no change made it does nothing unless the buyer asked to render / save / export: then pass buyer_asked_render:true. Say the seconds and files saved.',
  spb_refinish: (d) => d + ' NOT for a named LAYER or part ("the Black Base layer", "the Logos layer", "the roof"): that is spb_do with a layer / part target. Here the target is a COLOUR and it recolours those pixels wherever they sit (the black may live on another layer).',
  // OA3 2026-10-10 (lane ONLINE-AI-3): bank M-T01 "put carbon fiber on the roof": verb recolour + a finish builds a colour-source zone ("Carbon roof") whose brightness cannot show (1.4.4 baseline FAIL on t3), verb refinish keeps the colours per zone (PASS). Kill switch SPB_OA3_OFF.
  spb_do: (d) => d + (OA3 && !/never recolour/i.test(d) ? ' A finish named alone on a part that has no colour in the request ("carbon fiber on the roof", "matte hood", "chrome mirrors") is ALWAYS verb refinish with look.finish.keep_colour:true, never recolour.' : ''),
  spb_tweak: (d) => d + ' Works on drawn graphics too (scale re-sizes the right parameter of that kind; rotation turns stripes, speed lines and rays, the others cannot rotate and the tool says so). Finish-only looks (carbon, chrome, matte) are spec-only: applied but invisible in the flat preview (spec_only_note). Result: undo_with.',
};
const SCHEMA_ADD = {
  spb_render: { type: 'object', properties: { buyer_asked_render: { type: 'boolean', description: 'true when the buyer asked in words to render / save / export / send to iRacing, even if nothing changed since the last render. Leave it out for a render after your own changes.' } } },
};
function allTools() {
  const seen = new Set(), out = [];
  for (const t of STATIC_TOOLS.concat(CX2 && ASSISTANT_CONTEXT ? [ASSISTANT_CONTEXT.TOOL] : [], [CAR_KNOWLEDGE.TOOL], GENERATED)) { if (seen.has(t.name)) continue; seen.add(t.name); const d0 = (OAI && DESC_ADD[t.name]) ? DESC_ADD[t.name](t.description || '') : t.description; out.push({ name: t.name, description: require('../chatgpt/named-part-guard.cjs').toolDescription(t.name, require('../chatgpt/geometry-authority.cjs').toolDescription(t.name, MK ? MK.desc(t.name, d0 || '') : d0)), inputSchema: (OAI && SCHEMA_ADD[t.name]) ? SCHEMA_ADD[t.name] : (t.inputSchema || { type: 'object', properties: {} }), annotations: { readOnlyHint: READ_ONLY.has(t.name), destructiveHint: false, openWorldHint: false } }); }
  return NATIVE_LAYER_COLOUR ? out.concat([PRIVATE_LAYER_COLOUR.INSPECT_TOOL]).map(NATIVE_LAYER_COLOUR.tool).map(PRIVATE_LAYER_COLOUR.tool) : out;          // CX3: adds colour / colour_opacity to spb_edit_layer. OA2 2026-10-10 FIX: W25's merge had put this line in partCandidates() (a part-name list: tool() returned each string unchanged), so tools/list never advertised colour; moved here (kill switch SPB_CX3_OFF)
}

// M2 2026-10-07 (lane M2, _easy_claude_work/eval/m2/REPORT.md): RESTRAINT first (M1: 6 of 8 HARM = acting on vague / mood / reference / complaint requests), then the workflow; ~45% shorter.
// M3 2026-10-07 (classes OVER-ASKING on clear requests: train A-0064 / A-0445 'mud / dirt on the lower doors', A-0042 'dark roof', A-0424 'colour from my logo' with two logos;
// HOW-TO without the encyclopedia: A-0042 t1 'can I paint the windows', B-0371): concrete = part + colour / shade / effect; questions -> spb_encyclopedia. Duplicated tool text trimmed (budget 11.86k tok).
const INSTRUCTIONS_BASE = [
  'You drive Shokker Paint Booth (SPB), an app that designs iRacing car paints, through the spb_* tools. ' + (OA3 ? 'The paint is a 2D template sheet that may contain editable layers. Resolution, panel layout and available parts vary by the loaded document. Use exact current layer IDs for layer edits and only current verified named parts (region {part:"left side"}) for panel placement; never infer coordinates from a car name, catalog facts or big grid boxes.' : 'The paint is ONE flat 2048x2048 sheet of the whole car cut open (two side panels, hood, roof, trunk, bumpers, spoiler). Place everything on NAMED PARTS (region {part:"left side"}), never on big grid boxes.') + '',
  'RESTRAINT (the buyer\'s paint is their work; most harm comes from acting too soon): (1) VAGUE, mood, taste or reference requests ("make it pop", "something kind", "pastel livery", "Brazil colours", "like the car that won Daytona", "something nobody has seen"): change NOTHING; ask ONE short question or offer 2-3 concrete options (colours + where + finish; spb_design_recipes / spb_suggest_finishes help) and stop. Act when they pick, or when they said "surprise me / just do it". CONCRETE requests are NOT vague: a part (or the car) + a colour, shade, finish family, effect, pattern idea or a named classic livery ("holo roof", "dark roof", "mud on the lower doors", "tribal on both fenders", "Martini livery"): act now, choose the closest catalogue match / hex yourself, say what you chose, offer 1-2 alternatives AFTER; never ask which variant. Terse, slangy or misspelt orders are concrete too ("hod to chrom", "bumpr red", "roof 2 tone black n gold", "mak teh roof blak"): do them; only a real question (how / can I / what / why / do I need) is a how-to. Two candidates (two logos): use the most prominent, say which. When the buyer answers your question (a place, a colour, "yes", "less"), act on it with sensible defaults; never ask a second time. (2) COMPLAINTS ("looks plastic", "numbers are hard to read", "looks off"): answer in a sentence or two, offer 1-3 fixes, wait. (3) QUESTIONS ("can I paint the windows?"), how-to and render / iRacing / file trouble: call spb_encyclopedia (spb_check_setup for files) and answer from it, change nothing. (4) Never paint a whole scheme or the whole car unasked. (5) Change ONLY the parts the buyer named ("the right door" = right side; a part named as the reference, "same as the left", is not a target).',
  'Every write tool takes buyer_said = the buyer\'s latest message, VERBATIM (spb_do: text); never add your own words, a proposal or "approved" to it. Never mute or delete the buyer\'s zones unless they asked. The app reads them: vague / complaint / question words, or a whole-car change without confirm:true, return ask_back with options and change NOTHING: put that to the buyer and stop. confirm:true only when the buyer\'s words name the whole-car change (colours / finish, or a named classic livery such as Gulf / Martini), approved your proposal, or said surprise me. spb_do: put the frame in frame {act, ops:[...]} as JSON objects.',
  'Workflow: spb_status (if key_parts_missing: spb_request_parts, tell the buyer to show the parts, re-check). Existing livery edits: spb_do with a frame (preferred) or spb_refinish. "Make the car purple" / "whole car dark blue" = spb_do recolour target body + confirm:true (it keeps the accent zones and art; never spb_apply_scheme for a plain recolour). A named classic livery (Gulf, Martini, Rosso Corsa...) = spb_design_recipes then spb_apply_scheme with confirm:true at once (the name IS the request); never ask the buyer to pick a layout. The scheme tool recolours the whole body first by itself; report only what measured shows. Follow-ups on your own last change: "a bit darker / lighter / more X / less X" = spb_do recolour (or edit_zone color) with a NEW hex clearly different (about 15-20% lightness or a visibly different hue), never a tiny saturation nudge; if measured says no_visible_change, redo it once with a bigger step. "Undo / take it back / back to how it was / original" = spb_undo (steps = how many changes you made since the original), NEVER a hand-set colour. "Go crazy / do something cool / pick for me / I am lost" = the buyer handed you the choice: act now with confirm:true (state what you chose, offer alternatives after); if the app still returns ask_back, tell the buyer in one line and offer your top pick as a single yes/no. Shine-only looks (chrome, matte, carbon...) on an existing colour: keep_colour true, never false unless the buyer named a new colour (false repaints the part with the hidden base colour). Looks: use finish.family for chrome, satin chrome, dark chrome, metallic, pearl, candy, brushed, matte, satin, gloss, carbon (carbon fibre); spb_find_finishes only for other looks. Liveries the buyer asked for: spb_design_recipes, then spb_apply_scheme (base colour at the bottom; zones_touched lists zone numbers, 0 = top). Finishes: spb_suggest_finishes / spb_find_finishes, never invent keys. Band geometry: height 0 = roof-line .. 1 = rocker; length 0 = front .. 1 = rear.',
  'After EVERY change read measured (verdict, outside_px, decal_px, findings, line) and problems_found_by_app. verdict ok = say what the line says. reported / substituted / no_visible_change / findings = tell the buyer exactly that, offer spb_undo, never claim a clean result. Report only what the tool results show.',
  'ITERATING ON ONE LOOK (the most common use: "do X on this layer / zone" -> buyer looks -> "pattern smaller" -> "brighter, pink to blue"): keep working on the SAME zone. After a write the result names working_zone. Every follow-up on that look ("smaller / bigger / finer", "rotate it", "brighter / darker / lighter", "more / less shiny", "more / less intense / subtle", "more purple", "change the pink to blue") = spb_tweak (one property of that zone, nothing else moves), never a new zone, never a new scheme. A colour swap inside the look = spb_tweak change colour with to_colour hex. A tweak asked twice ("again", "a bit more") = the same call again. If measured says no_visible_change, say honestly that the change was applied but is too small / too fine to see here, give the numbers, and offer a bigger step. "Undo" is still spb_undo. Sizes of a DRAWN graphic (checker squares, stripes, dots): spb_tweak scale re-draws it with one undo + one draw; never undo more steps than you made and never re-draw by hand. "A bit more orange / bluer / pinker" = spb_tweak change hue with toward = that colour word (it rotates the solid colour; do not use saturation for it). Shine-only finishes (carbon, chrome, matte) have no visible size / brightness in the flat preview: say that once, offer spb_preview spec=true, and do not redo or add zones to chase it.',
  'PARTS YOU CANNOT LOCATE: if the buyer names a part (hood, spoiler, left door...) that spb_status / spb_get_car_map does not list for this car, or a tool answers unknown_part, do NOT guess and paint. Ask: "I can\'t tell where the <part> is on this template. Send me a picture with it circled, or tell me roughly where it is on the sheet (top middle, lower left...)." Then use their answer (spb_look_at_paint / their picture) and place it by region rect, and say which area you used.',
  'Numbers, sponsors and logos stay untouched unless named. Spec-only ("only the shine", "keep the colours"): a FOUNDATION finish (base::f_chrome, base::f_satin_chrome, base::f_metallic, base::f_pearl, base::f_brushed, base::matte, base::satin, base::gloss) on the zones that already cover the area with NO color; never base::chrome / base::metallic / base::candy for that (they repaint). Spec map: R metal, G roughness, B clearcoat (16 = max gloss).',
  ...(CX2 && ASSISTANT_CONTEXT ? ['DESIGN CONVERSATION: at the start, after a reconnect, or when the buyer refers to earlier options ("the second one"), call spb_assistant_context with their question (include_paint=true when you discuss this paint): it returns your recent chat turns with the buyer, the tools you really have now, relevant SPB guidance and, if asked, the open car / layers / zones. Keep their stated colours, protected artwork and rejected looks; a proposal of yours or a hypothetical question is not an edit approval. Get a real preview before visual judgments. Old help cards may describe tool limits that no longer apply: trust the current tool list and actual results.'] : []),
  'APP CHAT: when the buyer asks you to "listen to / connect to my Shokker chat" (or you were started for it), loop: spb_wait_for_message -> act on the messages (they ARE the buyer’s words) -> spb_reply with a short plain answer -> spb_wait_for_message again. Every answer the buyer should see goes through spb_reply while app chat is on; when you suggest finishes, pass their keys in spb_reply finishes so the buyer SEES thumbnails ("Show me more" = page on with exclude). Stop when they say stop / done or talk to you here instead. A message marked again:true was handed to an earlier wait that never answered (e.g. you were restarted): check the car first in case it is already done, then answer it.',
  ...(KITS ? ['KITS: spb_kit places a SPONSOR logo on named parts (kit sponsor), a car NUMBER on doors / roof (kit number), or checks / fixes the SPEC (kit spec). Use it ONLY when the buyer asks for that in words; never to improve a paint unasked, and vague ("make the materials realistic") = action propose, read it out, wait. Pass buyer_said verbatim on every call. Sponsor: logo_layer = the layer that holds the logo (spb_status lists layers) or logo_file = a path the buyer gave; parts = only what they named; a material only if they said so. Number: number + places they named; fill / outline only as they said (the rest is the app default: say so); if the paint already has numbers the tool asks replace vs alongside: put that to the buyer. Spec: check = read-only report (offer fixes; fix only when they ask); propose = read-only plan; apply ONLY after they agreed (buyer_agreed:true). Report the tool\'s own numbers (layers, parts, cm, spec M / R / C, on_part_pct, not_changed) and undo_with; spb_undo takes a kit back as one step.'] : []),
  'Flat paints (no layers): spb_look_at_paint, read where numbers / logos / stripes really are (no number drawn / the named thing is not there: say so), spb_mark_elements with boxes, check the image, then spb_refinish target "numbers".',
  'RENDER: ' + (CX2 ? 'after an authorized paint change is finished (never for advice, comparisons or questions)' : 'when a buyer request is finished') + ', call spb_render once so the car is rendered (say the seconds / files saved in your answer). ZONES: reuse empty zones and stack looks in one zone; for a new base over most of the car use spb_reset_zones (keep what the buyer still wants) + edit the catch-all, never one mute call per zone. spb_edit_zone: prefer zone_id or a unique zone_name (index + expect_name otherwise). Recolour a textured zone keeping its detail: hue, no color. spb_undo works on this paint\'s bridge history only. Describe a picture only if your client delivered it; otherwise use the measured numbers and say so.',
].join('\n');
// ONLINE-AI 2026-10-09: 3 sentences swapped (same length): the graphic-size sentence (the re-draw now uses the right parameter per kind, rotation is honest, undo counts changes), the shine-only sentence (carbon colour / brightness
// DOES show, texture size / shine does not), and the render sentence (files_saved 0). Kill switch SPB_ONLINE_AI_OFF=1 = the 1.4.1 text.
const INSTR_SWAPS = [
  ['RENDER: after an authorized paint change is finished (never for advice, comparisons or questions), call spb_render once so the car is rendered (say the seconds / files saved in your answer).',
   "RENDER: after the LAST change of a buyer request that changed the paint, call spb_render ONCE and say the seconds and files saved (files_saved 0 = NOTHING was written, say so). Not after every tool call of one request, and never for advice, complaints or questions that changed nothing. If the buyer asks to render / save / export / see it in iRacing, call it with buyer_asked_render:true."],
  ['RENDER: when a buyer request is finished, call spb_render once so the car is rendered (say the seconds / files saved in your answer).',
   "RENDER: after the LAST change of a buyer request that changed the paint, call spb_render ONCE and say the seconds and files saved (files_saved 0 = NOTHING was written, say so). Not after every tool call of one request, and never for advice, complaints or questions that changed nothing. If the buyer asks to render / save / export / see it in iRacing, call it with buyer_asked_render:true."],
  ['Sizes of a DRAWN graphic (checker squares, stripes, dots): spb_tweak scale re-draws it with one undo + one draw; never undo more steps than you made and never re-draw by hand.',
   'Sizes of a DRAWN graphic (checker squares, stripes, dots, waves): spb_tweak scale re-draws it with the right size parameter for that kind; rotation turns only stripes, speed lines and rays (for the rest the tool says so: relay it). Never re-draw by hand. spb_undo counts CHANGES (a tweak is one): "undo that" = steps 1. A tweak moves the whole look; for ONE part of it ("roof only") use spb_do on that part.'],
  ['Shine-only finishes (carbon, chrome, matte) have no visible size / brightness in the flat preview:',
   'Shine-only finishes (carbon, chrome, matte) have no visible texture size / shine in the flat preview (spec_only_note):'],
  ['(say the seconds / files saved in your answer)', '(say the seconds / files saved in your answer; files_saved 0 = NOTHING was written, say so)'],
  ['never for advice, comparisons or questions', 'never for advice, complaints, comparisons or questions'],
];
const INSTRUCTIONS = OAI ? INSTR_SWAPS.reduce((t, w) => t.split(w[0]).join(w[1]), INSTRUCTIONS_BASE) : INSTRUCTIONS_BASE;

const PROMPTS = [
  { name: 'design_livery', description: 'Design a paint scheme for the car open in Shokker Paint Booth.', arguments: [{ name: 'brief', description: 'What you want, e.g. "old-school Pepsi look, flat finish with chrome trim"', required: true }],
    text: (a) => 'Using Shokker Paint Booth, design this for my car: ' + (a.brief || 'a clean retro livery') + '\nFollow the Shokker workflow: spb_status, spb_request_parts if parts are missing, spb_design_recipes. If my brief leaves colours or layout open, offer me 2-3 options first; once I pick (or if the brief is exact), spb_apply_scheme with buyer_said = my words and confirm:true. Read measured / problems_found_by_app and tell me exactly what they say.' },
  { name: 'spec_only', description: 'Change only the shine / metal / roughness, never the paint colours.', arguments: [{ name: 'brief', description: 'e.g. "make the hood mirror chrome"', required: true }],
    text: (a) => 'Using Shokker Paint Booth, change ONLY the spec map (shine / metal / roughness), keep every paint colour exactly as it is: ' + (a.brief || '') + '\nUse a Foundation finish (base::f_chrome for mirror chrome, base::matte for matte, base::satin for satin ...) on the zones that already cover the part (edit them, leave color out so their colour stays; color "source" only on a bare template). Check spb_preview with spec=true afterwards and undo if any colour changed.' },
];

// ------------------------------------------------------------------ bridge call
function tokenFile() { return process.env.SPB_MCP_TOKEN_FILE || path.join(process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'), 'ShokkerPaintBooth', 'mcp', 'token.txt'); }
function readToken() { try { return fs.readFileSync(tokenFile(), 'utf8').trim(); } catch (e) { return ''; } }
let APP_CHAT_SCOPE = null;
// [S22 2026-10-13 beta Claude setup] AUTOLAUNCH (beta plan C: "Claude can open SPB"). When Shokker Paint Booth is not running, the first call that is refused (ECONNREFUSED: nothing was sent, so a retry is safe) starts the INSTALLED app,
// waits for /api/health (then for the app page to connect to the bridge) and retries ONCE. Windows + the production port 59876 only; a dev run with no installed exe behaves exactly as before (no launch, same error text).
// One spawn per cooldown window and never while a Shokker process is already running / starting (concurrent calls share one launch). KILL SWITCH: env SPB_AUTOLAUNCH_OFF=1.
// Test hooks: SPB_AUTOLAUNCH_EXE (a file to run instead of the installed app; .js files run with this node; allows launching on any port), SPB_AUTOLAUNCH_WAIT_S (default 55: Claude Desktop gives up on a tool call at about 60 s), SPB_AUTOLAUNCH_COOLDOWN_S (default 300).
const AUTOLAUNCH = !process.env.SPB_AUTOLAUNCH_OFF;
const AL = { inflight: null, child: null, spawnErr: null, launchedAt: 0, lastSpawn: 0, lastNote: '' };
function alSleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
function alProbe(p, ms) {          // raw GET on the configured port, never launches: resolves { status, json } or null
  return new Promise((resolve) => {
    let done = false; const fin = (v) => { if (!done) { done = true; resolve(v); } };
    const req = http.request({ host: '127.0.0.1', port: PORT, path: p, method: 'GET' }, (res) => {
      const ch = []; res.on('data', (c) => ch.push(c));
      res.on('end', () => { let j = null; try { j = JSON.parse(Buffer.concat(ch).toString('utf8')); } catch (e) { /* not json */ } fin({ status: res.statusCode, json: j }); });
    });
    req.on('error', () => fin(null)); req.setTimeout(ms || 2500, () => { req.destroy(); fin(null); }); req.end();
  });
}
function alFindExe() {          // the installed app's exe: installer folders first (package.json build: per-user NSIS, name shokker-paint-booth-v6, productName "Shokker Paint Booth V11"), then the uninstall registry entries (read-only reg query)
  const ov = process.env.SPB_AUTOLAUNCH_EXE; if (ov) return fs.existsSync(ov) ? ov : null;
  if (process.platform !== 'win32') return null;
  const minV = parseInt(VERSION, 10) || 0, found = [];          // an older generation (V8 ...) is never started by a newer connector
  const add = (f) => { const m = /^Shokker Paint Booth V(\d+)\.exe$/i.exec(path.basename(f || '')); if (!m || Number(m[1]) < minV) return; try { if (fs.statSync(f).isFile()) found.push({ v: Number(m[1]), f }); } catch (e) { /* gone */ } };          // exact name only: "Uninstall Shokker Paint Booth V11.exe" must never match
  const roots = [path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'Programs'), process.env.ProgramFiles, process.env['ProgramFiles(x86)']].filter(Boolean);
  for (const r of roots) {
    let dirs = []; try { dirs = fs.readdirSync(r); } catch (e) { continue; }
    for (const d of dirs) { if (!/shokker/i.test(d)) continue; let fl = []; try { fl = fs.readdirSync(path.join(r, d)); } catch (e) { continue; } fl.forEach((n) => add(path.join(r, d, n))); }
  }
  try {
    const cp = require('child_process');
    ['HKCU', 'HKLM'].forEach((hive) => {
      const o = cp.spawnSync('reg', ['query', hive + '\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall', '/s', '/f', 'Shokker Paint Booth V', '/d'], { encoding: 'utf8', timeout: 8000, windowsHide: true });
      String(o.stdout || '').split(/\r?\n/).forEach((ln) => { const m = /REG_(?:EXPAND_)?SZ\s+"?([A-Za-z]:\\[^"\r\n]*?Shokker Paint Booth V\d+\.exe)/i.exec(ln); if (m) add(m[1]); });
    });
  } catch (e) { /* no registry access: the folder search above is enough */ }
  found.sort((a, b) => b.v - a.v);
  return found.length ? found[0].f : null;
}
function alRunning(exe) {          // is a process with this exe name already running (= already starting up)?
  if (process.env.SPB_AUTOLAUNCH_EXE || process.platform !== 'win32') return false;
  try { const o = require('child_process').spawnSync('tasklist', ['/FI', 'IMAGENAME eq ' + path.basename(exe), '/NH', '/FO', 'CSV'], { encoding: 'utf8', timeout: 8000, windowsHide: true }); return String(o.stdout || '').toLowerCase().indexOf(path.basename(exe).toLowerCase()) >= 0; } catch (e) { return false; }
}
// [S22 2026-10-13 beta Claude setup] SURVIVAL: the app must outlive this extension process. Measured on this PC (Win11): a plain detached grandchild DIES when its parent's job object (kill-on-close) is closed, a child started through explorer.exe SURVIVES (its parent is the shell, outside the job).
// So on Windows the real exe is started THROUGH EXPLORER (breakaway; clean environment too), and if no Shokker process (or health) shows up within SPB_AUTOLAUNCH_VERIFY_S (8) it is started directly: detached + stdio ignore + unref. windowsHide is deliberately OFF for the app exe: SW_HIDE in STARTUPINFO hides a GUI app's first window (measured with charmap.exe); it stays ON only for the console child the tests start (.js).
// alPlan is pure (platform / env passed in) so mcp/test/autolaunch-plan.test.cjs can pin the spawn options; SPB_AUTOLAUNCH_DRYRUN=<file> (TEST ONLY) appends each planned spawn there instead of starting anything.
function alPlan(exe, platform, baseEnv, sysRoot) {
  const isJs = /\.(c|m)?js$/i.test(exe), env = Object.assign({}, baseEnv);
  if (isJs) return [{ kind: 'direct', command: process.execPath, args: [exe], options: { detached: true, stdio: 'ignore', windowsHide: true, env } }];
  delete env.ELECTRON_RUN_AS_NODE; delete env.NODE_OPTIONS;          // Claude Desktop runs extensions with ELECTRON_RUN_AS_NODE=1: SPB (an Electron app) must not inherit it or it starts as plain node and opens no window
  const direct = { kind: 'direct', command: exe, args: [], options: { detached: true, stdio: 'ignore', windowsHide: false, cwd: path.dirname(exe), env } };
  if (platform !== 'win32') return [direct];
  return [{ kind: 'breakaway', command: path.join(sysRoot || 'C:\\Windows', 'explorer.exe'), args: [exe], options: { detached: true, stdio: 'ignore', windowsHide: false, env } }, direct];
}
function alSpawn(a) {
  const dry = process.env.SPB_AUTOLAUNCH_DRYRUN;
  if (dry) { const o = Object.assign({}, a.options, { env: { ELECTRON_RUN_AS_NODE: a.options.env.ELECTRON_RUN_AS_NODE || null, NODE_OPTIONS: a.options.env.NODE_OPTIONS || null } }); fs.appendFileSync(dry, JSON.stringify({ kind: a.kind, command: a.command, args: a.args, options: o }) + '\n'); AL.child = null; return; }
  const child = require('child_process').spawn(a.command, a.args, a.options);
  if (a.kind === 'breakaway') { AL.child = null; child.on('error', () => { /* the direct start below covers it */ }); }          // the explorer client exits at once: it is not the app, so it is not tracked as "mine"
  else { AL.child = child; AL.spawnErr = null; child.on('error', (e) => { AL.spawnErr = e; }); }
  child.unref();
}
async function alRun() {
  const ov = process.env.SPB_AUTOLAUNCH_EXE;
  if (!ov && (process.platform !== 'win32' || PORT !== 59876)) return { up: false, note: '' };
  const waitMs = Math.max(3, Number(process.env.SPB_AUTOLAUNCH_WAIT_S) || 55) * 1000, coolMs = (Number(process.env.SPB_AUTOLAUNCH_COOLDOWN_S) || 300) * 1000, t0 = Date.now(), left = () => waitMs - (Date.now() - t0);
  const mine = !!(AL.child && AL.child.exitCode === null && !AL.spawnErr && Date.now() - AL.launchedAt < 10 * 60000);          // a copy THIS process started is still alive: only wait for it
  if (!mine) {
    const exe = alFindExe();
    if (!exe) return { up: false, note: '' };          // dev run / app not installed here: exactly as before
    if (!alRunning(exe)) {          // a Shokker process that is already running (still starting) is waited for, never started a second time
      if (Date.now() - AL.lastSpawn < coolMs) return { up: false, note: AL.lastNote };
      AL.lastSpawn = Date.now();
      try {
        const plan = alPlan(exe, process.platform, process.env, process.env.SystemRoot || process.env.windir);          // [S22 2026-10-13 beta Claude setup] see SURVIVAL above
        alSpawn(plan[0]); AL.launchedAt = Date.now(); log('Shokker Paint Booth was not running: started ' + exe + (plan[0].kind === 'breakaway' ? ' (through explorer, outside this process\'s job)' : ''));
        if (plan[0].kind === 'breakaway' && plan[1]) {          // nothing showed up (no process, no health) in the verify window: start it directly
          let seen = false; const vms = Math.max(1, Number(process.env.SPB_AUTOLAUNCH_VERIFY_S) || 8);
          for (let i = 0; i < vms && !seen; i++) { await alSleep(1000); seen = alRunning(exe) || !!(await alProbe('/api/health', 1000)); }
          if (!seen) { log('the explorer start showed no process after ' + vms + ' s: starting it directly'); alSpawn(plan[1]); }
        }
      }
      catch (e) { AL.lastNote = 'Shokker Paint Booth is installed but could not be started automatically. Open it from the Start menu or the desktop shortcut, then ask me again'; log('start failed: ' + (e && e.message)); return { up: false, note: AL.lastNote }; }
    }
  }
  let up = false;
  while (left() > 0 && !AL.spawnErr) { const h = await alProbe('/api/health', 2500); if (h && h.status === 200) { up = true; break; } await alSleep(1000); }
  if (!up) { AL.lastNote = AL.spawnErr ? 'Shokker Paint Booth is installed but could not be started automatically. Open it from the Start menu or the desktop shortcut, then ask me again' : 'I started Shokker Paint Booth for you, but it is still opening. Wait about a minute, then ask me again'; return { up: false, note: AL.lastNote }; }
  while (left() > 0) {          // the app page (Pro mode, AI panel) must connect to the bridge before a tool call can work; an OFF bridge or an old server without this route is not waited for
    const s = await alProbe('/api/mcp/status', 2500);
    if (!s || s.status !== 200 || !s.json || s.json.enabled === false || s.json.connected) break;
    await alSleep(1500);
  }
  return { up: true, note: '' };
}
function alEnsure() {
  if (!AUTOLAUNCH) return Promise.resolve({ up: false, note: '' });
  if (!AL.inflight) AL.inflight = alRun().catch((e) => { log('autolaunch: ' + (e && e.message)); return { up: false, note: '' }; }).then((r) => { AL.inflight = null; return r; });
  return AL.inflight;
}
function httpJson(method, p, body, timeoutMs, _retried) {
  return new Promise((resolve, reject) => {
    const data = body ? Buffer.from(JSON.stringify(body)) : null;
    const req = http.request({ host: '127.0.0.1', port: PORT, path: p, method, headers: Object.assign({ 'X-SPB-MCP-Token': readToken(), 'X-SPB-MCP-Client': String(CLIENT.name || '').slice(0, 60), ...(p === '/api/mcp/call' && APP_CHAT_SCOPE ? {'X-SPB-Document-Scope': APP_CHAT_SCOPE} : {}) }, data ? { 'Content-Type': 'application/json', 'Content-Length': data.length } : {}) }, (res) => {
      const chunks = []; res.on('data', (c) => chunks.push(c));
      res.on('end', () => { const txt = Buffer.concat(chunks).toString('utf8'); let j = null; try { j = JSON.parse(txt); } catch (e) { /* not json */ } resolve({ status: res.statusCode, json: j, text: txt }); });
    });
    req.on('error', (err) => {          // [S22 2026-10-13 beta Claude setup] app not running -> start the installed app once, wait, retry once (see AUTOLAUNCH above)
      if (!_retried && AUTOLAUNCH && err && err.code === 'ECONNREFUSED') {
        alEnsure().then((r) => { if (r.up) httpJson(method, p, body, timeoutMs, true).then(resolve, reject); else { if (r.note) err.message = r.note; reject(err); } }, () => reject(err));
      } else reject(err);
    });
    req.setTimeout(timeoutMs || 130000, () => { req.destroy(new Error('timeout')); });
    if (data) req.write(data);
    req.end();
  });
}
function timeoutFor(app) { return ({ render: 295, reset_zones: 90, apply_scheme: 170, preview: 90, add_zone: 150, edit_zone: 150, duplicate_zone: 150, edit_layer: 90, undo: 90, do: 170, check: 90, kit: 290 })[app] || 60; }
function friendly(r) {
  const j = r.json || {};
  if (r.status === 401) return 'Shokker could not verify this connection (pairing token). In Shokker Paint Booth open the AI panel settings, switch ON "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth", then restart your AI assistant (Claude or Codex).';
  if (r.status === 503 && j.error === 'disabled') return 'The AI bridge is switched OFF in Shokker Paint Booth. Ask the buyer to open the AI panel (settings gear) and switch on "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth".';
  if (r.status === 503 && j.error === 'app_not_ready' && AL.launchedAt && Date.now() - AL.launchedAt < 5 * 60000) return 'I started Shokker Paint Booth for you and it is still loading (it has to open Pro mode with the AI panel). Wait about 30 seconds, then ask me again.';          // [S22 2026-10-13 beta Claude setup]
  if (r.status === 503) return 'Shokker Paint Booth is not ready: open the app in Pro mode (the AI panel must be loaded) and try again.';
  if (r.status === 504) return j.message || 'Shokker did not answer in time.';
  return j.message || j.error || ('Shokker returned HTTP ' + r.status);
}
// a response over the size cap keeps VALID JSON: the longest lists are cut (60% at a time) and the cut is reported in _truncated
function fitJson(value, limit) {
  let text = JSON.stringify(value, null, 1) || '';
  if (text.length <= limit) return text;
  let clone; try { clone = JSON.parse(JSON.stringify(value)); } catch (e) { return text.slice(0, limit) + '\n...(truncated)'; }
  const cut = [];
  for (let guard = 0; guard < 80 && JSON.stringify(clone, null, 1).length > limit; guard++) {
    let best = null, bestLen = 0;
    (function walk(o, path) { if (Array.isArray(o)) { const l = JSON.stringify(o).length; if (o.length > 1 && l > bestLen) { best = { o, path }; bestLen = l; } o.forEach((x, i) => walk(x, path + '[' + i + ']')); } else if (o && typeof o === 'object') Object.keys(o).forEach(k => walk(o[k], path + '.' + k)); })(clone, '$');
    if (!best) break;
    const keep = Math.max(1, Math.floor(best.o.length * 0.6)); cut.push({ path: best.path, kept: keep, of: best.o.length }); best.o.length = keep;
  }
  const out = (clone && typeof clone === 'object' && !Array.isArray(clone)) ? Object.assign({}, clone, { _truncated: cut.slice(-6), _truncated_note: 'the response was too large: the lists above were cut to fit; ask again with narrower filters (or a page / exclude) to see the rest' }) : clone;
  let t2 = JSON.stringify(out, null, 1); if (t2.length > limit) t2 = t2.slice(0, limit) + '\n...(truncated)';
  return t2;
}
function toContent(res) {
  const content = []; let images = [];
  if (res && res.result && Array.isArray(res.result.images)) { images = res.result.images; res = Object.assign({}, res, { result: Object.assign({}, res.result, { images: undefined }) }); }
  const text = fitJson(res.result === undefined ? res : res.result, 24000);
  content.push({ type: 'text', text });
  for (const im of images) {
    const m = /^data:(image\/[a-z+.-]+);base64,(.*)$/i.exec(String(im.data_url || ''));
    if (m) { content.push({ type: 'text', text: 'image: ' + (im.name || 'picture') }); content.push({ type: 'image', data: m[2], mimeType: m[1] }); }
  }
  return content;
}
// ------------------------------------------------------------------ blind clients (WP8, 2026-10-03): ChatGPT connectors and some SDKs drop MCP image blocks
// SPB_MCP_BLIND_CLIENT = true | false | auto (default auto; or put the word in <token dir>/blind_client.txt). auto = the client's name (initialize clientInfo) is not in the allow-list.
const SIGHTED_CLIENTS = ['claude-code', 'claude-desktop', 'claude-ai', 'codex', 'local-agent-mode']; // claude-ai is what Claude Desktop / claude.ai report; codex matches codex-mcp-client etc. (prefix match); local-agent-mode = Claude Desktop Code-tab agent sessions (seen 2026-10-07, image-capable)
const BLIND_TOOLS = new Set(['spb_look_at_paint', 'spb_mark_elements', 'spb_preview']);
let CLIENT = { name: '', version: '' };
function blindMode() {
  let v = String(process.env.SPB_MCP_BLIND_CLIENT || '').trim().toLowerCase();
  if (!v) { try { v = fs.readFileSync(path.join(path.dirname(tokenFile()), 'blind_client.txt'), 'utf8').trim().toLowerCase(); } catch (e) { v = ''; } }
  if (v === 'true' || v === '1' || v === 'yes' || v === 'on') return 'true';
  if (v === 'false' || v === '0' || v === 'no' || v === 'off') return 'false';
  return 'auto';
}
function isBlindClient() {
  const m = blindMode(); if (m === 'true') return true; if (m === 'false') return false;
  const n = String(CLIENT.name || '').toLowerCase();
  return !SIGHTED_CLIENTS.some((a) => n === a || n.startsWith(a));
}
const UNVERIFIED = 'UNVERIFIED: this client cannot see the paint; confirm in the app. Do not claim you saw the picture: say what the text below measured and ask the buyer to check Shokker Paint Booth.';
// the text stand-in for the pictures: describe_paint summary + the app’s own finder guess (when the result carries one)
async function blindText(name, result) {
  const part = { notice: UNVERIFIED, tool: name, client: CLIENT.name || '(none sent)' }; // orchestrator 2026-10-07: name the client so a wrongly-blind sighted client is diagnosable (put its name in SIGHTED_CLIENTS)
  try {
    const r = await httpJson('POST', '/api/mcp/call', { tool: 'describe_paint', args: {}, timeout: 20 }, 35000);
    if (r.json && r.json.ok !== false && r.json.result !== undefined) part.describe_paint_summary = r.json.result;
  } catch (e) { part.describe_paint_summary = 'unavailable (' + (e && e.message) + ')'; }
  if (result && typeof result === 'object') {
    if (result.app_guess !== undefined) part.app_finder_guess = result.app_guess;
    else if (result.candidates !== undefined || result.kind !== undefined) part.app_finder_guess = { kind: result.kind, candidates: result.candidates, maybe_more: result.maybe_more };
    if (result.colour_shares_percent !== undefined) part.colour_shares_percent = result.colour_shares_percent;
  }
  return fitJson(part, 6000);
}
// ------------------------------------------------------------------ AITER 2026-10-08: iterate on ONE zone (spb_tweak), working-zone tracking, unknown-part honesty
let WORKING = null;          // { id, name } of the zone the last successful write created / changed through this bridge
const ROTS = {};             // zone id -> pattern rotation (the app's zone listing does not show it)
const WRITE_APPS = ['reset_zones', 'do', 'edit_zone', 'refinish', 'add_zone', 'duplicate_zone', 'add_graphic', 'apply_scheme'];
async function bridgeCall(app, args, secs) {
  if (WRITE_APPS.indexOf(app) !== -1 || app === 'edit_layer' || app === 'undo' ||
      (app === 'kit' && !/^(?:check|propose)$/i.test(String((args || {}).action || 'place')))) {
    const prepared = await require('../chatgpt/source-bound-execution.cjs').prepare(app, args || {}, () =>
      httpJson('POST', '/api/mcp/call', { tool: 'get_state', args: {}, timeout: 30 }, 45000));
    if (prepared.blocked) return {status:200,json:{ok:true,result:prepared.blocked}};
    args = prepared.args;
  }
  return httpJson('POST', '/api/mcp/call', { tool: app, args: args || {}, timeout: secs || 60 }, ((secs || 60) + 15) * 1000);
}
async function zonesNow() { try { const r = await bridgeCall('zones', {}, 30); const z = r.json && r.json.result && r.json.result.zones; return Array.isArray(z) ? z : null; } catch (e) { return null; } }
function zkey(z) { return String(z.id || z.name) + '|' + String(z.look || '') + '|' + String(z.covers || '') + '|' + (z.muted ? 'M' : ''); }
function pickWorking(before, after) {
  if (!before || !after) return null; const B = new Map(before.map((z) => [String(z.id || z.name), zkey(z)]));
  const ch = after.filter((z) => !z.muted && B.get(String(z.id || z.name)) !== zkey(z));
  return ch.length ? ch[0] : null;          // index 0 = top of the stack = the zone the buyer sees on that area
}
function lookNum(look, word) { const m = new RegExp('(?:^|\\| )' + word + ' (-?[0-9.]+)').exec(String(look || '')); return m ? Number(m[1]) : null; }
function lookPattern(look) { const m = /(?:^|\| )pattern ([^\s(]+) \(/.exec(String(look || '')); return m ? m[1] : null; }
function clampN(v, a, b) { return Math.max(a, Math.min(b, v)); }

// W1MCP 2026-10-09 (lane W1-MCP, eval/w1mcp/REPORT.md): two spb_tweak holes found by the 84-convo Sonnet run. (a) "make the squares smaller" on a DRAWN graphic (checker / dots / stripes): scale only crushes a texture the
// graphic zone does not have, so nothing changed and Claude then undid TWO steps and re-drew by hand (M-T04). We remember the add_graphic call that made the working zone; a scale tweak on it undoes that one write (only when it is
// still the latest write) and re-draws it with n scaled. (b) "a bit more orange": the planner turned the hue request into a +20 saturation nudge, nothing visible changed (M-T36): for a solid-colour zone the hue is rotated here
// (toward the named colour when given) and applied with edit_zone color. Kill switches: SPB_MCP_NOGFXSCALE=1, SPB_MCP_NOHUEFIX=1.
let WSEQ = 0; const GFX = {};
const HUES = { red: 0, orange: 24, amber: 38, gold: 45, yellow: 55, lime: 85, green: 120, teal: 175, cyan: 185, aqua: 185, blue: 220, navy: 228, purple: 275, violet: 270, magenta: 300, pink: 330, rose: 340 };
function hex2hsl(h) { const r = parseInt(h.slice(1, 3), 16) / 255, g = parseInt(h.slice(3, 5), 16) / 255, b = parseInt(h.slice(5, 7), 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2; let hh = 0, ss = 0; if (mx !== mn) { const d = mx - mn; ss = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn); hh = mx === r ? (g - b) / d + (g < b ? 6 : 0) : (mx === g ? (b - r) / d + 2 : (r - g) / d + 4); hh *= 60; } return [hh, ss, l]; }
function hsl2hex(hh, ss, l) { hh = ((hh % 360) + 360) % 360; const c = (1 - Math.abs(2 * l - 1)) * ss, x = c * (1 - Math.abs(((hh / 60) % 2) - 1)), m = l - c / 2; let r = 0, g = 0, b = 0; if (hh < 60) { r = c; g = x; } else if (hh < 120) { r = x; g = c; } else if (hh < 180) { g = c; b = x; } else if (hh < 240) { g = x; b = c; } else if (hh < 300) { r = x; b = c; } else { r = c; b = x; } const f = (v) => ('0' + Math.round((v + m) * 255).toString(16)).slice(-2); return '#' + f(r) + f(g) + f(b); }
function nudgeHue(hex, up, towardWord, amtWord) {
  const [h, s, l] = hex2hsl(hex), step = amtWord === 'lot' ? 60 : (amtWord === 'little' ? 22 : 38); let dir = up ? 1 : -1;
  const tw = String(towardWord || '').toLowerCase().trim(), th = /^#[0-9a-f]{6}$/i.test(tw) ? hex2hsl(tw)[0] : HUES[tw];
  // ONLINE-AI 2026-10-09 (M-T36: dark red #951111 "a bit more orange" -> #954111 = BROWN): a dark colour rotated into the orange / yellow range goes brown. Move less, keep it saturated and a touch lighter.
  const dark = (hh, ll) => OAI && ll < 0.42 && ((hh % 360) + 360) % 360 >= 12 && ((hh % 360) + 360) % 360 <= 80;
  if (th != null) { let d = ((th - h + 540) % 360) - 180; dir = d >= 0 ? 1 : -1; let mv = Math.min(Math.abs(d), step); const nh0 = h + dir * mv; if (dark(nh0, l)) { mv = Math.min(mv, amtWord === 'lot' ? 24 : 14); return hsl2hex(h + dir * mv, Math.max(s, 0.85), Math.min(l + 0.05, 0.45)); } return hsl2hex(nh0, Math.max(s, 0.35), l); }
  if (dark(h + dir * step, l)) return hsl2hex(h + dir * Math.min(step, amtWord === 'lot' ? 24 : 14), Math.max(s, 0.85), Math.min(l + 0.05, 0.45));
  return hsl2hex(h + dir * step, Math.max(s, 0.35), l);
}

// ONLINE-AI 2026-10-09 (CAUSES.md C1/C2/C3): spb_tweak on DRAWN graphics. The W1MCP re-draw passed `n` for every kind, but only rings / rays / chevrons / speed_lines use n as a COUNT: a checker has `size`, dots `spacing` + `size`,
// stripes `w` + `gap`, waves `w` / `spacing` / `amp` / `wavelength`, flames `scale` (M-T04: "make the squares smaller" re-drew an identical checker and said "27 squares across"). Rotation of a kind without an angle used to
// edit a zone rotation that does nothing and report success. GFX_SIZE rows: [param, default, min, max, mode] (mode inv = a count: smaller means MORE).
function r4(v) { return Math.round(v * 10000) / 10000; }
const GFX_SIZE = {
  checker: [['size', 0.07, 0.012, 0.5]], dots: [['spacing', 0.07, 0.015, 0.4], ['size', 0.055, 0.01, 0.4]],
  stripes: [['w', 0.06, 0.004, 0.5], ['gap', 0.08, 0.004, 0.6]], waves: [['w', 0.04, 0.004, 0.3], ['spacing', 0.1, 0.01, 0.6], ['amp', 0.05, 0.005, 0.4], ['wavelength', 0.25, 0.03, 1.5]],
  chevrons: [['w', 0.03, 0.004, 0.2], ['depth', 0.4, 0.03, 1], ['n', 6, 1, 60, 'inv']], speed_lines: [['wmin', 0.006, 0.002, 0.1], ['wmax', 0.022, 0.004, 0.2], ['lenmin', 0.12, 0.02, 1], ['lenmax', 0.5, 0.05, 1]],
  rings: [['r0', 0.12, 0.02, 1.2], ['r1', 0.9, 0.05, 1.5], ['w0', 0.018, 0.003, 0.2], ['w1', 0.04, 0.005, 0.3]], rays: [['n', 18, 2, 120, 'inv']], lightning: [['w', 0.035, 0.005, 0.3], ['jag', 0.12, 0.01, 0.6]],
  flames: [['scale', 1, 0.5, 2]],
};
function scaleGraphic(a0, f) {          // f < 1 = smaller; returns { args, changed, moved } or null when this kind has no size
  const k = String(a0.kind || '').toLowerCase(), spec = GFX_SIZE[k]; if (!spec && k !== 'strokes') return null;
  const a = Object.assign({}, a0), changed = {}; let moved = false;
  const put = (key, def, lo, hi, mode) => { const cur = a[key] != null ? Number(a[key]) : def; if (!isFinite(cur)) return; let v = mode === 'inv' ? cur / f : cur * f; v = Math.max(lo, Math.min(hi, v)); v = (mode === 'inv') ? Math.round(v) : r4(v); if (Math.abs(v - cur) > 1e-9) moved = true; a[key] = v; changed[key] = v; };
  if (k === 'strokes') { if (Array.isArray(a.items)) { a.items = a.items.map((it) => Object.assign({}, it, { w0: r4(Math.max(0.003, (Number(it.w0) || 0.02) * f)), w1: r4(Math.max(0.003, (Number(it.w1) || 0.02) * f)) })); moved = true; changed.items = 'widths x' + r4(f); } }
  else (spec || []).forEach((s) => {
    if (k === 'stripes' && s[0] === 'w' && a.stroke_px != null) return put('stroke_px', 6, 1, 400);
    if (k === 'stripes' && s[0] === 'gap' && a.gap_px != null) return put('gap_px', 6, 0, 400);
    put(s[0], s[1], s[2], s[3], s[4]);
  });
  if (k === 'rings' && Array.isArray(a.radii)) { a.radii = a.radii.map((x) => r4(Math.max(0.02, Math.min(1.5, Number(x) * f)))); if (Array.isArray(a.widths)) a.widths = a.widths.map((x) => r4(Math.max(0.003, Number(x) * f))); moved = true; changed.radii = 'x' + r4(f); }
  return { args: a, changed, moved };
}
function rotateGraphic(a0, deg) {          // returns { args, changed } or null when this kind cannot rotate
  const k = String(a0.kind || '').toLowerCase(), a = Object.assign({}, a0);
  if (k === 'stripes' || k === 'speed_lines') { a.angle = (((Number(a.angle) || 0) + deg) % 360 + 360) % 360; return { args: a, changed: { angle: a.angle } }; }
  if (k === 'rays') { a.from = (Number(a.from) || 0) + deg; a.to = (a.to != null ? Number(a.to) : 360) + deg; return { args: a, changed: { from: a.from, to: a.to } }; }
  return null;
}
function finishTok(z) { return String((z && z.look) || '').split(' | ')[0]; }
// the working zone of a write = the zone that SHOWS most when the write made several zones with the same finish (carbon on a part makes one zone per zone it covers + a colour-source zone: the old top-of-stack pick was a 0.2% sliver),
// and the siblings = all of them, so one tweak moves the whole look.
function pickWorkingOAI(before, after) {
  if (!before || !after) return null; const B = new Map(before.map((z) => [String(z.id || z.name), zkey(z)]));
  const ch = after.filter((z) => !z.muted && B.get(String(z.id || z.name)) !== zkey(z)); if (!ch.length) return null;
  const fresh = ch.filter((z) => !B.has(String(z.id || z.name))); let wz = ch[0];
  if (fresh.length > 1 && fresh.every((z) => finishTok(z) === finishTok(fresh[0]))) { wz = fresh[0]; fresh.forEach((z) => { if ((Number(z.visible_pct) || 0) > (Number(wz.visible_pct) || 0)) wz = z; }); }
  const pool = fresh.length ? fresh : ch, ft = finishTok(wz);
  return { wz, sibs: pool.filter((z) => finishTok(z) === ft).map((z) => ({ id: z.id, name: z.name })) };
}
const SPEC_ONLY_RE = /^(f_carbon|f_chrome|f_satin_chrome|f_dark_chrome|f_metallic|f_pearl|f_brushed|f_matte|f_satin|matte|satin|chrome|carbon)/i;
function withFields(res, fields) {          // add keys to the JSON text of a tool result (never breaks it)
  try { const c = res && res.content; if (!c) return res; for (const x of c) { if (x.type === 'text') { const j = JSON.parse(x.text); if (j && typeof j === 'object' && !Array.isArray(j)) { Object.assign(j, fields); x.text = JSON.stringify(j); } return res; } } } catch (e) { /* leave as is */ }
  return res;
}
function tweakAmounts(args) {
  const amt = args.amount, w = (typeof amt === 'string' && /lot|much|way|big/.test(amt)) ? 'lot' : ((typeof amt === 'string' && /bit|little|touch|slight/.test(amt)) ? 'little' : undefined);
  return { amt, amtWord: w, f: w === 'lot' ? 0.45 : (w === 'little' ? 0.8 : 0.65) };
}
// ONLINE-AI 2026-10-09: spb_undo counts LOGICAL changes (what the buyer sees), not page-history steps. A 2-colour checker, a body-first scheme and a multi-zone scale are 2+ page writes but ONE change; a graphic
// "smaller / bigger" tweak is an undo + a re-draw, so undoing it must put the PREVIOUS size back (page undo alone would delete the graphic). HIST = one entry per change made through this bridge: { n: page steps it took,
// restore?: how to bring the previous drawing back }. Anything made outside this bridge counts 1 step each (as before).
const HIST = [];
// ONLINE-AI 2026-10-09 (A-0234 t2: the buyer COMPLAINED "the RED I asked for, not pink"; the model looked, then called spb_render: 44 s and, with the iRacing folder set, the buyer's files overwritten for a turn that changed nothing).
// DIRTY = this bridge changed the paint since the last render. spb_render with DIRTY false refuses unless the buyer asked to render / save / export (buyer_asked_render:true).
const RENDER_NEXT = "If this was the LAST change of the buyer's request, call spb_render once now and tell the buyer the seconds and files saved (not after every step of one request).";          // ONLINE-AI 2026-10-09 (2): p7b run: with the instruction alone the model rendered in 1 of 8 change turns (baseline CX2: 1 of 104); the result of a write now carries the reminder
let DIRTY = false, RENDERED_PENDING = false;          // RENDERED_PENDING: a render succeeded and no write happened since
const AFTER_RENDER_NOTE = "This is the first change after a render and this app build compares it with the rendered picture (an older page without the P7 fix), so outside_px, decal_px and any spill / numbers-and-logos-changed finding are inflated by about 100k px of nothing. Do NOT tell the buyer about spill or logo damage from these numbers and do not undo or stop for them; trust inside_px and a look at the paint (spb_preview / spb_look_at_paint).";
function histPush(n) { DIRTY = true; HIST.push({ n: n || 1 }); if (HIST.length > 80) HIST.shift(); }
async function oaiUndo(args) {
  const steps = Math.max(1, Math.min(30, Math.round(Number(args && args.steps) || 1)));
  // Check every possible graphic restore BEFORE changing history or undoing pixels.
  for (const e of HIST.slice(-steps)) if (e && e.restore) {
    const blocked = await unknownPartRefusal('add_graphic', e.restore.args || {});
    if (blocked) return {content:[{type:'text',text:JSON.stringify(blocked)}]};
  }
  DIRTY = true;
  let pending = 0, k = steps, last = null; const notes = [];
  const flush = async () => { if (pending > 0) { last = await bridgeCall('undo', { steps: pending }, timeoutFor('undo')); pending = 0; } };
  let restored = false;
  while (k > 0) {
    const e = HIST.pop(); k--;
    if (!e) { pending += 1; continue; }
    if (e.kit) { await flush(); const ku = await bridgeCall('kit', { action: 'undo' }, 90); if (ku.json && ku.json.ok !== false && ku.json.result && ku.json.result.changed !== false) { last = ku; notes.push('the ' + (e.label || 'kit') + ' is taken back (one step)'); } else notes.push('the ' + (e.label || 'kit') + ' could NOT be undone: ' + String((ku.json && ku.json.result && ku.json.result.note) || (ku.json && ku.json.error) || 'refused')); continue; }          // OA2: a kit change is one step of the kit undo
    if (!e.restore) { pending += e.n; continue; }
    let run = e; while (k > 0 && HIST.length && HIST[HIST.length - 1].restore) { run = HIST.pop(); k--; }
    if (k > 0) continue;          // the entry below is the graphic's own draw and is removed next: no need to bring an older size back first
    await flush(); if (last && (!last.json || last.json.ok === false)) break;
    const u = await bridgeCall('undo', { steps: run.restore.nW, _spb_expected_source: run.restore.args._spb_expected_source }, timeoutFor('undo')); last = u; if (!u.json || u.json.ok === false) break;
    const zPre = await zonesNow() || [], d = await drawGfx(Object.assign({}, run.restore.args), run.restore.colour2);
    if (d.ok) { await trackGfx(zPre, run.restore.args, run.restore.colour2); last = d.r; restored = true; notes.push('the ' + String(run.restore.args.kind) + ' is back at its previous size'); } else notes.push('the previous size could not be re-drawn: the graphic is removed, draw it again if wanted');
  }
  await flush();
  if (!last || !last.json || last.status >= 400 || last.json.ok === false) return { isError: true, content: [{ type: 'text', text: last ? friendly(last) : (notes.length ? notes.join('; ') : 'nothing to undo') }] };          // OA2: say why a kit could not be undone

  if (!restored) WORKING = null;
  const R = last.json.result && typeof last.json.result === 'object' && !Array.isArray(last.json.result) ? last.json.result : { result: last.json.result };
  return { content: toContent({ result: Object.assign({}, R, { undone_changes: steps, restored: notes.length ? notes : undefined }) }) };
}
// a CHECKER draws ONE colour (colours[0]); the second colour of a flag is the complementary squares = the same checker one row up (v0 - size), in its own zone. So a 2-colour checker is two add_graphic writes (colour2).

// ------------------------------------------------------------------ OA2 2026-10-10: spb_kit (Sponsor Kit / Number Kit / Spec Doctor / Spec Autopilot of the page, js/spb-online-kits.js)
// Restraint lives here as well as in the page: a write needs the buyer's words; a sponsor needs parts the words name; a number needs the digits and a place in the words; spec apply/fix need a message that is not the one that asked for the report.
let KIT_SAID = { check: '', propose: '' };
const PART_WORDS = /\b(door|doors|hood|bonnet|trunk|deck|tailgate|roof|quarter|quarters|tv|rail|rails|side|sides|fender|fenders|panel|panels|everywhere|all over)\b/i;
function kitText(o) { return { content: [{ type: 'text', text: JSON.stringify(o) }] }; }
function normSaid(t) { return String(t || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
function readLogoFile(p) {
  const ext = path.extname(String(p || '')).toLowerCase(), types = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.gif': 'image/gif' };
  if (!types[ext]) return { error: 'logo_file must be a PNG, JPG, SVG, WEBP or GIF picture (got "' + ext + '").' };
  let st; try { st = fs.statSync(p); } catch (e) { return { error: 'That logo file does not exist: ' + p }; }
  if (!st.isFile() || st.size > 8 * 1024 * 1024) return { error: 'logo_file must be a picture file under 8 MB.' };
  return { data: 'data:' + types[ext] + ';base64,' + fs.readFileSync(p).toString('base64'), name: path.basename(p) };
}
async function kitTool(a0) {
  let a = Object.assign({}, a0);
  const kit = String(a.kit || '').toLowerCase(), act = String(a.action || (kit === 'spec' ? '' : 'place')).toLowerCase();
  if (!['sponsor', 'number', 'spec'].includes(kit) && act !== 'undo') return { isError: true, content: [{ type: 'text', text: 'kit must be sponsor, number or spec.' }] };
  const said = String(a.buyer_said || '').trim(), n = normSaid(said);
  const write = act === 'place' || act === 'remove' || act === 'fix' || act === 'apply';
  if (write && said.length < 3) return kitText({ changed: false, refused: true, note: 'spb_kit ' + act + ' needs buyer_said = the buyer\'s words, verbatim. Nothing was changed.' });
  if (kit === 'sponsor' && act === 'place') {
    if (!PART_WORDS.test(said)) return kitText({ changed: false, ask: 'Which parts should the logo go on (left door, right door, hood, trunk, rear quarters, TV panels, roof rails)? The buyer\'s words name none, so nothing was placed.' });
    if (a.logo_file) { const f = readLogoFile(String(a.logo_file)); if (f.error) return kitText({ changed: false, refused: true, note: f.error }); a.logo_data = f.data; a.logo_name = f.name; delete a.logo_file; }
  }
  if (kit === 'number' && act === 'place') {
    const digits = String(a.number || '').replace(/[^A-Za-z0-9]/g, '');
    if (!digits) return kitText({ changed: false, ask: 'What number (1 to 4 digits or letters)? Nothing was placed.' });
    if (!new RegExp('(^|[^a-z0-9])' + digits.toLowerCase() + '([^a-z0-9]|$)').test(said.toLowerCase()) && !/\b(number|numbers)\b/i.test(said)) return kitText({ changed: false, ask: 'The buyer\'s words do not give the number ' + digits + '. Ask which number they want. Nothing was placed.' });
    if (!/\b(door|doors|roof|side|sides|left|right|both|all)\b/i.test(said)) return kitText({ changed: false, ask: 'Where should the number go: left door, right door, roof, or all three? Nothing was placed.' });
  }
  if (kit === 'spec' && act === 'apply') {
    if (a.buyer_agreed !== true) return kitText({ changed: false, ask: 'Apply only after the buyer has seen the proposal and agreed. Show spb_kit spec propose first, then call apply with buyer_agreed:true. Nothing changed.' });
    if (KIT_SAID.propose && n === KIT_SAID.propose) return kitText({ changed: false, ask: 'That is the same message that asked for the proposal, not an agreement to apply it. Read the proposal to the buyer, wait for their yes, then apply. Nothing changed.' });
  }
  if (kit === 'spec' && act === 'fix' && KIT_SAID.check && n === KIT_SAID.check && !/\b(fix|repair|correct|sort|clean|apply)\b/.test(n)) return kitText({ changed: false, ask: 'The buyer only asked for a check. Tell them what the Doctor found and offer the fixes; apply one only when they ask. Nothing changed.' });
  if (act === 'check' && kit === 'spec') KIT_SAID.check = n;
  if (act === 'propose' && kit === 'spec') KIT_SAID.propose = n;
  let r;
  try { r = await bridgeCall('kit', a, timeoutFor('kit')); } catch (e) { return { isError: true, content: [{ type: 'text', text: 'Could not reach Shokker Paint Booth on 127.0.0.1:' + PORT + ' (' + (e && e.message) + '). Is the app running?' }] }; }
  if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(r) }] };
  const R = r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result) ? r.json.result : null;
  if (!R) return { content: toContent(r.json) };
  const extra = {};
  if (act === 'undo') { if (R.changed) { for (let i = HIST.length - 1; i >= 0; i--) if (HIST[i].kit) { HIST.splice(i, 1); break; } DIRTY = true; } }
  else if (R.changed === true && write) { DIRTY = true; HIST.push({ n: 0, kit: true, label: kit === 'spec' ? (act === 'fix' ? 'spec fix' : 'auto spec') : kit + ' kit' }); if (HIST.length > 80) HIST.shift(); extra.render_next = RENDER_NEXT; }
  return { content: toContent({ result: Object.assign({}, R, extra) }) };
}
function checkerSecond(a, c) { return Object.assign({}, a, { colours: [c], v0: r4((Number(a.v0) || 0) - (Number(a.size) || 0.07)) }); }
function gfxGood(r) { const rr = r && r.json && r.json.result; return !!(r && r.json && r.status < 400 && r.json.ok !== false && !(rr && typeof rr === 'object' && (rr.ask || rr.ask_back || rr.changed === false))); }
async function drawGfx(a, colour2) {          // one graphic (+ its second colour); on a failed second colour the first is taken back
  const r = await bridgeCall('add_graphic', a, timeoutFor('add_graphic')); if (!gfxGood(r)) return { ok: false, r };
  if (colour2) {
    const r2 = await bridgeCall('add_graphic', checkerSecond(a, colour2), timeoutFor('add_graphic')); if (!gfxGood(r2)) { await bridgeCall('undo', { steps: 1 }, timeoutFor('undo')); return { ok: false, r: r2 }; }
    const R1 = r.json.result, R2 = r2.json.result;
    if (R1 && R2 && typeof R1 === 'object' && typeof R2 === 'object' && !Array.isArray(R1) && !Array.isArray(R2)) r.json.result = Object.assign({}, R1, { applied: (R1.applied || []).concat(R2.applied || []), images: R2.images || R1.images, measured: R2.measured || R1.measured });
  }
  return { ok: true, r };
}
async function trackGfx(prevZones, args, colour2) {          // remember the add_graphic that made the newest zone(s) (spb_tweak re-draws from it)
  WSEQ++; const zs2 = await zonesNow(); const fresh = zs2 ? zs2.filter((q) => !q.muted && prevZones.every((o) => String(o.id) !== String(q.id))) : [];
  fresh.forEach((q) => { GFX[String(q.id)] = { seq: WSEQ, args, colour2: colour2 || undefined }; });
  if (fresh.length) { const top = fresh.reduce((b, q) => ((Number(q.visible_pct) || 0) > (Number(b.visible_pct) || 0) ? q : b), fresh[0]); WORKING = { id: top.id, name: top.name, sibs: fresh.map((q) => ({ id: q.id, name: q.name })) }; return top; }
  return null;
}
async function oaiGraphicTweak(args, z, gx, ch, up, zs) {
  const said = String(args.buyer_said || '').trim(), { amt, amtWord, f } = tweakAmounts(args), kind = String(gx.args.kind || '').toLowerCase();
  const stop = (rule) => ({ content: [{ type: 'text', text: JSON.stringify({ changed: false, tweaked_zone: z.name, rule }) }] });
  // A refusal must precede the undo used to re-draw a graphic.
  const blocked = await unknownPartRefusal('add_graphic', gx.args || {});
  if (blocked) return {content:[{type:'text',text:JSON.stringify(blocked)}]};
  if (gx.seq !== WSEQ) return stop('NOTHING changed. This zone is a drawn ' + kind + ' graphic and other changes were made after it, so it cannot be re-drawn without losing them. Tell the buyer, and offer to draw it again.');
  let m, label;
  if (ch === 'scale') { m = scaleGraphic(gx.args, up ? 1 / f : f); label = (up ? 'bigger' : 'smaller'); if (m && !m.moved) return stop('NOTHING changed: this ' + kind + ' is already at the ' + (up ? 'biggest' : 'smallest') + ' size the app allows. Tell the buyer; offer the other direction.'); }
  else { const deg = typeof amt === 'number' ? Math.abs(amt) : (amtWord === 'lot' ? 90 : (amtWord === 'little' ? 15 : 30)); m = rotateGraphic(gx.args, up ? deg : -deg); label = 'rotated ' + (up ? '+' : '-') + deg + ' degrees'; if (!m) return stop('NOTHING changed. A drawn ' + kind + ' cannot be rotated (it has no angle). Tell the buyer; offer to draw it again as stripes or speed_lines at an angle, or to move / resize it.'); }
  if (!m) return stop('NOTHING changed. This graphic kind (' + kind + ') has no size parameter to change. Tell the buyer; offer to draw it again with new numbers.');
  const nW = gx.colour2 ? 2 : 1;          // writes that made this graphic (a 2-colour checker = 2)
  const u = await bridgeCall('undo', { steps: nW, _spb_expected_source: gx.args._spb_expected_source }, timeoutFor('undo')); if (!u.json || u.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(u) }] };
  const a2 = Object.assign({}, m.args, { buyer_said: gx.args.buyer_said || said });          // the words that passed the gate when it was first drawn (a tweak phrase like "it is too big" would get ask_back and leave the graphic undone)
  const d = await drawGfx(a2, gx.colour2), r = d.r, rr = r.json && r.json.result;
  if (!d.ok) {          // put the buyer's graphic back: the undo above removed it
    const d0 = await drawGfx(Object.assign({}, gx.args), gx.colour2);
    if (d0.ok) await trackGfx(zs, gx.args, gx.colour2);
    return { isError: true, content: [{ type: 'text', text: 'The ' + kind + ' could not be re-drawn (' + friendly(r).slice(0, 200) + '). ' + (d0.ok ? 'The original graphic was put back: NOTHING changed.' : 'WARNING: the original graphic could not be put back: call spb_undo once and draw it again.') }] };
  }
  const nz = await trackGfx(zs, a2, gx.colour2); HIST.push({ n: 0, restore: { args: gx.args, colour2: gx.colour2, nW } });
  const out = { tweaked_zone: nz ? nz.name : z.name, zone_id: nz ? nz.id : z.id, change: ch, direction: up ? 'up' : 'down', applied_as: kind + ' graphic re-drawn ' + label + ' (' + nW + ' undo + ' + nW + ' draw)', graphic_params_changed: m.changed, undo_with: 'spb_undo steps:1 puts the previous size back' };
  const res0 = rr && typeof rr === 'object' && !Array.isArray(rr) ? Object.assign({}, out, rr) : Object.assign({}, out, { result: rr });
  res0.honesty = 'The graphic was re-drawn (one undo + one draw). Report only what measured shows.';
  return { content: toContent({ result: res0 }) };
}
async function oaiFinishScale(args, z, zs) {          // scale of a finish-only zone (carbon / chrome / matte...): DIRECT edit_zone scale on the sibling zones of that write that show something (the planner "lifted" the colour-source zone above the recolours and EXPOSED the base colour)
  const said = String(args.buyer_said || '').trim(), up = String(args.direction || 'down').toLowerCase() === 'up', { f } = tweakAmounts(args), fac = up ? 1 / f : f;
  const sibIds = (WORKING && WORKING.sibs && WORKING.sibs.some((s) => String(s.id) === String(z.id))) ? WORKING.sibs.map((s) => String(s.id)) : [String(z.id)];
  const sibs = zs.filter((q) => sibIds.indexOf(String(q.id)) !== -1 && !q.muted), showing = sibs.filter((q) => (Number(q.visible_pct) || 0) >= 0.05), targets = showing.slice(0, 6);
  if (!targets.length) return { content: [{ type: 'text', text: JSON.stringify({ changed: false, tweaked_zone: z.name, rule: 'NOTHING changed: this zone shows 0% of the car (other zones cover it), so a scale tweak on it would only re-stack the zones and could expose the base colour. Tell the buyer; use spb_get_zones to find the zone that shows (visible_pct), or ask which look they mean.' }) }] };
  const done = [], limits = []; let last = null, best = null, errText = null, allNothing = true;
  for (const t of targets) {
    const cur = lookNum(t.look, 'scale') == null ? 1 : lookNum(t.look, 'scale'), nv = r4(clampN(cur * fac, 0.1, 4));
    if (Math.abs(nv - cur) < 0.005) { limits.push(t.name); continue; }
    const r = await bridgeCall('edit_zone', { zone_id: String(t.id), buyer_said: said, scale: nv }, timeoutFor('edit_zone'));
    if (!r.json || r.status >= 400 || r.json.ok === false) { errText = friendly(r); break; }
    WSEQ++; done.push({ zone: t.name, scale_from: cur, scale_to: nv }); last = r.json.result;
    const mm = last && last.measured; if (mm && mm.nothing_visible !== true) allNothing = false; if (mm && (!best || (mm.changed_px || 0) > (best.measured.changed_px || 0))) best = last;
  }
  if (!done.length) return errText ? { isError: true, content: [{ type: 'text', text: errText }] } : { content: [{ type: 'text', text: JSON.stringify({ changed: false, rule: 'NOTHING changed: the texture scale is already at its ' + (up ? 'biggest' : 'smallest') + ' (' + limits.join(', ') + '). Tell the buyer; offer the other direction.' }) }] };
  const out = { tweaked_zone: z.name, zone_id: z.id, change: 'scale', direction: up ? 'up' : 'down', scaled_zones: done, applied_as: 'direct texture scale on ' + done.length + ' zone(s) of this look (nothing else re-stacked)' };
  const res = Object.assign({}, out, best || last || {}); if (last && last.images) res.images = last.images; if (res.measured) res.measured = Object.assign({}, res.measured, { nothing_visible: allNothing });
  histPush(done.length); res.undo_with = 'spb_undo steps:1 reverts this scale change (all ' + done.length + ' zone edit' + (done.length > 1 ? 's' : '') + ')';
  if (errText) res.partial = 'Some zones were scaled, then: ' + errText.slice(0, 200);
  if (limits.length) res.at_limit = limits;
  const after = await zonesNow(), az = after && after.find((q) => String(q.id) === String(z.id)); if (az) { out.after = String(az.look || ''); res.after = out.after; }
  return { content: toContent({ result: res }) };
}
async function doTweak(args) {
  if (!OAI) return doTweakLegacy(args);
  const said = String(args.buyer_said || '').trim(); if (!said) return doTweakLegacy(args);
  const zs = await zonesNow(); if (!zs) return doTweakLegacy(args);
  let z = null;
  if (args.zone_id) z = zs.find((q) => String(q.id) === String(args.zone_id)); else if (args.zone_name) z = zs.find((q) => q.name === args.zone_name) || zs.find((q) => String(q.name || '').toLowerCase() === String(args.zone_name).toLowerCase());
  else if (WORKING) z = zs.find((q) => String(q.id) === String(WORKING.id)) || zs.find((q) => q.name === WORKING.name);
  const ch = String(args.change || '').toLowerCase().replace('color', 'colour'), up = String(args.direction || 'down').toLowerCase() === 'up';
  // ONLINE-AI 2026-10-09 (full run, M-T01 t3 "now a bit brighter": the model named the colour-source carbon zone that shows 0% of the roof; the planner LIFTED it above the seafoam recolours and the roof turned solid yellow = the base colour):
  // a tweak aimed at a zone of this bridge's last write that shows nothing goes to the sibling of the same write that shows the most. Nothing is re-stacked.
  let retargeted = null;
  if (z && !GFX[String(z.id)] && (Number(z.visible_pct) || 0) < 0.05 && WORKING && WORKING.sibs && WORKING.sibs.some((q) => String(q.id) === String(z.id))) {
    const alt = zs.filter((q) => !q.muted && String(q.id) !== String(z.id) && WORKING.sibs.some((w) => String(w.id) === String(q.id)) && (Number(q.visible_pct) || 0) >= 0.05).sort((a, b) => (Number(b.visible_pct) || 0) - (Number(a.visible_pct) || 0))[0];
    if (alt) { retargeted = z.name; z = alt; args = Object.assign({}, args, { zone_id: String(alt.id), zone_name: undefined }); }
  }
  let res;
  if (z && (ch === 'scale' || ch === 'rotation') && GFX[String(z.id)] && !process.env.SPB_MCP_NOGFXSCALE) res = await oaiGraphicTweak(args, z, GFX[String(z.id)], ch, up, zs);
  else if (z && ch === 'scale' && !/\| pattern /.test(String(z.look || '')) && (SPEC_ONLY_RE.test(finishTok(z)) || /colour source/.test(String(z.look || '')))) res = await oaiFinishScale(args, z, zs);
  else { res = await doTweakLegacy(args); if (!res.isError && !/"changed":\s*false/.test(String(res.content && res.content[0] && res.content[0].text || ''))) histPush(1); }
  if (z && !res.isError && !/"changed":\s*false/.test(String(res.content && res.content[0] && res.content[0].text || '')) && ['scale', 'shine', 'metal', 'intensity', 'opacity'].indexOf(ch) !== -1 && SPEC_ONLY_RE.test(finishTok(z))) withFields(res, { spec_only_note: 'This finish (' + finishTok(z) + ') is a SPEC finish (shine / metal / texture): the change IS applied but the flat colour preview cannot show it. If measured says nothing visible, that is why: say so once, offer spb_preview spec=true, and do NOT redo it or add zones to chase it.' });
  if (retargeted && !res.isError) withFields(res, { retargeted_from: retargeted, retargeted_note: '"' + retargeted + '" shows 0% of the car (other zones cover it), so the change was applied to "' + z.name + '", the zone of the same look that shows. Say it in one clause.' });
  { const tx = String(res.content && res.content[0] && res.content[0].text || '');
    if (!res.isError && DIRTY && /"applied":\s*\[\s*"/.test(tx) && !/"changed":\s*false/.test(tx) && !/"render_next"/.test(tx)) withFields(res, { render_next: RENDER_NEXT });
    if (RENDERED_PENDING && !res.isError && /"measured"/.test(tx)) { RENDERED_PENDING = false; const big = (re) => { const m = re.exec(tx); return !!m && Number(m[1]) > 20000; }; if (big(/"outside_px":\s*(\d+)/) || big(/"decal_px":\s*(\d+)/)) withFields(res, { after_render_note: AFTER_RENDER_NOTE }); }
    if (!res.isError && /"changed":\s*false/.test(tx) && !/"rule"/.test(tx) && ['brightness', 'colour', 'hue', 'saturation'].indexOf(ch) !== -1) withFields(res, { fallback_hint: "The tweak changed nothing. If you fall back to spb_do, put the part or layer name in text (for example \"a bit darker (the Logos layer)\") and keep replace_last:true: a frame target that is not in the text is dropped and the planner asks Where should that go?" }); }
  // OA3 2026-10-10: see the OA3 constant. The zone borrows its colour from the paint underneath, so brightness / hue / saturation / colour on it applies but cannot show (measured nothing_visible).
  if (OA3 && z && !res.isError && ['brightness', 'hue', 'saturation', 'colour'].indexOf(ch) !== -1 && /colour source/.test(String(z.look || ''))) {
    const tx3 = String(res.content && res.content[0] && res.content[0].text || '');
    if (/"nothing_visible":\s*true/.test(tx3)) withFields(res, { colour_source_note: 'The zone "' + z.name + '" takes its colour from the paint underneath it (colour source), so a ' + ch + ' change on it cannot show: nothing visible changed. Do not report this as done. Make the same change on the PART instead: spb_do with the buyer\'s words plus the part name in text, frame verb adjust (relative {prop, dir, amount}) targeting that part, replace_last true; then spb_get_zones and, if the new zone lost the finish, put the finish back with spb_edit_zone. If you cannot, tell the buyer plainly that nothing visibly changed.' });
  }
  const t0 = String(res.content && res.content[0] && res.content[0].text || '');
  if (!res.isError && !/"undo_with"/.test(t0) && !/"changed":\s*false/.test(t0)) withFields(res, { undo_with: 'spb_undo steps:1 reverts this tweak' });
  return res;
}
async function doTweakLegacy(args) {
  const said = String(args.buyer_said || '').trim(); if (!said) return { isError: true, content: [{ type: 'text', text: 'buyer_said is required (the buyers own words).' }] };
  const zs = await zonesNow(); if (!zs) return { isError: true, content: [{ type: 'text', text: 'Shokker did not list the zones (is the app open in Pro mode with the bridge on?).' }] };
  let z = null;
  if (args.zone_id) z = zs.find((q) => String(q.id) === String(args.zone_id)); else if (args.zone_name) z = zs.find((q) => q.name === args.zone_name) || zs.find((q) => String(q.name || '').toLowerCase() === String(args.zone_name).toLowerCase());
  else if (WORKING) z = zs.find((q) => String(q.id) === String(WORKING.id)) || zs.find((q) => q.name === WORKING.name);
  if (!z) return { content: [{ type: 'text', text: JSON.stringify({ changed: false, rule: 'NOTHING changed: there is no current zone to tweak (nothing was made through this bridge yet, or it was removed). Call spb_get_zones, pick the zone the buyer means and pass zone_name, or make the look first. If you cannot tell which zone, ask the buyer which one.', zones: zs.slice(0, 12).map((q) => q.name) }) }] };
  const ch = String(args.change || '').toLowerCase().replace('color', 'colour'), up = String(args.direction || 'down').toLowerCase() === 'up', amt = args.amount;
  const amtWord = (typeof amt === 'string' && /lot|much|way|big/.test(amt)) ? 'lot' : ((typeof amt === 'string' && /bit|little|touch|slight/.test(amt)) ? 'little' : undefined);
  const look = String(z.look || ''), out = { tweaked_zone: z.name, zone_id: z.id, change: ch, direction: up ? 'up' : 'down' };
  let r;
  const gx = GFX[String(z.id)];
  if (ch === 'scale' && gx && !process.env.SPB_MCP_NOGFXSCALE) {
    if (gx.seq !== WSEQ) return { content: [{ type: 'text', text: JSON.stringify({ changed: false, rule: 'NOTHING changed. This zone is a drawn ' + gx.args.kind + ' graphic and other changes were made after it, so it cannot be re-drawn at another size without losing them. Tell the buyer, and offer to draw it again at the new size.' }) }] };
    const n0 = Number(gx.args.n) || 16, f = amtWord === 'lot' ? 2.2 : (amtWord === 'little' ? 1.3 : 1.7), n1 = Math.max(2, Math.min(80, Math.round(up ? n0 / f : n0 * f)));
    const u = await bridgeCall('undo', { steps: 1 }, timeoutFor('undo')); if (!u.json || u.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(u) }] };
    const a2 = Object.assign({}, gx.args, { n: n1, buyer_said: said }); r = await bridgeCall('add_graphic', a2, timeoutFor('add_graphic'));
    out.before = { n: n0, kind: gx.args.kind }; out.after_requested = { n: n1 }; out.applied_as = 'graphic re-drawn at ' + n1 + ' (was ' + n0 + '), the old one undone';
    if (r.json && r.json.ok !== false) { WSEQ++; const zs2 = await zonesNow(); const nz = zs2 && zs2.find((q) => !q.muted && zs.every((o) => String(o.id) !== String(q.id))); if (nz) { GFX[String(nz.id)] = { seq: WSEQ, args: a2 }; WORKING = { id: nz.id, name: nz.name }; out.tweaked_zone = nz.name; out.zone_id = nz.id; } }
    if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(r) }] };
    const res0 = r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result) ? Object.assign({}, out, r.json.result) : Object.assign({}, out, { result: r.json.result });
    res0.honesty = 'The graphic was re-drawn (one undo + one draw). Report only what measured shows.';
    return { content: toContent({ result: res0 }) };
  }
  const solid = /colour solid (#[0-9a-fA-F]{6})/.exec(look);
  if (ch === 'hue' && solid && !process.env.SPB_MCP_NOHUEFIX) {
    const nh = nudgeHue(solid[1], up, args.toward, amtWord); out.before = { colour: solid[1] }; out.after_requested = { colour: nh, hue_rotated: true };
    r = await bridgeCall('edit_zone', { zone_id: String(z.id), buyer_said: said, color: nh }, timeoutFor('edit_zone')); if (r.json && r.json.ok !== false) WSEQ++;
  } else if (['scale', 'brightness', 'hue', 'saturation', 'shine', 'metal'].indexOf(ch) !== -1) {
    const prop = { scale: 'scale', brightness: 'lightness', hue: 'hue', saturation: 'saturation', shine: 'gloss', metal: 'metal' }[ch], rel = { prop, dir: up ? 1 : -1 }; if (amtWord) rel.amount = amtWord; else if (typeof amt === 'number') rel.amount = amt;
    out.before = look;
    r = await bridgeCall('do', { frame: { v: 1, act: 'change', ops: [{ verb: 'adjust', target: { kind: 'zone', zones: [String(z.id)] }, relative: rel }], decals: 'protect' }, text: said }, timeoutFor('do'));
  } else if (ch === 'rotation') {
    const pid = lookPattern(look), cur = ROTS[z.id] != null ? ROTS[z.id] : (lookNum(look, 'rotation') || 0), deg = typeof amt === 'number' ? Math.abs(amt) : (amtWord === 'lot' ? 90 : (amtWord === 'little' ? 15 : 30)), nv = ((Math.round(cur + (up ? deg : -deg)) % 360) + 360) % 360;
    const a = { zone_id: String(z.id), buyer_said: said }; if (pid) a.pattern = { id: pid, rotation: nv }; else a.rotation = nv;
    out.before = { rotation: cur }; out.after_requested = { rotation: nv }; r = await bridgeCall('edit_zone', a, timeoutFor('edit_zone')); if (r.json && r.json.ok !== false) ROTS[z.id] = nv;
  } else if (ch === 'opacity' || ch === 'intensity') {
    const pid = lookPattern(look), po = (function () { const m = /pattern [^|]*opacity (\d+)/.exec(look); return m ? Number(m[1]) : 100; })(), step = amtWord === 'lot' ? 40 : (amtWord === 'little' ? 15 : 25);
    if (pid && ch === 'opacity') { const nv = clampN(po + (up ? step : -step), 5, 100); out.before = { pattern_opacity: po }; out.after_requested = { pattern_opacity: nv }; r = await bridgeCall('edit_zone', { zone_id: String(z.id), buyer_said: said, pattern: { id: pid, opacity: nv } }, timeoutFor('edit_zone')); }
    else { const ci = lookNum(look, 'intensity'); const cur = ci == null ? 100 : ci, nv = clampN(cur + (up ? step : -step), 5, 100); out.before = { intensity: cur }; out.after_requested = { intensity: nv }; r = await bridgeCall('edit_zone', { zone_id: String(z.id), buyer_said: said, intensity: nv }, timeoutFor('edit_zone')); }
  } else if (ch === 'colour') {
    if (!/^#[0-9a-f]{6}$/i.test(String(args.to_colour || ''))) return { content: [{ type: 'text', text: JSON.stringify({ changed: false, rule: 'to_colour must be a #rrggbb hex: resolve the buyers colour word first, then call again.' }) }] };
    out.before = { look }; out.after_requested = { colour: args.to_colour }; r = await bridgeCall('edit_zone', { zone_id: String(z.id), buyer_said: said, color: args.to_colour }, timeoutFor('edit_zone'));
  } else return { content: [{ type: 'text', text: JSON.stringify({ changed: false, rule: 'change must be one of scale | rotation | brightness | hue | saturation | shine | metal | opacity | intensity | colour.' }) }] };
  if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(r) }] };
  WSEQ++;          // W1MCP
  const after = await zonesNow(), az = after && after.find((q) => String(q.id) === String(z.id)); if (az) { out.after = String(az.look || ''); WORKING = { id: z.id, name: az.name }; }
  const res = r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result) ? Object.assign({}, out, r.json.result) : Object.assign({}, out, { result: r.json.result });
  res.honesty = 'Report only what before / after / measured show. If measured says no_visible_change, say the change was applied (name the numbers) but is too small or too fine to see on this preview, and offer a bigger step. Do not claim a look you did not verify.';
  return { content: toContent({ result: res }) };
}
// Named targets require fresh current-source confirmation. No cache or fail-open fallback.
async function unknownPartRefusal(app, args) {
  const prepared = await require('../chatgpt/source-bound-execution.cjs').prepare(app, args || {}, () =>
    httpJson('POST', '/api/mcp/call', { tool: 'get_state', args: {}, timeout: 30 }, 45000));
  if (prepared.blocked) return prepared.blocked;
  if (args) args._spb_expected_source = prepared.args._spb_expected_source;
  return null;
}
async function chatTool(name, args) {          // APPCHAT 2026-10-09
  const unreachable = (e) => ({ isError: true, content: [{ type: 'text', text: 'Could not reach Shokker Paint Booth on 127.0.0.1:' + PORT + ' (' + (e && e.message) + '). Is the app running?' }] });
  if (name === 'spb_reply') {
    const t = String((args && args.text) || '').trim(); if (!t) return { isError: true, content: [{ type: 'text', text: 'text is required' }] };
    let r; try { r = await httpJson('POST', '/api/mcp/reply', { text: t, reply_to: args.reply_to, finishes: Array.isArray(args.finishes) ? args.finishes : undefined, use_on: args.use_on || undefined }, 15000); } catch (e) { return unreachable(e); }
    if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(r) }] };
    return { content: [{ type: 'text', text: JSON.stringify({ shown_in_app: true, next: 'call spb_wait_for_message again for the buyer’s next message' }) }] };
  }
  const secs = Math.max(10, Math.min(590, Number(args && args.timeout_s) || 170));
  let r; try { r = await httpJson('GET', '/api/mcp/inbox/wait?timeout=' + secs, null, (secs + 20) * 1000); } catch (e) { return unreachable(e); }
  if (r.status === 404) return { isError: true, content: [{ type: 'text', text: 'This Shokker version has no app chat yet: update Shokker Paint Booth.' }] };
  if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(r) }] };
  if (r.json.none) return { content: [{ type: 'text', text: JSON.stringify({ none: true, enabled: r.json.enabled, next: r.json.enabled === false ? 'The buyer switched the AI connection off: stop waiting.' : 'No message yet: call spb_wait_for_message again.' }) }] };
  const newest3 = (r.json.messages || []).at(-1);          // CX3: classify the newest buyer message; advice-only blocks every non-read-only tool (see callTool)
  if (newest3) APP_CHAT_SCOPE = newest3.document_scope || null;
  if (DESIGN_INTENT && newest3) { try { APP_CHAT_ADVICE = DESIGN_INTENT.classify(newest3.text).mode === 'advice'; APP_CHAT_ADVICE_AT = Date.now(); } catch (e3) { APP_CHAT_ADVICE = false; } }
  return { content: [{ type: 'text', text: JSON.stringify({ reply_to: newest3 && newest3.seq, request_intent: DESIGN_INTENT && newest3 ? DESIGN_INTENT.classify(newest3.text) : undefined, messages: r.json.messages, note: r.json.note || undefined, rule: 'These are the BUYER’S OWN WORDS typed in the Shokker app chat box. Handle them exactly as if typed here (same RESTRAINT rules, buyer_said = this text verbatim), then spb_reply with reply_to equal to the latest message seq and your short answer (questions you would ask the buyer also go through spb_reply), then spb_wait_for_message again.' }) }] };
}
async function callTool(name, args) {
  if (name === 'spb_car_knowledge') {
    try { return {content:[{type:'text',text:JSON.stringify(CAR_KNOWLEDGE.lookup(args || {}))}]}; }
    catch(e) { return {isError:true,content:[{type:'text',text:String(e.message||e)}]}; }
  }
  if (CX3 && APP_CHAT_ADVICE && Date.now() - APP_CHAT_ADVICE_AT < 900000 && !READ_ONLY.has(name) && name !== 'spb_reply' && !(name === 'spb_kit' && args && (args.action === 'check' || args.action === 'propose'))) return { isError: true, content: [{ type: 'text', text: 'The current buyer message is advice only. Discuss the design in words (spb_reply); wait for an explicit editing request before changing or rendering anything.' }] };          // CX3 2026-10-09
  if (name === 'spb_assistant_context' && CX2 && ASSISTANT_CONTEXT) {          // CX2: read-only; every sub-read goes through the normal tool paths (no new write access)
    try {
      const packet = await ASSISTANT_CONTEXT.build(args || {}, {
        tools: allTools, call: callTool,
        appKnowledge:query=>FRESH_KNOWLEDGE.packet(MK,query,VERSION),
        history: async () => {
          const r = await httpJson('GET', '/api/mcp/conversation', null, 10000);
          if (r.status >= 400 || !r.json || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: 'Recent chat unavailable: ' + friendly(r) }] };
          return r.json;
        }
      });
      return { content: [{ type: 'text', text: JSON.stringify(packet) }] };
    } catch (e) { return { isError: true, content: [{ type: 'text', text: String(e && e.message || e) }] }; }
  }
  if (name === 'spb_kit') return KITS ? kitTool(args || {}) : { isError: true, content: [{ type: 'text', text: 'Unknown tool spb_kit' }] };
  if (name === 'spb_wait_for_message' || name === 'spb_reply') return chatTool(name, args || {});
  if (name === 'spb_tweak' && !process.env.SPB_MCP_NOTWEAK) return doTweak(args || {});
  if (name === 'spb_encyclopedia') { // ONLINE_GROUNDING: GET the server search directly (no app page needed)
    const q = String((args && args.query) || '').trim(); if (!q) return { isError: true, content: [{ type: 'text', text: 'query is required' }] };
    let r; try { r = await httpJson('GET', '/api/encyclopedia/search?k=' + Math.max(1, Math.min(8, Number(args.k) || 4)) + '&q=' + encodeURIComponent(q.slice(0, 300)), null, 20000); }
    catch (e) { return { isError: true, content: [{ type: 'text', text: 'Could not reach Shokker Paint Booth on 127.0.0.1:' + PORT + ' (' + (e && e.message) + '). Is the app running?' }] }; }
    if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: (r.json && r.json.message) || ('Shokker returned HTTP ' + r.status + (r.status === 404 ? ' (this Shokker version has no encyclopedia search yet: use spb_manual)' : '')) }] };
    const res = (r.json.results || []).map((x) => ({ title: x.title, summary: x.summary, faq: x.faq || undefined, more_faq: (x.more_faq && x.more_faq.length) ? x.more_faq : undefined, how: x.how, controls: (x.controls && x.controls.length) ? x.controls : undefined, link: x.link, confident: x.confident }));
    if (MK) {          // MCP-KNOW: code-verified facts first (they win where an article is wrong), then the articles; the app briefing once per session
      const vf = process.env.SPB_FRESH_KNOWLEDGE_OFF ? MK.factsFor(q) : FRESH_KNOWLEDGE.statelessFacts(MK,q).map(f=>f.text), out = { content: [{ type: 'text', text: fitJson(vf.length ? { verified_facts: vf, articles: res, rule: 'verified_facts are checked against the app itself and win where an article disagrees. Otherwise answer from the articles, cite the article title. confident=false = a weak match.' } : { articles: res, rule: (process.env.SPB_FRESH_KNOWLEDGE_OFF ? 'The SPB Encyclopedia is authoritative: answer from these articles, cite the article title, never contradict them. confident=false = a weak match.' : 'Bundled verified app facts and current measured capabilities take precedence over conflicting article text. Answer from supported guidance and cite the article title. confident=false = a weak match.') }, 12000) }] };
      const br = MK.briefingOnce(); if (br) out.content.push({ type: 'text', text: br });
      return out;
    }
    return { content: [{ type: 'text', text: fitJson({ articles: res, rule: 'The SPB Encyclopedia is authoritative: answer from these articles, cite the article title, never contradict them. confident=false = a weak match.' }, 12000) }] };
  }
  if (OAI && name === 'spb_undo' && !process.env.SPB_MCP_NOTWEAK) return oaiUndo(args || {});
  // ONLINE-AI 2026-10-09 (2): 1.4.2 allowed a render only when the buyer asked (6 of 52 scenarios had regressed when the model rendered on its own, because the first write after a render was diffed against the full-render picture: ~100k px of false spill; page P7).
  // P7 is fixed page-side now (js/spb-intent-report.js snap(), kill switch SPB_P7_OFF), and the owner asked for the render after changes, so: render when this bridge changed the paint since the last render (DIRTY) or when the buyer asked; refuse a render when nothing changed.
  if (OAI && name === 'spb_render' && !DIRTY && !(args && args.buyer_asked_render === true)) return { content: [{ type: 'text', text: JSON.stringify({ rendered: false, changed: false, note: 'Nothing was rendered: nothing has changed since the last render and the buyer did not ask to render / save / export / see it in iRacing. Answer in words. If the buyer did ask, call spb_render again with buyer_asked_render:true.' }) }] };
  const app = NAME_MAP[name];
  if (!app) return { isError: true, content: [{ type: 'text', text: 'Unknown tool ' + name }] };
  // R9 2026-10-08 (R9-17 'nah back to how it was': Claude re-set the hood to a hand-picked yellow instead of undoing; the pixel check passed it, the hood was NOT the original mint). A write whose buyer words are an undo /
  // revert / back-to-original is refused with the instruction to call spb_undo (nothing changes). Kill switch: SPB_MCP_NOUNDOGUARD=1. ONLINE-AI 2026-10-09: the two regexes below were written with literal BACKSPACE characters (0x08; a Python '\b' in a non-raw string) since R9, so this guard NEVER matched. Now real \b word boundaries; mcp/test/undo_guard_regex.test.cjs fails on any 0x08 in this file.
  if (!process.env.SPB_MCP_NOUNDOGUARD && ['do', 'edit_zone', 'refinish', 'add_zone', 'edit_layer', 'duplicate_zone', 'add_graphic', 'apply_scheme'].indexOf(app) !== -1) {
    const said = String((args && (args.buyer_said || args.text)) || '').toLowerCase();
    if (said && said.length < 90 && /\b(undo|revert|take (that|it) back|put it back|back to (how it was|the original|what it was|normal|before|stock)|as it was before|how it was|go back)\b/.test(said) && !/\b(and|then|but) (make|paint|change|add|put|now)\b/.test(said)) {
      return { content: [{ type: 'text', text: JSON.stringify({ changed: false, rule: 'NOTHING was changed. The buyer asked to UNDO / go back. Call spb_undo (steps = how many changes you made since the original: 1 for "undo that", 2 for "undo both", all of them for "back to how it was"), then check measured and tell the buyer. Do not set a colour by hand.' }) }] };
    }
  }
  // R4 2026-10-08 (R4-21 Gulf livery / I4-4 'whole car dark blue' via apply_scheme): the scheme's body base only covers the paint layer's own colour, so an old zone on top (mint 'Seafoam Chalk', 48% of the car)
  // kept showing and the result was patchy blobs while the reply claimed 'powder blue body'. For a CONFIRMED scheme with a base colour the body is recoloured FIRST through spb_do (same call Claude would make,
  // keeps accents / decals, the stripes are then laid above it). Best effort: any refusal / error is ignored and the scheme goes ahead unchanged. Kill switch: SPB_MCP_NOBASEFIRST=1.
  if (WRITE_APPS.indexOf(app) !== -1) { const refusal = await unknownPartRefusal(app, args || {}); if (refusal) return { content: [{ type: 'text', text: JSON.stringify(refusal) }] }; }
  let baseFirst = null;
  if (app === 'apply_scheme' && !process.env.SPB_MCP_NOBASEFIRST && args && args.confirm === true && args.keep_accents !== false && args.palette && /^#[0-9a-f]{6}$/i.test(String(args.palette.base || '')) && args.buyer_said) {
    try {
      const b = await bridgeCall('do', { frame: { v: 1, act: 'change', ops: [{ verb: 'recolour', target: { kind: 'body' }, look: { colour: { hex: args.palette.base } } }], decals: 'protect' }, text: String(args.buyer_said), confirm: true, _spb_expected_source: args._spb_expected_source }, timeoutFor('do'));
      const bj = b.json && b.json.result;
      baseFirst = (b.json && b.json.ok !== false && bj && bj.changed !== false && !bj.ask) ? 'done' : 'skipped';
    } catch (e) { baseFirst = 'skipped'; }
  }
  // ONLINE-AI 2026-10-09 (M-T04 "checkered flag pattern on the roof": one white colour in the rear fifth of the roof, the black squares "skipped"): a checker fills the WHOLE named part unless the buyer asked for a band / edge, and the
  // second colour is drawn as the complementary squares (checkerSecond). Both are best effort: any refusal leaves the call exactly as the model sent it.
  let chk2 = null;
  if (OAI && app === 'add_graphic' && args && String(args.kind || '').toLowerCase() === 'checker') {
    if (args.u0 == null && args.u1 == null && args.v0 == null && args.v1 == null && !/\b(rear|back|end|edge|strip|stripe|band|line|trim|bottom|top|front|nose|tail|corner|rocker)\b/i.test(String(args.buyer_said || ''))) args = Object.assign({}, args, { u0: 0, u1: 1 });
    if (Array.isArray(args.colours) && args.colours.length >= 2 && /^#[0-9a-f]{6}$/i.test(String(args.colours[1])) && String(args.colours[1]).toLowerCase() !== String(args.colours[0]).toLowerCase()) { chk2 = String(args.colours[1]); args = Object.assign({}, args, { colours: [args.colours[0]] }); }
  }
  const zBefore = (!process.env.SPB_MCP_NOTWEAK && WRITE_APPS.indexOf(app) !== -1) ? await zonesNow() : null;
  let r;
  try { r = await bridgeCall(app, args || {}, timeoutFor(app)); }
  catch (e) { return { isError: true, content: [{ type: 'text', text: 'Could not reach Shokker Paint Booth on 127.0.0.1:' + PORT + ' (' + (e && e.message) + '). Is the app running?' }] }; }
  if (!r.json || r.status >= 400 || r.json.ok === false) return { isError: true, content: [{ type: 'text', text: friendly(r) }] };
  if (chk2 && r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result) && r.json.result.changed !== false && !r.json.result.ask && !r.json.result.ask_back) {
    try {
      const r2 = await bridgeCall('add_graphic', checkerSecond(args, chk2), timeoutFor('add_graphic')), R1 = r.json.result, R2 = r2.json && r2.json.result;
      if (gfxGood(r2) && R2 && typeof R2 === 'object') { r.json.result = Object.assign({}, R1, { applied: (R1.applied || []).concat(R2.applied || []), images: R2.images || R1.images, second_colour: { colour: chk2, drawn_as: 'the complementary squares (one row up), so both colours show as a real checkerboard', measured: R2.measured && R2.measured.line } }); }
      else { r.json.result = Object.assign({}, R1, { incomplete: 'The second colour (' + chk2 + ') did NOT draw. Say so plainly and offer it.' }); chk2 = null; }
    } catch (e) { chk2 = null; }
  }
  if (baseFirst === 'done' && r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result)) r.json.result = Object.assign({}, r.json.result, { body_recoloured_first: 'The whole body was recoloured to the scheme base colour first (spb_do body), so the old body zones no longer hide it; the stripes and trim are laid above it. Report from measured.' });
  if (zBefore && r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result)) { const zAfter = await zonesNow(), pw = OAI ? pickWorkingOAI(zBefore, zAfter) : null, wz = pw ? pw.wz : pickWorking(zBefore, zAfter); if (wz) { WORKING = { id: wz.id, name: wz.name, sibs: pw ? pw.sibs : undefined }; r.json.result = Object.assign({}, r.json.result, { working_zone: wz.name, working_zone_note: 'Follow-ups on this look (smaller, brighter, change X to Y) = spb_tweak: it moves one property of this zone and nothing else.' }); } }
  if (WRITE_APPS.indexOf(app) !== -1) WSEQ++;
  if (app === 'add_graphic' && WORKING && args && args.kind && !process.env.SPB_MCP_NOGFXSCALE) { GFX[String(WORKING.id)] = { seq: WSEQ, args: Object.assign({}, args), colour2: chk2 || undefined }; if (OAI && WORKING.sibs) WORKING.sibs.forEach((q) => { GFX[String(q.id)] = { seq: WSEQ, args: Object.assign({}, args), colour2: chk2 || undefined }; }); }          // W1MCP (+ ONLINE-AI: every zone of that write)
  if (app === 'undo') { WORKING = null; }
  if (OAI && r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result)) {          // ONLINE-AI 2026-10-09: say what the buyer must hear, and how to undo
    const R = r.json.result, extra = {}, sk = R.tool_result && R.tool_result.skipped;
    if (app === 'render' && R.rendered !== false) { DIRTY = false; RENDERED_PENDING = true; }
    if (WRITE_APPS.indexOf(app) !== -1 && RENDERED_PENDING) { RENDERED_PENDING = false; if (R.measured && (Number(R.measured.outside_px) > 20000 || Number(R.measured.decal_px) > 20000)) extra.after_render_note = AFTER_RENDER_NOTE; }
    if (app === 'render' && (R.files_saved === 0 || /not set/i.test(String(R.iracing_folder || '')))) extra.warning = 'Rendered in the app, but NO file was written (files_saved 0, iracing_folder not set): iRacing will not see this paint yet. Tell the buyer plainly; the steps are in spb_encyclopedia ("iRacing folder") or spb_check_setup. Do not say it was saved.';
    if (WRITE_APPS.indexOf(app) !== -1 && R.measured && R.measured.nothing_visible === true && /(carbon|chrome|matte|satin|brushed|metallic|pearl|"scale"|"rotation")/i.test(JSON.stringify(args || {}))) extra.nothing_visible_note = 'Expected for a texture size / shine-only change (carbon, chrome, matte, weave scale): the flat preview cannot show it, the change IS applied. Say that once. Do NOT redo it, duplicate zones or undo to chase a visible difference (spb_preview spec=true shows the spec map).';
    if (app === 'add_graphic' && Array.isArray(sk) && sk.length) extra.incomplete = 'Part of what was asked did NOT draw: ' + sk.join('; ') + '. Say so plainly (never "done" for the whole thing) and offer the missing part.';
    if (WRITE_APPS.indexOf(app) !== -1 && app !== 'undo' && R.changed !== false && !R.ask && !R.ask_back && !R.unknown_part) { histPush(1 + (chk2 ? 1 : 0) + ((app === 'apply_scheme' && baseFirst === 'done') ? 1 : 0)); extra.undo_with = 'spb_undo steps:1 reverts this' + (chk2 ? ' (both colours)' : ((app === 'apply_scheme' && baseFirst === 'done') ? ' (the body recolour + the scheme)' : '')); }
    if (WRITE_APPS.indexOf(app) !== -1 && DIRTY && R.changed !== false && !R.ask && !R.ask_back && !R.unknown_part && !(Array.isArray(R.failed) && R.failed.length && !(R.applied && R.applied.length))) extra.render_next = RENDER_NEXT;
    if (Object.keys(extra).length) r.json.result = Object.assign({}, R, extra);
  }
  if (MK && READ_ONLY.has(name) && r.json.result && typeof r.json.result === 'object' && !Array.isArray(r.json.result)) {          // MCP-KNOW: one note per read-only tool family per session
    const nt = (name === 'spb_preview' && !(args && args.spec)) ? null : MK.note(name); if (nt) r.json.result = Object.assign({}, r.json.result, { app_facts: nt });
  }
  // Geometry authority: legacy library coordinates carry no calibrated source receipt.
  r.json.result = require('../chatgpt/geometry-authority.cjs').qualifyLegacyTool(name, r.json.result);
  const content = toContent({ result: r.json.result });
  if (MK && (name === 'spb_status' || name === 'spb_get_state')) { const br = MK.briefingOnce(); if (br) content.push({ type: 'text', text: br }); }
  if (BLIND_TOOLS.has(name) && isBlindClient()) {
    content.push({ type: 'text', text: await blindText(name, r.json.result) });
    if (blindMode() === 'true') return { content: content.filter((c) => c.type !== 'image' && !/^image: /.test(c.text || '')) };
  }
  return { content };
}

// ------------------------------------------------------------------ MCP over stdio
function send(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); }
function reply(id, result) { send({ jsonrpc: '2.0', id, result }); }
function fail(id, code, message) { send({ jsonrpc: '2.0', id, error: { code, message } }); }
async function handle(msg) {
  const { id, method, params } = msg;
  const isReq = id !== undefined && id !== null;
  try {
    switch (method) {
      case 'initialize': {
        const ci = (params && params.clientInfo) || {}; CLIENT = { name: String(ci.name || ''), version: String(ci.version || '') };
        log('client', JSON.stringify({ name: CLIENT.name, version: CLIENT.version }), 'blind_mode=' + blindMode(), 'blind=' + isBlindClient());
        const want = params && params.protocolVersion; const v = SUPPORTED.includes(want) ? want : SUPPORTED[0];
        return reply(id, { protocolVersion: v, capabilities: { tools: { listChanged: false }, prompts: { listChanged: false } }, serverInfo: { name: 'shokker-paint-booth', title: 'Shokker Paint Booth', version: VERSION }, instructions: (process.env.SPB_FRESH_KNOWLEDGE_OFF ? (MK ? MK.instructions(INSTRUCTIONS) : INSTRUCTIONS) : FRESH_KNOWLEDGE.instructions(MK,INSTRUCTIONS,VERSION)) + (NATIVE_LAYER_COLOUR ? CX3_LAYER_NOTE : '') });
      }
      case 'notifications/initialized': case 'notifications/cancelled': return;
      case 'ping': return reply(id, {});
      case 'tools/list': return reply(id, { tools: allTools() });
      case 'tools/call': { const out = await callTool(params && params.name, params && params.arguments); return reply(id, out); }
      case 'prompts/list': return reply(id, { prompts: PROMPTS.map((p) => ({ name: p.name, description: p.description, arguments: p.arguments })) });
      case 'prompts/get': {
        const p = PROMPTS.find((x) => x.name === (params && params.name)); if (!p) return fail(id, -32602, 'Unknown prompt');
        return reply(id, { description: p.description, messages: [{ role: 'user', content: { type: 'text', text: p.text((params && params.arguments) || {}) } }] });
      }
      case 'resources/list': return reply(id, { resources: [] });
      case 'resources/templates/list': return reply(id, { resourceTemplates: [] });
      default: if (isReq) return fail(id, -32601, 'Method not found: ' + method);
    }
  } catch (e) { if (isReq) fail(id, -32603, String(e && e.message || e)); else log('error', String(e && e.message || e)); }
}
let buf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buf += chunk; let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (!line) continue;
    let msg; try { msg = JSON.parse(line); } catch (e) { log('bad json'); fail(null, -32700, 'Parse error'); continue; }
    if (Array.isArray(msg)) msg.forEach((m) => handle(m)); else handle(msg);
  }
});
process.stdin.on('end', () => process.exit(0));
log('ready, bridge port', PORT);
