# Fresh-install SPB intelligence

The owner’s priority is that a new customer connects an existing subscription and immediately receives useful SPB knowledge without the development repository or this chat history. Claude already supplies the generated1.4.7 knowledge pack. This work reuses and corrects that pack, makes delivery repeatable, and checks that its installed dependencies actually exist.

## Customer delivery contract

1. Ship the generated app briefing, verified operating facts, local Encyclopedia and compiled exact-car references with the app update. Keep the source manuals in one maintained location; customers consume the generated runtime files.
2. MCP initialization tells a fresh client to retrieve context. Put the essential sequence in the first512 characters. The in-app subscription worker also requires fresh context before accepting a reply; model memory is not the delivery mechanism.
3. Every `spb_assistant_context` read returns the complete bounded `app_knowledge` separately from search articles, current-document capabilities and conversation. It includes a content hash, server version and delivery-policy version. A previous read, reconnect or fresh model worker cannot consume it permanently.
4. Relevant verified corrections repeat on Encyclopedia reads and take precedence over conflicting historical articles. Current measured capabilities and action receipts govern current-file/action claims. Knowledge is useful operating guidance, not permission or proof of geometry.
5. Generate Online and Offline guidance from the same corrected canonical sources. The Offline Helper uses its local retrieval and supported deterministic actions; it does not acquire unrestricted model conversation merely by receiving documentation.

[OpenAI’s MCP documentation](https://developers.openai.com/plugins/build/mcp-server) supports initialization instructions alongside tool metadata and recommends putting essential cross-tool guidance first. The concrete repeated context packet is SPB’s implementation, not a guarantee that every external client will obey an instruction.

## Concrete defects and candidate fixes

- Original context parsing joined encyclopedia JSON with an appended once-only briefing. JSON parsing failed and prose was clipped to4,500 characters. The owned reader now preserves independently parseable result blocks; the app briefing has its own16,000-character budget and explicit unavailable/oversized states.
- Once-only correction suppression could leave a repeated query saying articles must never be contradicted. Delivery revision2 uses stateless specific-before-broad facts and qualifies response rules/tool metadata. Deliberately stale article tests preserve corrections across two reads.
- The pack said every car had known parts and that two logos should use the most prominent. Eighteen exact source corrections require verified loaded geometry, explicit duplicate identity, honest stored-material semantics, exact template/check-date/file identity and requested-render evidence. All23 existing facts are retained; four focused facts are added. The corrected head is2,040 characters.
- Sixteen additional reviewable corrections across three Online/Offline knowledge cards address current Foundation recipes, clearcoat direction, mode capabilities, geometry and actual Undo history. Their shared source/index adoption remains open.

## Measured evidence

- Delivery handoff: two independent mock MCP processes/four context turns; reconnect, search failure, complete briefing, version movement and exact rollback. Original12 artifacts remain frozen.
- Parent private59910 read-only probe: three context reads after another tool consumed the original briefing; structured articles and complete10,457-character original briefing retained,0 paint reads/models.
- Quality bank: original pack supports10/15 delivery rubrics,11/15 with actual private Encyclopedia retrieval; corrected candidate supports15/15. These counts measure delivered propositions, **not model success rates**.
- Final clean candidate stage: `fresh-install/packaging/stages/candidate-20261011T034315002281Z`; twelve offline Node checks plus the actual local Encyclopedia search pass. Access to outside source files/modules and network is denied.192 cars/291 facts,38 tools,385 embedded browser knowledge chunks and skill references resolve locally.
- Parent release gate independently checks411 runtime files and204 compiled-car inputs; no stale/missing source hashes. The inspected current shipped mirror and existing MCPB fail the richer closure checks. This is a staged installation layout, not a built installer.
- Actual fresh ChatGPT-plan Codex worker outside the repository, with project instruction loading disabled and an ephemeral session: one model turn, three context reads, five reviewed question checks pass. The model chose context retrieval from MCP initialization without the test prompt teaching the sequence or answers. It handled scheme constraints, duplicate identity, unknown geometry, stored template date/open-file limits and separate paint-pattern Opacity/Spec controls. Controlled transport explicitly withheld loaded paint. `verify_fresh_model.py` verifies the worker and71 frozen helper artifacts. The earlier repository-nested probe is excluded from this count. No native in-app Send/action/Undo proof is implied.

## Exact review and adoption

`fresh_install_edits.py` + `build_candidates.py` stage the shared MCP index patch. Owned `assistant-context.cjs` now includes the parser/packet slot; exact prior native-tested bytes were archived without re-freezing historical model evidence.

Canonical knowledge changes: `fresh-install/quality/candidate/{knowledge_src.cjs,CORE_BRIEFING.md}.patch`; generated candidate `app-knowledge.cjs`. Additional source-card patches: `fresh-install/quality/docs-review/`. Delivery implementation/precedence: `fresh-install/delivery/` and its frozen `review/` lane.

Release review: `fresh-install/packaging/distribution-closure.json`, `runtime-sync-additions.json`, `verify_distribution.py`. Rebuild the MCP bundle and installer after reviewed promotion, then verify the extracted artifacts and actual buyer startup. Do not replace current Claude source with an old whole candidate.

Successor: the exact released V10 executable now passes real knowledge/MCP startup probes, and staged setup selects it without PATH Node. Fourteen new setup tests, six existing config/guard tests and twelve runtime tests pass; install and Copy remain disabled on failed knowledge or entry-syntax checks. Both Offline index paths were followed: current Full Editor data corrections plus identity advice pass fourteen output cases; legacy geometry/capability/advice display gaps remain. The combined private stage preserves the earlier model/package receipts. [One adoption path](FRESH_INSTALL_ADOPTION.md).

Remaining gates: Claude/shared adoption, full canonical Online/Offline rebuild, built installer/MCPB closure, automatic customer lifecycle, native Claude parity, provider-limit fallback and supported action/Undo behavior. Verified released-binary capability does not mean these new files ship in the current installer. No API credits, external posts, new SPB project variants or UV-map invention.
