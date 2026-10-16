# Saved project discussion — private candidate, 2026-10-09

Customers need their design discussion to accompany a saved project. The implementation stores exact customer quotes and assistant proposals, then exposes them to the online context and Offline Helper. It does not infer an approved brief from a proposal.

## Existing authorities

- `spbProAI.log()` owns the visible conversation; this module reads it.
- `SpbConvo` owns live offers, target resolution, pending questions and action/Undo state. Saved discussion does not replace or hydrate that live state.
- `SPBSourceLoadTransaction` owns committed source identity and rollback.
- `SPBProjects` owns project serialization and verified source/layer/config restore. Its `projectId` identifies a saved envelope and is regenerated on save; it is not treated as a stable ID across all versions of a named project.

## Private implementation

`design-brief.js` uses schema `spb-design-brief/1`. The optional `assistantBrief` field in a `.spbproj` has the same project ID as its enclosing payload. Saving another version binds a fresh copy to that new envelope. The existing backend preserves this field and still calculates the source fingerprint itself.

The module keeps at most60 turns and24,000 text characters. Individual text excerpts are capped at4,000 characters and marked; omitted turns are counted. It retains short opening instructions and recent turns within the budget, including recent corrections. Online context receives a smaller bounded historical view. Optional descriptive `design_proposals` on assistant turns now preserve the actual Offline alternatives, original request and constraints. An allowlist excludes arbitrary target/queue/approval fields. Descriptions count toward both the24,000-character save budget and8,000-character context budget. It never saves image payloads, masks, queues, executable option arguments, target IDs or Undo IDs. The source path is used only for local session isolation, not copied into the brief.

Successful source commits clear the previous document's saved discussion and establish a new chat boundary. Failed source loads do not clear it. Project open captures the in-memory discussion state before source load; successful verified project restore attaches only the matching envelope's discussion. A successful rollback restores the previous discussion, while an incomplete rollback leaves it detached. Legacy unverified projects, unknown schemas and mismatched project IDs do not restore notes. The existing Forget notes action also clears the current discussion for subsequent saves. Old saved files are not rewritten by forgetting.

The private Offline route recognizes questions about the saved brief and shows bounded buyer quotes plus the last assistant proposal, explicitly marked as unapproved. It also lists saved structured directions and constraints. Ordinal explanation questions can read the latest saved proposal, labelled historical, without restoring live option state or accepting an edit. It returns no actions. `spb_assistant_context.saved_design_brief` makes the same historical evidence available to connected assistants even when a large paint snapshot is omitted.

The Full Editor shows **Recall saved discussion** and **Forget saved discussion** when notes are attached. Recall enters the existing Offline front door with its typed-input marker, or goes to the connected assistant. Its card does not link to an unrelated encyclopedia article. Forget detaches the current notes for future saves; existing saved files remain unchanged.

## Live document isolation

`conversation-scope.js` is a separate in-memory lifecycle coordinator. It resets existing stores rather than competing with `SpbConvo`: Full Editor legacy history/options/Versions, Offline pending/topic/list state, builder steps, Paint by Numbers text/picks/cache/timers and the intent planner. Successful source commits, including same-source reloads, expire those references. Failed loads preserve them. A direct committed-path/fingerprint change is also caught before a message or state read.

Tool closures and their queues receive an in-memory document stamp. Old tool calls/queues and delayed ask results reject after a switch; the actual warm/model completion path cannot repopulate the new document's history. Durable buyer notes and confirmed car-map learning remain intact. A failed reset is visible and blocks stamped tools. Successful rollback restores discussion quotes as historical evidence without restoring live targets, old action buttons, Versions or Undo IDs.

Native testing also found Paint by Numbers retained the old question and palette because counts alone did not identify the document. Its dedicated reset clears the old reader cache and timer; the final native A→B check shows an empty question, no old Run button, and wine/gold suggestions for the red/gold fixture.

Private project testing additionally stages a narrow `v5_entrypoint_security.py` correction: the V5 guard now resolves the same default project directory as `project_routes`. The normal default is unchanged; private storage overrides are checked against the existing owned-output policy. Tests still reject external project and finish-pack writes. No guard is disabled.

`SPB_DESIGN_BRIEF_OFF` disables capture, restore and recall. Source boundaries still invalidate stale notes while disabled. The existing CX1/CX2 and newer1.4.2 MCP work is preserved.

## Exact proposed integration

