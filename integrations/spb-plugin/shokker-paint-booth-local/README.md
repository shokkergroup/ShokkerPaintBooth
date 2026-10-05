# Shokker Paint Booth Local Pilot 0.1.0

Private test package for a local Codex host. It bundles SPB-specific painting
instructions and an exact snapshot of the existing dependency-free Node MCP
adapter. The bridge performs the work in your installed SPB application.

This is a pilot, not a public-directory release or an embedded editor. SPB's
existing Connect Codex setup remains the currently documented buyer route.

## Requirements

- Windows with a compatible local Codex host and Node.js available as `node`.
- A purchased, running SPB installation in Pro mode.
- The assistant bridge enabled in SPB's AI panel settings.
- The host must support local plugins and bundled stdio MCP processes. Local
  plugin availability varies by client; installing on the web does not install
  or execute software on your PC.

The adapter defaults to port 59876 and reads the existing per-user SPB pairing
token. For another port, pass `SPB_PORT` through the host's supported MCP
configuration. Never include a buyer token in a shared plugin package.

## Test installation

Use the target local host's supported plugin/source installation flow with the
`shokker-paint-booth-local` directory. Host-specific directory/ZIP installation
must be checked in that host; this source archive is not a universal installer.
Use either this plugin's MCP connection or the existing manual/Connect Codex
entry for a session so the assistant has one clear SPB connection. Review any
existing configuration before changing it; this package does not remove entries.

Start with: "Using Shokker Paint Booth, inspect my current car and suggest a
livery using real finishes from its catalog." Confirm status and actual preview
images before asking for paint changes. Select an image-capable model in Codex;
model availability and subscription usage follow the buyer's account and client.

Full schemes require a longer tool timeout than many clients' defaults. The
existing SPB setup uses 200 seconds; apply a supported server timeout override
if the plugin host provides one. This manifest does not force approval policies.

## Scope and limits

- Local stdio MCP and instructions are included. No HTTPS endpoint, buyer OAuth,
  device relay, hosted renderer, MCP App UI or file-handler extension is included.
- ChatGPT web/mobile access to the buyer's local SPB is not established by this
  package. A separate supported connection and production service are required.
- Known app acceptance gaps are recorded in the architecture document: preserving
  repainted colors in spec-only edits, composer cleanup and clean-profile/Electron
  validation must be rechecked against current app fixes before buyer release.
- Protocol discovery proves the package starts and advertises real tools. It
  does not prove every painting workflow or host installation works.

`BUILD_PROVENANCE.json` records the source hashes. Rebuild with the adjacent
`build_plugin.py` whenever the production adapter or generated tools change;
do not hand-edit the copied adapter. The builder checks source stability and
validates portable manifests against the official Agent Plugins schemas.

Official packaging guidance:
[Package your plugin](https://developers.openai.com/plugins/build/plugins).
