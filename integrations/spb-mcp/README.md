# Shokker Paint Booth MCP

A working, model-independent MCP server for operating SPB. It uses the official
Python MCP SDK and a dedicated Chrome session. There is no model API dependency,
no screen takeover and no renderer/tool-dispatch replacement.

It is a small background service. A skill is optional teaching material; the
included `spb://guide` MCP resource provides operating instructions to any client.
MCP is supplied by the AI host application, so a raw model without tool access
cannot connect by itself. Local stdio and authenticated Streamable HTTP work.

## What it can do

- Discover and operate all current UI controls, dropdowns and dialogs dynamically.
- Paint, select, pick colors, erase, pan, zoom and transform using browser pointer
  paths and keyboard modifiers through the existing SPB event handlers.
- Inspect active Layer/Zone targets, canvas dimensions, document metadata and errors.
- Import local files through the Shokker picker or HTML file chooser; interact with
  Save/Open, render/export controls and download files into an artifact folder.
- Open other pages of the same SPB server, including specialized editors/viewers.
- Run arbitrary JavaScript inside the selected app page to call ANY existing SPB
  function/API, inspect full app state, and automate operations not covered by UI
  convenience tools. This full-access tool is intentionally not a read-only sandbox.
- Return native MCP screenshots, exact canvas hashes, compact JSON and paged results.
- Handle long scripts by operation ID, including prompts that need another tool call.

This gives broad control, not a claim that every existing SPB feature is bug-free.
An underlying broken function stays a bug; the MCP reports it instead of replacing
it with a fake result. Controller-level scripting does not validate pointer behavior.

## Start using it on this machine

SPB must already be running. Production browser endpoint: `http://localhost:59876/`.
Development validation uses the existing isolated server at `http://localhost:59880/`.
Chrome and Python3.10+ are required. Tested dependencies are pinned in requirements.

For an isolated dependency installation, run `Install-SPB-MCP.ps1` in PowerShell.
It creates `.venv`, installs dependencies, and writes `data/client-config.json`.
It never overwrites Codex, Claude or another application's configuration.
On this machine the already-installed Python also runs the server directly:

```powershell
python integrations/spb-mcp/spb_mcp_server.py --print-config
```

The output is a ready-to-copy MCP `mcpServers.spb` entry with absolute paths. Add
that entry to an MCP-capable client's settings. Clients using separate form fields
need the same Command and Arguments. Choose the model within that client as usual.
For clients with TOML settings, the equivalent entry on this machine is:

```toml
[mcp_servers.spb]
command = 'C:\Python313\python.exe'
args = ['C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\integrations\spb-mcp\spb_mcp_server.py', '--url', 'http://localhost:59876/']
```

Use the virtual-environment Python path instead after running the installer.
Do not run the stdio server as a persistent visible terminal: the AI client starts
and stops it. This build does not silently modify the AI clients installed here.

## HTTP connection for multiple clients

```powershell
python integrations/spb-mcp/spb_mcp_server.py --transport streamable-http
```

Endpoint: `http://127.0.0.1:59890/mcp`. The server generates
`integrations/spb-mcp/data/http-token.txt` on first start. Configure the client with
`Authorization: Bearer <contents of that file>`. Keep the token out of shared logs.
Loopback binding and the MCP SDK's origin/host validation remain enabled.

For unattended Windows launch, use Start-Process with `-WindowStyle Hidden` and
explicit log files; the stdio configuration is easier for normal local clients.
`Start-SPB-MCP.ps1` provides that hidden launch; `Stop-SPB-MCP.ps1` checks the
recorded process identity before stopping it. Save and close MCP documents first.
Cloud-only AI hosts cannot reach your computer's localhost. They require a secure
reachable deployment/connector; this build does not publicly expose SPB or create
a tunnel. Clients that support only OAuth enrollment rather than supplied bearer
headers will need that additional deployment adapter.

Two clients can address the same explicit SPB session ID through one HTTP server.
Commands are serialized per document. Long app scripts block new mutating commands
until they finish; dialog replies remain available. Avoid conflicting instructions
from multiple AIs or a human editing the same document simultaneously.

## Workspaces and existing documents

Default: `spb_open_session` launches private headless Chrome with a fresh document.
It does not see your unsaved document in an ordinary browser/Electron window.
Use SPB Save/Open to transfer a saved project, or explicitly attach a debugging-
enabled existing browser with `cdp_url` and its exact `page_url`. No CDP/debug port
is enabled on your personal browser or Electron automatically.

A private browser shares its configured SPB backend. Server configuration, project
storage and actual export destinations are not isolated by the browser profile.
Tests must use an audit backend. Native server-side Windows file dialogs are blocked
in private sessions; the Shokker picker, direct app APIs and HTML uploads work without
desktop focus. OS-only Electron functions require attachment to that Electron app
with its preload API available; they are not invented in a plain Chrome session.

`visible:true` opens a review window when wanted. Closing a private session discards
unsaved document state, so save first. Closing an attached session removes MCP event
listeners and leaves the existing browser tab open. Artifacts remain on disk.

## Efficient operation

Read `spb://guide` once. Use targeted `spb_controls` searches and batch actions.
After importing, wait for the actual source readiness (`#btnRender:not([disabled])`)
before painting. Project dialogs also open asynchronously. A submitted action is
not evidence that a render/save completed. Inspect the resulting file/state.
Pixel arrays stay in Chrome; checkpoints return hashes. Large script results become
local JSON files, fetched in slices only when necessary. Screenshots are opt-in.
No specific token-saving percentage has been measured.

## Verification

```powershell
python tests/spb_mcp_protocol_smoke.py
python tests/spb_mcp_http_smoke.py
```

Tests use the real MCP client protocol and the isolated SPB backend, not direct
calls to Python tool functions. Evidence is under `_tools_simplification_work/mcp/`.
The stdio test imports two-layer ORA, makes a real Brush stroke, verifies exact Undo,
renames a Layer, saves a project, answers a native prompt, downloads a source PNG,
receives an MCP image, runs asynchronous JS and checks partial-batch failure.
The HTTP test rejects missing/wrong tokens and connects two independent clients.
These are representative integration proofs, not an exhaustive audit of every finish
or app workflow. No SPB installer build or production server restart is included.

References: [MCP server concepts](https://modelcontextprotocol.io/docs/develop/build-server),
[tested official Python SDK version](https://github.com/modelcontextprotocol/python-sdk/tree/v1.25.0).
