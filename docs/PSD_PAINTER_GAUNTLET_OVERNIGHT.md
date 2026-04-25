# PSD Painter Gauntlet Overnight

This shift succeeds only if a painter can load a PSD template into Shokker Paint Booth and credibly stay inside SPB for real work.

Do not impress with volume.
Impress with trust, correctness, tool feel, workflow parity, and sustained execution.

## Mission

Turn Shokker Paint Booth into a true PSD-template painting workstation:

- Photoshop-like layer behavior
- trustworthy paint tools
- predictable selections
- solid text/shape workflows
- real preview/render trust
- performance that holds up under actual painting
- regression protection that proves the gains

## Shift Rules

This is a 6+ hour shift, not a sprint.

- No final report before the final 30 minutes.
- If one lane is complete, immediately pull the next lane.
- If blocked, report the blocker in one short line and move within 5 minutes.
- Do not farm easy structural tests while obvious user-facing tool gaps remain.
- Do not drift into finishes/catalog/build-system churn unless blocked on tool work.
- Do not pre-credit backlog items from prior sessions unless re-verified tonight.
- Every completed task number must include proof:
  - code path changed, or
  - behavioral test added, or
  - manual acceptance note, or
  - doc/checklist artifact created

## Product Standard

Ask this constantly:

"If a painter imported a real PSD at 2 AM, what would still make them bounce back to Photoshop?"

Fix that next.

## The Heenan Family

### Agent Heenan
CEO / Chief Architect / integrator / final verifier

Owns:
- scope control
- delegation
- anti-idle enforcement
- integration
- conflict resolution
- heartbeat reporting
- final report honesty

### Agent Flair
The technician

Owns:
- hardest correctness work
- layer/tool/selection semantics
- subtle parity bugs
- "why does this feel wrong?" logic

### Agent Windham
The workhorse

Owns:
- tool-by-tool consistency sweeps
- repetitive correctness cleanup
- guardrails
- fixing every similar bug once the pattern is known

### Agent Luger
The total package

Owns:
- full-stack blocker relief
- cross-file fixes
- integration support
- taking over whatever is most urgent

### Agent Sting
The visible one

Owns:
- tool feel
- cursor feedback
- action clarity
- painter confidence
- UX that makes features feel real

### Agent Hawk
Road Warrior frontend/perf

Owns:
- canvas responsiveness
- tool latency
- paint-loop performance
- preview invalidation discipline

### Agent Animal
Road Warrior backend/perf

Owns:
- render/preview parity
- heavy-path profiling
- payload efficiency
- server-side workflow trust

### Agent Bockwinkel
The professor

Owns:
- tool audit matrix
- acceptance criteria
- regression net
- fact-checking agent claims
- ranked findings

### Agent Pillman
The loose cannon

Owns:
- adversarial sequences
- weird user behavior
- rapid input chaos
- breaking assumptions

### Agent Street
The exotic specialist

Owns:
- one high-value painter wow-feature only after core trust is healthy

### Agent Raven
Cleanup and simplification

Owns:
- remove sprint noise
- tighten naming/comments/docs
- make tomorrow easier

## Mandatory Shift Order

1. PSD Painter Gauntlet audit
2. Tool-by-tool trust matrix
3. Tool behavior normalization
4. Layer/tool/selection interoperability
5. PSD-template workflow hardening
6. Running-app acceptance proof
7. Performance under real painter workflows
8. Regression expansion
9. One high-value workflow enhancement only if healthy
10. Cleanup and handoff

## Heartbeat Format

Use this exact structure:

```text
[HH:MM] Heenan Family heartbeat
Done:
- Heenan: ...
- Flair: ...
- Windham: ...
- Luger: ...
- Sting: ...
- Hawk: ...
- Animal: ...
- Bockwinkel: ...
- Pillman: ...
- Street: ...
- Raven: ...

Completed tasks:
- #123 proof: ...
- #124 proof: ...

In progress:
- ...

Next tasks:
- #...
- #...

Files:
- E:\Koda\Shokker Paint Booth Gold to Platinum\...

Verification:
- ...

Risks:
- ...
```

