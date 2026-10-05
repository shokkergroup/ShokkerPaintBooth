# SPB developer connection and efficient testing

Status: this proposal was superseded by the owner's explicit full-access build request.
The working implementation is [SPB MCP](../integrations/spb-mcp/README.md), with
14 MCP tools, stdio and authenticated loopback HTTP. Client configurations remain
user-controlled; no personal AI client configuration was overwritten.
Owner request: faster, cheaper development without taking over the desktop.

## What is possible

A private local MCP server can expose SPB-specific commands to Codex. Codex supports
local STDIO and Streamable HTTP MCP servers; no official SPB integration is required.
Reference: https://learn.chatgpt.com/docs/extend/mcp?surface=cli
MCP provides structured access. Savings depend on fewer calls and smaller results,
not the protocol alone. No percentage reduction has been measured or promised.

## Reuse existing pieces

- `server_routes/diagnostics.py`: server health and diagnostics.
- `js/canvas/tool-audit.js`: opt-in pixel, history and timing evidence.
- Existing Node/Python contracts: deterministic correctness checks.
- `tests/training_wheels_browser.py`: private headless Chrome, fresh profile,
  visible DOM controls, compact JSON and two screenshots; no desktop focus.
- `scripts/spb_context.js`: named code slices; select bounded slices, not full dumps.

Backend diagnostics alone do not know the browser's selected Layer, Zone or tool.
A frontend session adapter is required. It must call the same controllers as the
visible UI; bypassing dispatch would hide exactly the failures the owner reported.

## Narrow proposed pilot

Build one local bridge for Brush and Select Object -> Transform, using an isolated
fixture document. Do not build another editor or expose the owner's active document
by default. Prefer STDIO plus a loopback frontend adapter and allowlisted commands.

Proposed commands:
1. `get_state`: build, document, dimensions, tool, Layer/Zone target, dirty status.
2. `run_scenario`: named fixture and repeatable ordinary-controller actions.
3. `verify_result`: changed bounds, unchanged siblings/masks, exact Undo/Cancel.
4. `profile_interaction`: phase timings for a specified workload.
5. `get_evidence`: bounded errors or one relevant screenshot on failure/request.

Return one compact result with local artifact paths, for example:
`{"scenario":"number-rotate","pass":true,"changedLayers":["Numbers"],"otherObjectsExact":true,"zoneExact":true,"undoExact":true}`
This is an example schema, not evidence from an implemented MCP command.

## Workflow adopted now

Reproduce once, patch the responsible module, run the relevant regression, inspect
one visual result, record the remaining limitation, stop rechecking passing paths.
Use private headless browser tests for repeatable state/layout checks; keep the
separate Chrome session for pointer feel and visual review. Headless or throttled
background timings do not establish smoothness in the owner's foreground session.
Return counts, bounds and failures rather than arrays of pixels or whole DOM dumps.
Use targeted searches and bounded windows; do not reread giant files or old reports.
Only broaden testing for a new failure, changed shared behavior or owner report.

Pilot acceptance: same Brush/object workflows and failure detection as manual tests;
no owner-profile writes or desktop takeover; compare tool-call count, output bytes,
elapsed time and available usage data against the same baseline. Keep the bridge
only if it demonstrably reduces work without bypassing the user interaction path.

## Training Wheels correction completed in this session

First launch offers Turn on / No thanks / X. Guidance opens as a compact bottom-right
overlay, full quests stay available, and X persistently turns it off. Tutorial stays
reachable in Easy as well as Pro. Legacy explicit opt-outs and quest progress remain.
The prior center-docked guide was rejected by the owner and has been removed.
Browser evidence: `_tools_simplification_work/training-wheels-browser.json`.
