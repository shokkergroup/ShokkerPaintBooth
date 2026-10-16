# Use your ChatGPT subscription with SPB

**Current acceptance (Oct10):** protected native layer recolour passes Offline Helper, one ChatGPT-plan conversation, independent 512px fixture output and native Undo. Exact boundaries and remaining real-car, setup/reconnect and packaged-delivery gaps are in [REPORT.md](REPORT.md) and [SMARTER_AI.md](SMARTER_AI.md). The older zone-based checkpoint in `LAYERED_EDIT_ACCEPTANCE.md` is historical; its partial-alpha limitation must not be treated as current native-overlay evidence.

The first connection uses your installed Codex assistant, signed in with ChatGPT, and SPB's existing local MCP bridge. You can ask that assistant to receive messages from SPB's chat box and send its answers back there. SPB supplies the tools and chat interface; Codex runs the assistant using your eligible ChatGPT plan.

This uses your plan's allowance. It does not provide unlimited usage or an extra allowance. Do not choose API-key authentication for this setup.

## Start a session

1. Install Codex and Node.js. Sign into Codex with ChatGPT. Choose an account-supported model in Codex.
2. In SPB, use **Connect ChatGPT / Codex** to add SPB's local MCP connection. Enable the AI bridge. Keep one SPB page open.
3. Finish the current Claude session before switching assistants. In SPB's AI panel choose ChatGPT/Codex. In your Codex chat, paste the contents of [start-app-chat.txt](start-app-chat.txt).
4. Wait for the assistant's connection reply in SPB, then type in SPB's chat box. Keep Codex running. Say stop when finished.

The existing setup gives SPB tools a 200-second timeout; the session prompt waits for messages for 170 seconds per call. A wait uses no model generation while the local tool is blocked, but repeated timeout/continuation turns can still use plan allowance. An actual subscription-backed chat exchange has passed in the isolated development app. Editing, Undo, cold setup and reliable wake-up still need buyer acceptance.

SPB's pairing token stays on your PC. Codex manages its own ChatGPT login. Paint previews and requested tool results are sent to your chosen assistant.

## ChatGPT itself and direct sign-in inside SPB

Ordinary ChatGPT web chat requires its own custom MCP connection. That is a separate transport and setup from local Codex. A successful MCP connection alone does not prove that messages in SPB can wake a ChatGPT conversation.