## Final Report Format

1. What shipped
2. What was verified
3. What is only structurally guarded
4. What still needs manual proof
5. What remains risky
6. Best next sprint

## PSD Painter Gauntlet Checklist

The app should eventually pass all of these in reality, not just on paper:

- Import a real PSD template
- Paint on the base layer
- Paint on a named sponsor layer
- Paint on a hidden layer and understand what is happening
- Refuse paint on a locked layer
- Fill a selection on the active layer
- Delete a selection on the active layer
- Recolor only the selected layer
- Clone only the selected layer
- Smudge only the selected layer
- Use eyedropper from composite and current layer
- Transform a layer and undo in one step
- Duplicate a styled layer and keep styles
- Merge down a styled layer and bake styles correctly
- Restrict a zone to a source layer and trust the result
- Preview and render must agree
- Save, reload, and continue without broken state

## TWENTY WINS shift (2026-04-19) — gauntlet items closed structurally

| Item | Status | Win # | Proof |
|---|---|---|---|
| Refuse paint on locked layer | ✓ structurally guarded | #4 polish, #5 | flipLayerH/V, rotateLayer90 CW/CCW, knockoutLayer all toast and bail when layer.locked |
| Restrict zone to source layer (delete-layer scenario) | ✓ shipped | #10 | deleteLayer now confirms + scrubs zones[*].sourceLayer (closes silent-restriction-loss bug) |
| Free Transform Esc / Enter / Ctrl+Z precedence | ✓ structurally guarded | #1 | All 32 keydown listeners bail on defaultPrevented; Free Transform owns Esc/Enter/Ctrl+Z via stopImmediatePropagation |
| Transform a layer + Ctrl+Z restores in one step | ✓ verified clean | #4 audit | Single _pushLayerUndo per commit, marathon's 180° single-step intact |
| Preview matches state for selection moves / spatial mask edits | ✓ shipped | #8 | spatialMask added to preview hash; duplicateZone now fires triggerPreviewRender |
| Preview matches state when 2nd/3rd/4th/5th base placement is flipped | ✓ shipped | #19 | secondBasePatternFlipH/V (and 3rd/4th/5th) now serialized to engine |
| Browser does not lie about audit flags | ✓ shipped | #14 | FINISH_BROWSER_QUALITY_FLAGS rebuilt from fresh 2026-04-18 audit (0 broken/slow/ggx; 16 genuine spec_flat) |
| Finish-data drift catches itself on boot | ✓ shipped | #18 | validateFinishData() enhanced (phantom + cross-registry + duplicate-name + spec-pattern checks); auto-runs |
| Right-click "Select All" pushes undo, fires preview | ✓ shipped (marathon #61) | — | _ctxSelectAll routes through pushZoneUndo + triggerPreviewRender |
| Layer-panel does not execute crafted-PSD layer-name JS | ✓ shipped (marathon #68) | — | renderLayerPanel escapes l.name/l.path/l.groupName via escapeHtml |
| Render gallery does not execute crafted note/tag JS | ✓ shipped (marathon #69) | — | buildGalleryHTML escapes entry.tags/notes/zones_summary |
| PSD-import endpoint refuses non-.psd path traversal | ✓ shipped (marathon #70) | — | All 3 PSD routes call _sanitize_path + enforce .psd extension |
| Painter releasing mouse outside canvas commits stroke | ✓ shipped (marathon #74) | — | Document mouseup proxy + window blur safety net |

## Items still requiring manual painter proof (running app)

These are STRUCTURALLY GUARDED but not running-app verified tonight:

1. Open a real PSD template (Heatwave / Coulby / SimWrap) — every layer rasterizes, names match, fx baked correctly.
2. Click a sponsor layer, choose Recolor, drag — only that layer's pixels change.
3. Lock a layer, try every quick-button (flip H, rotate 90, knockout) — all toast and bail.
4. Restrict a zone to a layer, delete the layer — confirm dialog appears, sourceLayer cleared, zone paints whole car after Confirm.
5. Toggle 2nd-base placement flip H — preview renders the flip immediately.
6. Open finish browser — pearl / chrome_wrap / antique_chrome no longer show "Audit: Broken" chip; obsidian / liquid_titanium / platinum show "Audit: Flat Spec".
7. Open devtools console — `validateFinishData()` runs on boot, surfaces drift counts.
8. Painter selects a finish, paints, then closes the tab within 500ms — autosave flushes synchronously (marathon #72).
9. Painter releases mouse outside canvas mid-stroke — stroke commits cleanly (marathon #74).
10. Painter does any global Ctrl+Z while Free Transform is active — transform cancels, no double-undo (Win #1).

## Tool Audit Matrix To Build And Maintain

Every major tool should be scored for:

- layer-local behavior
- selection behavior
- hidden-layer behavior
- locked-layer behavior
- no-layer fallback behavior
- symmetry behavior
- brush size behavior
- opacity behavior
- hardness behavior
- flow behavior
- spacing behavior
- cursor fidelity
- undo behavior
- redo behavior
- preview fidelity
- render parity
- PSD-template usability
- regression coverage
- acceptance status

## Backlog

### Track A: Core Tool Trust

1. Audit brush tool start behavior.
2. Audit brush tool move behavior.
3. Audit brush tool end behavior.
4. Audit eraser start behavior.
5. Audit eraser move behavior.
6. Audit eraser end behavior.
7. Audit recolor start behavior.
8. Audit recolor move behavior.
9. Audit recolor end behavior.
10. Audit smudge start behavior.
11. Audit smudge move behavior.
12. Audit smudge end behavior.
13. Audit clone start behavior.
14. Audit clone move behavior.
15. Audit clone end behavior.
16. Audit history brush start behavior.
17. Audit history brush move behavior.
18. Audit history brush end behavior.
19. Audit dodge start behavior.
20. Audit dodge move behavior.
21. Audit dodge end behavior.
22. Audit burn start behavior.
23. Audit burn move behavior.
24. Audit burn end behavior.
25. Audit blur brush start behavior.
26. Audit blur brush move behavior.
27. Audit blur brush end behavior.
28. Audit sharpen brush start behavior.
29. Audit sharpen brush move behavior.
30. Audit sharpen brush end behavior.
31. Audit pencil start behavior.
32. Audit pencil move behavior.
33. Audit pencil end behavior.
34. Verify brush undo label clarity.
35. Verify eraser undo label clarity.
36. Verify recolor undo label clarity.
37. Verify smudge undo label clarity.
38. Verify clone undo label clarity.
39. Verify history brush undo label clarity.
40. Verify dodge/burn undo label clarity.

### Track B: Layer-Local Behavior

41. Verify color brush edits only selected layer.
42. Verify eraser edits only selected layer.
43. Verify recolor edits only selected layer.
44. Verify smudge edits only selected layer.
45. Verify clone edits only selected layer.
46. Verify history brush edits only selected layer.
47. Verify pencil edits only selected layer.
48. Verify dodge edits only selected layer.
49. Verify burn edits only selected layer.
50. Verify blur brush edits only selected layer.
51. Verify sharpen brush edits only selected layer.
52. Verify no-selected-layer fallback is explicit.
53. Verify hidden-layer painting feedback is clear.
54. Verify locked-layer painting is refused.
55. Verify invisible selected layer does not silently alter composite semantics.
56. Verify layer-local undo after one dab.
57. Verify layer-local undo after long stroke.
58. Verify layer-local redo after one dab.
59. Verify layer-local redo after long stroke.
60. Verify switching selected layer mid-session is safe.

### Track C: Selection Interop

61. Rect selection + fill on active layer.
62. Rect selection + delete on active layer.
63. Lasso selection + fill on active layer.
64. Lasso selection + delete on active layer.
65. Ellipse selection + fill on active layer.
66. Ellipse selection + delete on active layer.
67. Wand selection + fill on active layer.
68. Wand selection + delete on active layer.
69. Select-all-color + fill on active layer.
70. Select-all-color + delete on active layer.
71. Edge-detect selection + fill on active layer.
72. Edge-detect selection + delete on active layer.
73. Selection fill on composite when no editable layer exists.
74. Selection delete on composite when no editable layer exists.
75. Selection survives layer reorder.
76. Selection survives layer visibility toggle.
77. Selection survives sourceLayer changes.
78. Selection-to-new-layer-via-copy with rect.
79. Selection-to-new-layer-via-copy with lasso.
80. Selection-to-new-layer-via-copy with wand.

### Track D: Eyedropper / Sampling

81. Verify normal eyedropper samples composite.
82. Verify Shift+eyedropper samples current layer.
83. Verify current-layer eyedropper on transparent pixel.
84. Verify current-layer eyedropper with transformed layer bbox.
85. Verify current-layer eyedropper with hidden layer.
86. Verify current-layer eyedropper with locked layer.
87. Verify current-layer eyedropper on styled layer.
88. Decide and document whether effects are included in current-layer sample.
89. Add test for composite-vs-layer divergence.
90. Surface sample source in UI text.

### Track E: Brush Controls

91. Audit brush size honoring by color brush.
92. Audit brush size honoring by eraser.
93. Audit brush size honoring by recolor.
94. Audit brush size honoring by smudge.
95. Audit brush size honoring by clone.
96. Audit brush size honoring by history brush.
97. Audit brush size honoring by pencil.
98. Audit brush size honoring by dodge.
99. Audit brush size honoring by burn.
100. Audit brush size honoring by blur brush.
101. Audit brush size honoring by sharpen brush.
102. Audit opacity honoring by every paint-like tool.
103. Audit hardness honoring by every paint-like tool.
104. Audit flow honoring by every paint-like tool.
105. Audit spacing honoring by every paint-like tool.
106. Disable dead controls for tools that ignore them.
107. Add UI hints for partially supported controls.
108. Normalize slider reads through shared helpers if safe.
109. Add tests for top 5 tool-control contracts.
110. Document unsupported control semantics intentionally.

### Track F: Cursor / Feedback

111. Audit cursor for brush.
112. Audit cursor for eraser.
113. Audit cursor for recolor.
114. Audit cursor for smudge.
115. Audit cursor for clone.
116. Audit cursor for eyedropper.
117. Audit cursor for fill.
118. Audit cursor for gradient.
119. Audit cursor for text.
120. Audit cursor for shape.
121. Audit cursor for dodge/burn.
122. Audit cursor for blur/sharpen.
123. Audit cursor for selection tools.
124. Surface active target more clearly.
125. Surface source-layer restriction more clearly.
126. Surface “locked” tool-block reason more clearly.
127. Surface “hidden layer” paint warning more clearly.
128. Avoid toast spam while keeping trust high.
129. Add subtle persistent status instead of per-dab spam.
130. Add tests for target label refresh hooks.

### Track G: PSD Template Workflow

131. Import a sponsor-heavy PSD fixture.
132. Import a multi-group PSD fixture.
133. Import a hidden-layer-heavy PSD fixture.
134. Import a styled-layer PSD fixture.
135. Import a giant PSD fixture.
136. Verify selected layer persists after import completion.
137. Verify visibility toggles before full rasterize are preserved.
138. Verify reorder after import works.
139. Verify restrict-to-layer after import works.
140. Verify active painting after import works.
141. Verify effects editing after import works.
142. Verify merge-down after import works.
143. Verify flatten after import works.
144. Verify sourceLayer references survive import replacement cleanly.
145. Verify deleted layer references fail safely.
146. Verify renamed layer references remain ID-based and safe.
147. Verify duplicate names do not confuse sourceLayer routing.
148. Verify reload of same PSD does not orphan state.
149. Build a fixture pack for nightly checks.
150. Write a PSD-template acceptance ladder.

### Track H: Text / Shape / Sponsor Workflows

151. Verify text layer creation undo.
152. Verify text layer creation redo.
153. Verify text layer commit on Enter.
154. Verify text layer cancel on Esc.
155. Verify text layer locked guard.
156. Verify shape layer creation undo.
157. Verify shape layer creation redo.
158. Verify shape layer locked guard.
159. Verify add outline refuses locked layer.
160. Verify center-on-canvas refuses locked layer.
161. Verify fit-to-canvas refuses locked layer.
162. Verify transform refuses locked layer.
163. Verify duplicate styled sponsor keeps styles.
164. Verify mirror clone sponsor keeps intended properties.
165. Decide whether mirror clone should inherit lock state.
166. Verify sponsor ops preview invalidation.
167. Verify sponsor ops undo labels feel right.
168. Add behavioral proof where possible.
169. Improve sponsor workflow toasts only if high signal.
170. Add one sponsor-specific acceptance fixture.

### Track I: Layer Effects as Painter Workflow

171. Verify opening effects dialog without edit is no-op.
172. Verify first edit creates effects bag lazily.
173. Verify repeated slider drags coalesce to one undo step.
174. Verify close dialog triggers preview refresh.
175. Verify clear-all-effects undo.
176. Verify duplicate layer copies effects.
177. Verify mirror clone copies effects.
178. Verify merge-down bakes effects correctly.
179. Verify merge-visible bakes effects correctly.
180. Verify flatten bakes effects correctly.
181. Verify effect badge accuracy after edit.
182. Verify effect badge accuracy after clear.
183. Verify effect badge accuracy after duplicate.
184. Verify effect badge accuracy after merge.
185. Verify drop shadow edge cases.
186. Verify stroke edge cases.
187. Verify outer glow edge cases.
188. Verify color overlay edge cases.
189. Verify bevel edge cases.
190. Add one real running-app effect checklist.

### Track J: Transform / Move / Reorder

191. Verify layer drag move undo.
192. Verify layer drag move redo.
193. Verify transform commit undo.
194. Verify transform commit redo.
195. Verify transform cancel restores preview.
196. Verify transform panel refresh.
197. Verify reorder undo.
198. Verify reorder redo.
199. Verify selection survives reorder.
200. Verify selected row stays intuitive after delete.
201. Verify selected row stays intuitive after merge-down.
202. Verify selected row stays intuitive after flatten.
203. Verify selected row stays intuitive after duplicate.
204. Verify selected row stays intuitive after reorder.
205. Add debug logging only where it materially helps.
206. Remove noisy transform logs if overdone.
207. Add acceptance notes for move/transform trust.
208. Test fast Ctrl+Z/Ctrl+Y spam after transform.
209. Test drag then undo then drag again.
210. Test transform on styled layer.

### Track K: Preview / Render Trust

211. Verify preview matches render for plain PSD paint.
212. Verify preview matches render for layer-restricted zone.
213. Verify preview matches render after effect edit.
214. Verify preview matches render after merge-down.
215. Verify preview matches render after flatten.
216. Verify preview cache invalidates on layer visibility.
217. Verify preview cache invalidates on effect edit.
218. Verify preview cache invalidates on sourceLayer change.
219. Verify preview cache invalidates on selected layer transform.
220. Verify result card uses final outputs.
221. Verify result card after PSD import.
222. Verify result card after effect edit.
223. Verify result card after restrict-to-layer render.
224. Verify sourceLayer missing case paints nothing.
225. Verify sourceLayer missing case is user-visible.
226. Add parity diagnostics for hard cases.
227. Build one parity fixture.
228. Add tests for top preview/render parity regressions.
229. Write one human acceptance checklist for parity.
230. Re-run parity after perf work.

### Track L: Performance Under Real Painting

231. Profile `getImageData` hotspots during paint.
232. Profile `putImageData` hotspots during paint.
233. Profile `_initLayerPaintCanvas`.
234. Profile `_commitLayerPaint`.
235. Profile effect slider drags.
236. Profile preview invalidation during strokes.
237. Profile smudge under large brush.
238. Profile clone under large brush.
239. Profile recolor under large brush.
240. Profile history brush under large brush.
241. Profile dodge/burn under large brush.
242. Profile blur/sharpen under large brush.
243. Add `willReadFrequently` only where justified.
244. Remove obviously redundant full-canvas reads.
245. Reduce preview churn during slider drags if safe.
246. Reduce preview churn during rapid tool changes if safe.
247. Stress test 25-layer PSD painting.
248. Stress test 50-layer PSD painting.
249. Stress test 25-layer PSD + effects + render.
250. Ship top 3 safe perf wins.

### Track M: Chaos / Abuse

251. Paint on locked layer rapidly.
252. Paint on hidden layer rapidly.
253. Switch tools mid-stroke.
254. Switch selected layer mid-stroke.
255. Hide selected layer mid-stroke.
256. Lock selected layer mid-stroke.
257. Start transform and cancel with queued preview.
258. Open effects dialog and undo repeatedly.
259. Duplicate then merge then undo.
260. Delete then undo then redo.
261. Reimport PSD mid-session.
262. Restrict zone to deleted layer.
263. Restrict zone to hidden layer.
264. Restrict zone to transformed layer.
265. Use eyedropper during strange states.
266. Clone without source then set source then undo.
267. Use fill while selection tool remains active.
268. Use gradient while selection tool remains active.
269. Hit Ctrl+Z/Ctrl+Y in fast sequence after layer ops.
270. Report only reproducible failures.

### Track N: Running-App Acceptance Proof

271. Build one manual smoke flow for PSD import.
272. Build one manual smoke flow for active-layer paint.
273. Build one manual smoke flow for hidden-layer warning.
274. Build one manual smoke flow for locked-layer refusal.
275. Build one manual smoke flow for fill/delete on active layer.
276. Build one manual smoke flow for eyedropper current-layer sample.
277. Build one manual smoke flow for duplicate styled layer.
278. Build one manual smoke flow for merge-down styled layer.
279. Build one manual smoke flow for restrict-to-layer.
280. Build one manual smoke flow for render parity.
281. If feasible, script browser-based smoke.
282. If feasible, script Electron smoke.
283. Capture screenshots for 3 key flows.
284. Capture before/after for one bug fix.
285. Produce a “must manually verify” list.
286. Produce a “scripted enough to trust” list.
287. Produce a “still only structurally guarded” list.
288. Tie acceptance items back to code/tests.
289. Keep the list brutally honest.
290. Re-run after major tool fixes.

### Track O: Regression Net

291. Add truly behavioral test for eyedropper current layer.
292. Add truly behavioral test for locked-layer stroke refusal.
293. Add truly behavioral test for hidden-layer warning throttle.
294. Add truly behavioral test for pencil hard-edge footprint.
295. Add truly behavioral test for fill/delete target routing.
296. Add truly behavioral test for sourceLayer missing empty-mask chain.
297. Add truly behavioral test for transform undo roundtrip.
298. Add truly behavioral test for merge-down visibility refusal.
299. Add truly behavioral test for effect lazy-init state machine.
300. Add truly behavioral test for duplicate-styled-layer semantics.
301. Add structural tests only where behavior is hard to simulate.
302. Keep tests small and named by contract.
303. Avoid bloating with low-signal source grep tests if a behavior test is possible.
304. Tighten old brittle assertions where easy.
305. Add one decision-table test for all brush target gates.
306. Add one decision-table test for selection target gates.
307. Add one decision-table test for eyedropper sample-source choices.
308. Add one decision-table test for sponsor op lock guards.
309. Re-run full suite after each meaningful package.
310. Keep runtime sync clean.

### Track P: UI Clarity

311. Show active layer/composite target clearly.
312. Show source-layer restriction clearly.
313. Show lock-block reason clearly.
314. Show hidden-layer paint warning clearly.
315. Show current eyedropper sample source clearly.
316. Show fill/delete target clearly.
317. Show transform mode clearly.
318. Show layer-effects session clearly enough.
319. Improve tool label without clutter.
320. Improve tooltip language for Photoshop-familiar users.
321. Improve merge-down tooltip semantics.
322. Improve flatten tooltip semantics.
323. Improve duplicate styled layer tooltip.
324. Improve sourceLayer tooltip.
325. Improve sponsor op toasts if useful.
326. Avoid per-dab spam.
327. Keep language short and painter-friendly.
328. Add tests for any new helper logic.
329. Verify labels stay in sync on state changes.
330. Re-check after cleanup.

### Track Q: Tool-Specific Deep Dives

331. Clone source visualization.
332. Clone offset trust.
333. Clone with transformed target layer.
334. Clone with hidden selected layer.
335. Clone with locked selected layer.
336. Smudge accumulation behavior.
337. Smudge reset behavior.
338. History brush snapshot trust.
339. History brush with layer-local edits.
340. Dodge/burn exposure feel.
341. Blur/sharpen edge handling.
342. Recolor tolerance feel.
343. Pencil versus brush differentiation.
344. Gradient on layer versus composite.
345. Fill bucket on layer versus composite.
346. Text commit/cancel semantics.
347. Shape commit/cancel semantics.
348. Pen path to mask trust.
349. Magic wand tolerance trust.
350. Edge-detect selection usefulness.

### Track R: Cleanup / Handoff Quality

351. Remove stale sprint comments if misleading.
352. Remove duplicate comments that overclaim.
353. Fix handoff docs to match current test counts.
354. Fix handoff docs to match current B5 status.
355. Fix handoff docs to match current backlog closure honestly.
356. Make acceptance doc match actual code behavior.
357. Keep the docs shorter than the logs.
358. Leave breadcrumbs for next shift.
359. Mark unverified claims explicitly.
360. End cleaner than the shift started.

## Overflow Backlog

If all of the above is healthy and verified, continue here instead of idling.

### S1: Photoshop-Adjacency Enhancements

361. Add eyedropper sample-source toggle in UI.
362. Add current-layer/all-layers sampling label.
363. Add “contiguous” option where relevant.
364. Add “sample merged” semantics where useful.
365. Add layer-only fill shortcut if valuable.
366. Add one-step duplicate-and-transform workflow.
367. Add quick sponsor outline presets.
368. Add quick sponsor knockout workflow.
369. Add compare-current-layer vs composite helper.
370. Add one-click center/fit combo for decals.

### S2: Painter QoL

371. Add recent colors persistence audit.
372. Add swatch trust audit.
373. Add harmony picker trust audit.
374. Add brush preset persistence audit.
375. Add smoothing/stabilizer persistence audit.
376. Add one “working on current layer” persistent hint.
377. Add one “sample source” persistent hint.
378. Add one “zone restricted to X layer” persistent hint.
379. Add one “preview stale/pending” subtle indicator if needed.
380. Add one “locked layer” status chip if needed.

### S3: Brush Engine Enhancements

381. Actually wire smoothing into stroke flow if safe.
382. Actually wire stabilizer into stroke flow if safe.
383. Add tests for smoothing integration.
384. Add tests for stabilizer integration.
385. Ensure smoothing respects symmetry if used.
386. Ensure stabilizer respects symmetry if used.
387. Ensure smoothing does not break undo grouping.
388. Ensure stabilizer does not break undo grouping.
389. Profile smoothing impact.
390. Profile stabilizer impact.

### S4: Advanced Painter Acceptance

391. Full car-side sponsor workflow.
392. Full number-layer workflow.
393. Full striping workflow.
394. Full color-swap logo workflow.
395. Full contingency cleanup workflow.
396. Full pitboard edit workflow.
397. Full windshield banner workflow.
398. Full metallic/spec workflow paired with PSD paint.
399. Full export and in-game spot-check checklist.
400. One "paint a car start to finish in SPB" walkthrough.

## Starting Orders

1. Build tonight's tool trust matrix from actual code, not assumptions.
2. Pull the highest-risk painter-facing tool gaps first.
3. Keep running through the backlog for the full shift.
4. No early victory.
5. No idle time.
