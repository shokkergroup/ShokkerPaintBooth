# Chat intent and document boundaries — private59910, 2026-10-09

The Full Editor chat needs to distinguish discussion, proposed choices and authorized edits. A phrase containing a colour or finish is not automatically an editing request. A remembered design discussion is historical evidence, not an executable plan.

`design-intent.js` supplies a common bounded request contract to Offline routing, Full Editor Send and `spb_assistant_context.request_intent`. Advice-only messages return `mutation_allowed:false`. A finite Offline answer covers black/gold contrast, matte/satin, retained blue/white marks and no glitter. It explicitly answers from the description rather than claiming to see the paint. Other design questions get basic principles and the connected-helper route; this is not general model reasoning. An explicit later editing command stays outside the heuristic advice gate unless the message also says advice only. Protected-part commands remain editing requests.

Advice enters before option, complaint and editing parsers. It clears stale builder steps and suppresses Paint by Numbers placement choices and the builder's editing CTA. The first native test caught those independent controls even though the chat bubble was already correct. The final native question has one advice card, no placement/Run/Build-it controls and unchanged Undo history.

The connected relay also needs a server boundary. The private protocol uses:

- `POST /api/mcp/document`: a page UUID plus monotonic epoch. No paint path, artwork or login credential is included. Successful source commits advance the epoch; failed loads preserve it. Repeated registration is idempotent; delayed earlier registrations are refused.
- Inbox messages carry the current `document_scope`. Source changes retire queued/inflight messages and cancel queued tool calls. Authenticated conversation reads and browser polls expose current-document turns only.
- `spb_reply.reply_to` identifies the delivered buyer-message sequence. Missing, old or other-provider references are refused once document scoping is active. An answer acknowledges only that provider's messages through its sequence, preserving later messages.
- The browser rejects an old poll response even when it arrives after a source switch. Finish cards also carry their originating scope; an expired Use card cannot compose a new editing request.
- The MCP client retains the scope from its latest delivered app-chat message on tool requests. The server refuses that scope after a document change. A fresh buyer message rebinds the client. Advice-only messages additionally reject non-read tools in the client, including render.

Existing token, origin, enabled-bridge and editing-lease checks remain. The protocol targets one active editor page. Calls from an assistant that has never received an app-chat message still use the existing external-MCP contract; this does not prove document correlation for every outside-app command. Already executing asynchronous edits need their own document stamps, and the full async write audit remains open. Do not infer cancellation of every operation from cancellation of a queued call.

Evidence:

- `test_design_advice.cjs`: actual Offline claim and Full Editor Send, mixed question/command and protected-part cases; zero model/network/edit calls.
- `test_relay_document_scope.py DocumentRouting`:19 actual Flask contracts, including existing provider/auth tests, history/reply isolation, registration order and queued-call cancellation.
- `test_relay_document_ui.cjs`: actual relay code with delayed transport, fresh reply, expired Use card and registration-before-send.
- Native `_codex_mcp_work/chatgpt-dev/59910/native-design-advice.json/.png` and `native-relay-scope-ui.json/.png`.
- Actual MCP transport receipt `native-relay-scope-2026-10-09T21-18-25-456Z.json`: native A→B switch, advice write refusal, A reply/tool scope refusal, fresh B state/reply. This uses a controlled transport fixture, not language-model inference or API credits.

Promote the narrow patches together, preserving newer source-owner changes. Production module paths, explicit manifests and the session prompt must be updated coherently. The private development/research tree should not ship. Source-owner Claude must adopt the `reply_to` contract in its connected MCP client; the same backend/browser rules apply to both providers. No request or message was sent to Linear.

Actual reopened-discussion ChatGPT reasoning now passes: `context-session-probe-2026-10-09T21-23-41-022Z.json`. A fresh ChatGPT-authenticated process recovered retained blue/white marks, no glitter and the earlier satin-gold proposal from the saved brief, then refined it without repeating the constraints in the question. Four read/chat tools, exit0, no API fallback and no editing tools. Native reply: `reopened-model-discussion.json/.png`. Claude inference parity is still untested.

One native flat-colour edit→settled preview→chat Undo now passes; see `COLOUR_EDIT_ACCEPTANCE.md`. It exposed and repaired S3 colour-scope, guessed denominator and delayed-document-check defects. Unknown coverage is reported as preview coverage, never guessed car area. Remaining acceptance: layered protected edits, full-resolution output, post-reopen actions, layered failed-open/rollback, all asynchronous editing paths and supported customer setup/wake-up.