- `candidates/spb-pro-ai.js.patch`: observe source identity before messages, include saved discussion in state, clear it with Forget notes.
- `candidates/spb-offline-answer.js.patch`: read-only recall response through the existing answer-card path.
- `candidates/paint-booth-3-canvas.js.patch`: one observer in the successful structured source-result boundary; no painting math or dispatch changes.
- `candidates/spb-projects.js.patch`: optional brief serialization, verified restore and transactional rollback hooks, clear save/open toast text.
- `assistant-context.cjs`: separately bounded saved discussion, alongside existing live conversation state.
- `conversation-scope.js` and `candidates/spb-pbn.js.patch`: source coordinator plus the existing Paint by Numbers store's dedicated reset. Existing stores remain authoritative.
- `candidates/v5_entrypoint_security.py.patch`: resolve the same project storage location as the routes, while preserving the owned-output guard.

The private server serves these candidates only on59910 and isolates its project library under `_release_evidence/chatgpt-dev/59910/projects`. Do not copy private launchers/research directories into the installer. The source owner must merge the narrow patches into current source and add production-owned module paths to the normal runtime manifest.

## Evidence and remaining acceptance

Passed:

- `node mcp/chatgpt/test_design_brief.cjs`: project/source isolation; verified reopen; same-source reload; successful and failed rollback; bounded first/latest quotes; disabled/re-enabled state; Forget notes; actual staged project serializer, source-result and rollback functions; actual Offline recall with zero actions.
- `python mcp/chatgpt/test_design_brief_persistence.py`: real project routes write/read the discussion exactly in temporary files, and changed source bytes still fail fingerprint verification.
- `node mcp/chatgpt/test_assistant_context.cjs`: live options/pending approval/Undo and saved historical discussion survive omission of oversized paint state.
- `node mcp/chatgpt/test_conversation_scope.cjs`: actual Full Editor, Offline, Paint by Numbers and source-boundary modules; stale offers/Undo/Versions expire; old closures/queues and delayed model-path results reject; failed loads preserve state; reset failure blocks execution. Test transport performs no paid model call or paint mutation.
- `python mcp/chatgpt/test_private_project_guard.py`: actual V5 guard and project routes allow only owned test output, continue denying external storage and unrelated external writes.
- Existing cold-index, car identity and article-action tests remain passing.
- Native Full Editor Save/Open verified a28KB disposable flat-paint project with exact quotes and matching envelope ID, then restored its source fingerprint and recalled historical notes through the Offline card. Forget removed the current attached notes; later recall reported their absence. Source A→B cleared the chat, question and Run button. Evidence under private59910: `native-project-discussion-recalled.png`, `native-conversation-reset.json`, `native-conversation-reset.png`. No real customer project library was listed or written.
- The corrected Recall button passes native acceptance. `node mcp/chatgpt/car-knowledge/probe_mcp.cjs --live --expect-saved-brief` also reads the restored historical quotes through the actual MCP server, with no old executable change and an explicit unresolved car for the synthetic paint. Receipt: `car-knowledge-live-context-2026-10-09T21-02-10-385Z.json`.
- Real fresh ChatGPT subscription reasoning now passes from the native reopened project's brief: `context-session-probe-2026-10-09T21-23-41-022Z.json` and `reopened-model-discussion.json/.png`. The new question did not repeat the constraints; the model recovered blue/white marks and no glitter, then refined the gold proposal through read/chat tools only.

Still unproven:

- Native failure/rollback across layered documents and every asynchronous editing path; the flat-file lifecycle evidence does not prove those cases.
- Provider-server transcript/late-reply scoping now passes native + actual MCP transport checks in `CHAT_INTENT_AND_SCOPE.md`; complete already-running async edit isolation is still open.
- Advice-only routing now passes private native acceptance in `CHAT_INTENT_AND_SCOPE.md`; broader arbitrary design questions still require connected-model testing.
- Contradictory historical instructions, omitted-context recovery and Claude reasoning parity remain untested despite the successful reopened ChatGPT case.
- Actual protected layered edits, full-resolution changes and exact Undo after reopening a project. One flat-fixture native edit/preview/exact Undo now passes separately (`COLOUR_EDIT_ACCEPTANCE.md`); it was not the post-reopen layered acceptance.

The saved discussion is a useful foundation, not a claim that a model has inferred all customer intent or that a saved proposal authorizes an edit.
