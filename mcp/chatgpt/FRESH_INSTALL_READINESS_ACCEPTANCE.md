# Fresh-install knowledge and runtime readiness

Review candidates, not installed features. This extends [fresh-install knowledge delivery](FRESH_INSTALL_KNOWLEDGE_ACCEPTANCE.md). A customer's subscription supplies the model; the installed SPB update supplies versioned app knowledge. No development repository, API key or remembered conversation is required by this design.

## What changed

The existing Codex setup considered a PATH Node executable and `mcp/server/index.js` sufficient. The staged setup additionally verifies a local knowledge manifest, exact content hashes, readable car/help data, delivery of the complete app briefing through the actual context builder and entry syntax with the selected runtime. Missing, changed, disabled or unreadable knowledge disables both installation and Copy config; a failed recheck clears the earlier config. Configured, knowledge-ready, signed-in and listening states are not interchangeable.

An installed customer need not install Node separately when the current packaged SPB runtime passes verification. Selection prefers an explicitly bundled Node, then the current app's Electron executable, then verified PATH Node. The Electron parent supplies its own executable privately to its Python child; the resolver checks the exact installed layout and enabled RunAsNode fuse before a hidden bounded version probe. It never searches other SPB installations. The real knowledge check also runs JavaScript, which catches missing V8 resources that `--version` alone misses.

Generated config, manual command and knowledge probe share the selected runtime/environment. Electron runs with `ELECTRON_RUN_AS_NODE=1`; inherited Node preload/module settings are cleared. Existing unrelated Codex settings and entries remain preserved. An existing different SPB entry still requires the current manual review flow; this patch does not silently rewrite it. The manual CLI command requires applying the documented TOML timeout values afterward; the visible UI copies the complete TOML.

## Measured proof

- Fourteen focused setup tests pass: valid knowledge, changed/missing/invalid data, outside paths, disabled delivery, runtime absence, timeout/malformed output, config preservation/idempotence, shared runtime environment and invalid entry syntax even with a consistent manifest. Six adapted existing config/guard tests and twelve resolver tests also pass. Tests write only local config fixtures.
- Actual candidate UI logic passes controlled-fetch checks for initial failure and a failure discovered again at installation time. This is a component test, not native UI acceptance.
- The exact V10 10.0.3 release executable, SHA256 `e8e7973965b0326848e8d01dddcf67a3dfddc7d1fb635529af44a16869eecf50`, runs as Node20.18.3 with its same-release DLL/ICU/V8 resources. In an isolated candidate install layout, the actual setup function selects it with PATH Node unavailable, validates412 knowledge files and creates the correct config payload. All413 install files, including the manifest, remain unchanged. No owner config is installed.
- A separate guarded release-runtime process initializes the actual candidate MCP and lists38 tools. It denies outside-install reads, network, writes and child processes. No tool action or model call is performed.
- Knowledge counts:192 exact-car records,291 facts and384 Encyclopedia JSON files. These are delivery/integrity counts, not a claim that every car's geometry or every app feature is known.
- Parent combined stage adds the reviewed Offline data and duplicate-identity successor without overwriting earlier proof files. The same release executable selects successfully with no PATH Node, passes412 file checks and entry syntax. Separately, fourteen actual Full Editor route output cases pass in a VM; native installation remains open.

## Exact adoption order

1. Adopt the reviewed source knowledge/context/delivery and distribution closure from the linked knowledge acceptance document. Keep the previous frozen proofs as historical evidence.
2. Review `fresh-install/readiness/candidates/`: patches for `server_routes/codex_setup.py`, `js/spb-codex-setup.js` and the one Electron Python-child environment hook. Install `codex_knowledge.py` and `codex_runtime.py` into `server_routes/`. Do not replace a concurrently changed large file with a whole old candidate.
3. Install `knowledge-health.cjs` under `mcp/server/`. Generate `mcp/runtime-knowledge-manifest.json` from the final runtime bytes. It contains only install-relative paths, hashes and versions; never package absolute developer paths. Recompute after reviewed knowledge or runtime changes. The current generator targets the frozen private closure and is a reproducible review fixture, not a universal release build command.
4. Add these required files to packaging/sync, then rebuild and test the extracted installer/MCPB. Run the knowledge checker and real MCP initialization with the exact released executable. A hash manifest detects drift; it is not a cryptographic signature or proof that the content is correct.
5. Verify a new customer from the actual AI/settings entry: no separate PATH Node, no repository, signed-in subscription, current context, preserved drafts, provider-limit fallback and supported action/Undo receipts. Native Claude parity and full installer acceptance remain open.

Primary receipts: `fresh-install/readiness/review-manifest.json` binds29 artifacts and21 external review artifacts; `fresh-install/combined-review/proof.json` records the final data overlay. Independent review found and verified fixes for Copy-config bypass and unchecked entry syntax. [Compact adoption path](FRESH_INSTALL_ADOPTION.md). Tests use59910 only. Shared sources remain unchanged; no API credits, new SPB project saves or invented UV mapping.