OpenAI also offers **Sign in with ChatGPT** with optional ChatGPT-plan usage for eligible requests inside another app. Commercial access currently requires approval. SPB must obtain that access before shipping a direct subscription-backed sign-in integration; identity-only sign-in does not grant inference access. See [OpenAI's quickstart](https://developers.openai.com/siwc/quickstart).

For current evidence and unresolved checks see [REPORT.md](REPORT.md). Shared UI/bridge requests belong in [REQUESTS_FOR_CLAUDE.md](REQUESTS_FOR_CLAUDE.md).

The Full Editor conversation improvements and next acceptance steps are in [SMARTER_AI.md](SMARTER_AI.md). The private candidate adds recent-discussion recovery, current capabilities and relevant SPB knowledge through `spb_assistant_context`. Saved project discussion and native Save/Open/recall/Forget are documented in [DESIGN_BRIEF.md](DESIGN_BRIEF.md); fresh ChatGPT subscription reasoning from reopened notes now passes. Advice intent and provider-document isolation pass private native/MCP transport checks in [CHAT_INTENT_AND_SCOPE.md](CHAT_INTENT_AND_SCOPE.md). One disposable flat-colour edit/preview/exact chat Undo passes in [COLOUR_EDIT_ACCEPTANCE.md](COLOUR_EDIT_ACCEPTANCE.md). Layered protected editing, full-resolution output, post-reopen actions, Claude inference parity and all async write paths remain separate gates; these are private candidates.

## Development preflight and installation mismatch

The owned probe supports `--preflight-only`: it reads login status and reports authenticated but not listening, with model access unverified. It starts no inference. API login or configuration failure stops before launching the model. `--subscription-isolated --context --messages 1 --model <account-supported model>` tests one actual private59910 reply with only wait/context/reply tools and ephemeral isolated client configuration. Supply the intended installed executable through `--codex`; do not assume the PATH installation matches the desktop app.

Oct10 native evidence: PATH0.124.0 rejects the desktop config/model; installed app0.162.0-alpha.2 succeeds on the same queued question/account. A temporary supported service-tier override is explicit and does not rewrite customer configuration. This remains a development probe, not a customer launcher or unattended listener. See REPORT for exact receipts and limitations.

## Development only

Codex's private test server is `http://127.0.0.1:59910/paint-booth-v2.html`. Launch it with `python mcp/chatgpt/dev_server.py --port 59910 --candidate-routing` after building the candidates. It uses a private pairing token, config and output tree and refuses ports outside59910–59999. Never point this lane at the owner's59876. Candidate source copies and the bounded session probe are review/test tools, not installer contents. See the Living Wiki Oct9 entry for shared findings and lane ownership.


2026-10-11 06:30UTC — Prepared-browser shipment snapshot:598 hash-verified physical files/50.7MB,366 script tags, all16 helper loads explicitly before the real AI caller;16 syntax checks and Offline reference shipment gate PASS. Compiled car articles and matching manifest included; accepted private project/source callbacks retained. Full browser dependency gate BLOCKED by pre-existing absent js/finishes/user-import-car-preview.js. Native execution of this snapshot, installer and online inference remain NOT_RUN. No shared code installation, model calls, API credits or new project saves. Next: physical-file59910 host without helper injection, then native lifecycle acceptance. See [review](prepared-browser/README.md).


2026-10-11 06:33UTC — Physical frontend acceptance PASS on59910/PID88416: prepared HTML and365 available unique scripts served with inventory hash headers, no HTML injection/development JS fallback. Native FW31 template answer/official policy source, paintability follow-up, chat reset, hidden duplicate and disabled unrun builder observed. Eight paint/identity fields, visible preview SHA, layer DOM, History0 and two project hashes unchanged. Backend and large assets still use isolated existing fixtures; this is not a full installer/online acceptance. Physical-mode failure/draft/document replacement remain open. Natural overview gap reproduced: Tell me about the Williams FW31 falls back despite supported template answer. Next: broaden source-backed exact-car overview intent without authorizing edits or inventing template facts. [Evidence](prepared-browser/native-proof.json).


2026-10-11 06:41UTC — Natural car overview and complete published browser knowledge accepted privately on59910/PID257476. 1350 component cases PASS:768 sourced overviews/all192 cars,572 unchanged identity lookups,2 ambiguous families, 6 mixed-edit refusals and unknown/stale guards. Native natural FW31/short SRX/ambiguous Ferrari and follow-up checks PASS; eight paint fields, preview, History0 and original two fixtures preserved. Shipping gap found: Electron baseline has zero Encyclopedia JSON; initial browser snapshot had only six overlays. Added378 published JSON from frozen fresh-install payload while preserving six accepted overlays;976 files/384 published JSON now hash/parse/actual-serving verified. No drafts copied, API/model calls or new project saves. Initial proofs/three changed files preserved. Missing baseline car-preview script, source-owner adoption, physical failure/draft/document-replacement, full installer and signed-in online acceptance remain open. Next: physical-mode retrieval failure/retry and retained-draft lifecycle. [Overview evidence](body-output-consistency/car-overview/native-proof.json).


2026-10-11 06:53UTC — Physical missing-index natural-question bug reproduced and fixed privately on59910/PID67652. Before: car JSON503 made Tell me about the Williams FW31 receive unrelated-to-SPB dismissal. After:192-name synchronous identity hints recognise the car question without claiming facts ready; real fact lookup reaches retryable failure and recovers. 768 pre-fact recognition +768 unchanged indexed-answer cases/4 guards PASS; repaint mixed-edit guard added. Native delayed failure and success both preserve newer drafts; recovered source card stays accessible. Seven private fixture scope checks/eight payload gate checks PASS. Physical977-file/17-helper/384-JSON shipment hash/parse/actual serving verified. Eight paint fields/preview/History0/two original fixtures unchanged; control restoredfalse/0. No API/model calls/new saves/shared code install. Document replacement, source adoption/full installer/online and baseline missing car-preview remain open. Next: physical changed-document/stale-reply lifecycle. Current native evidence: prepared-browser/name-bootstrap/native-proof.json. Static verification labels do not run native tests; separate native proof supersedes the proposal’s initial NOT_RUN marker.


2026-10-11 07:04UTC — Physical changed-document native acceptance PASS/PID67652: during8-second car read, opened existing512²/3-layer protection project from2048²/42-layer ARCA. Old reply rejected with document-changed/resend note; newer draft retained through replacement and restoration. MCP independently measured42→3→42 layers. Seven paint fields, live/MCP preview hashes and History0 restored; two original saved files unchanged, no new saves. Identity intentionally changed through verified saved-project Open (including restored project configuration): original ARCA PSD SHA matches inspected reference, while current artwork/UV remain unverified. Native Which car template is this? now identifies ARCA Chevrolet SS by verified original-source SHA256 and states saved artwork may differ/UV positions unverified. Control normalfalse/0. No API/model calls/shared installation. Next: fresh installed-MCP context retrieval should convey this source proof, actual editable roles and geometry limits to subscription-backed assistants; source adoption/full installer/online inference and baseline absent car-preview dependency remain open.
