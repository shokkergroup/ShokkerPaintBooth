# Exact-car suggestion acceptance

Private localhost59910, Oct10 23:21EDT. Exact reviewable changes are in `reference_suggestion_edits.py`; shared Claude-owned source remains untouched. Rebuild with `build_candidates.py` and review the three candidate patches against current source before adoption.

`SpbOfflineAnswer.filterReferenceArticles` reuses the common car selector. A definite asked-car identity filters unrelated `cars.reference.*` hits. Legacy `car_pages.*` cards use only an explicit article/summary paint folder when available. This removes the misleading dirt-folder “Mini Stock: parts and folder” card from asphalt questions; it does not validate that article's geometry. General help/ideas remain. Ambiguous families and comparisons retain alternatives; unknown model codes suppress car-specific suggestions. Cold/missing knowledge and `SPB_REFERENCE_SUGGESTIONS_OFF` retain previous behavior.

Both the Paint by Numbers suggestions and connected `encSearch` caller apply the same scope. Raw PBN cache is bounded to40 queries/30 lightweight hits per query and re-filtered before display limits, so an early unscoped cache cannot preserve stale picks after knowledge loads. No extra fetch, model call, paint action or write retry is introduced.

Measured native acceptance:

- Asphalt Mini Stock query: asphalt reference retained; Dirt Mini Stock and the dirt-folder legacy card omitted; general template guidance retained.
- Dirt Mini Stock query: dirt reference/explicit dirt-folder legacy page retained; asphalt reference omitted. Switching back to the cached asphalt query remains scoped.
- One actual Offline Send answers with the inspected asphalt PSD and stored HTTP check, retaining latest-version/compatibility/UV limits.
- Eight exposed paint fields and both original reusable fixture hashes remain exact; zero model inference, API use or new saved-project variants.

`test_reference_suggestions.cjs` tests the actual generated filter/PBN/connected callers using192 real car-reference records, explicit legacy folder, unknown model, ambiguity, cold/warm caches, cache bound and feature flag. `verify_reference_suggestions_native.py` binds14 artifacts, including exact frozen generated source bytes. Screenshots/receipts are under `_codex_mcp_work/chatgpt-dev/59910/`; original wrong-card evidence comes from the prior transport snapshot, not a fresh same-session baseline.

Open: native connected-provider/installed/package adoption; legacy card title still omits “Dirt”; unmapped legacy pages retain prior search behavior. A separate common identity defect resolves “Mini Stock vs Dirt Mini Stock” to dirt alone because variant modifiers and containment are applied across the whole query. The suggestion comparison guard prevents hiding search alternatives; it does **not** fix comparison answers. Resolve independent named mentions before extending comparison claims. Geometry/calibrated UV acceptance remains separate.
