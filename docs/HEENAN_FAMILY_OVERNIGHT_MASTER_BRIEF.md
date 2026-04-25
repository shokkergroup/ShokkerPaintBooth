# Heenan Family Overnight Master Brief

This file is the single source of truth for a long-running autonomous Claude sprint on Shokker Paint Booth.

Use this when you want Claude to work overnight with one coordinator agent delegating to named subagents.

The intent is simple:

- keep the work real
- keep the work moving
- prevent early victory laps
- ensure the app is measurably better by morning

## Top-Line Command

```text
Do not impress me with volume; impress me with correctness, integration, proof, and sustained execution.

This sprint succeeds only if Shokker Paint Booth feels more trustworthy, faster, and more painter-friendly by morning.
```

## Master Prompt For Claude

```text
Do not impress me with volume; impress me with correctness, integration, proof, and sustained execution.

This sprint succeeds only if Shokker Paint Booth feels more trustworthy, faster, and more painter-friendly by morning.

You are Agent Heenan, CEO / Chief Architect of the Heenan Family, running a full overnight autonomous engineering sprint on Shokker Paint Booth.

Mission:
Improve the PSD layer system, zone system, paint tools, preview/render consistency, performance, and painter workflow trust.

What success means:
- PSD layers stack and behave more like Photoshop
- tools feel more consistent and predictable
- preview and full render agree more often
- layer/effect operations are safer and more undoable
- performance is improved in real hotspots
- tests and acceptance proof expand alongside the fixes

What does NOT count as success:
- inflated change count
- random catalog churn
- broad unrelated cleanup
- ending the sprint early because one workstream landed
- a final report that is longer than the actual shipped value

Hard rules:
- No final report before the final 30 minutes unless every approved workstream is either complete or explicitly blocked.
- When one workstream is stabilized, immediately pull the next highest-value numbered task from the backlog.
- Every heartbeat must include completed task numbers and the next task numbers.
- Prefer 5 strong wins over 50 shallow edits.
- Do not revert unrelated user work.
- Do not drift into finish-catalog expansion unless explicitly assigned late in the sprint.

The Heenan Family:

Agent Heenan:
- coordinator
- architect
- backlog owner
- integration lead
- verification lead
- heartbeat owner

Agent Flair:
- the technician
- longest and hardest correctness work
- layer/render/undo semantics
- subtle bugs with hidden risk

Agent Windham:
- the workhorse
- grind fixes
- consistency sweeps
- bug clusters

Agent Luger:
- floating full-stack support
- blocker relief
- integration support
- can absorb any role temporarily

Agent Sting:
- visible UX and workflow polish
- quick user-facing wins
- interaction feel

Agent Hawk:
- frontend/perf combat
- heavy-impact tactical fixes

Agent Animal:
- backend/engine/perf combat
- heavy-impact tactical fixes

Agent Street:
- exotic and unique work
- one high-wow prototype lane only after stability tracks are healthy

Agent Bockwinkel:
- professor
- audit
- acceptance criteria
- regression coverage
- evidence and fact-checking

Optional:
Agent Pillman:
- adversarial tester
- chaos monkey
- assumption breaker

Agent Raven:
- cleanup
- simplification
- final-phase battlefield cleanup

Sprint timing:
- Phase 1: first 45 minutes = audit, assign ownership, start execution
- Phase 2: deep parallel execution
- Phase 3: integration and conflict resolution
- Phase 4: acceptance, verification, and handoff in the final 30 minutes

New operating rule:
- Never end the sprint after one completed vertical slice.
- Continue pulling from the numbered backlog for the entire session.

Escalation rule:
If a worker hits a real product-risk decision, escalate to Heenan with:
- issue
- options
- recommendation
- impact if wrong

Heartbeat format:
[HH:MM] Heenan Family heartbeat
Done:
- Agent Heenan: ...
- Agent Flair: ...
- Agent Windham: ...
- Agent Luger: ...
- Agent Sting: ...
- Agent Hawk: ...
- Agent Animal: ...
- Agent Street: ...
- Agent Bockwinkel: ...
- Agent Pillman: ...
- Agent Raven: ...

Completed tasks:
- #...
- #...

In progress:
- ...

Next tasks:
- #...
- #...

Files:
- E:\Koda\Shokker Paint Booth Gold to Platinum\...

Risks:
- ...

Verification:
- ...

Use the approved workstream order and numbered backlog in docs/HEENAN_FAMILY_OVERNIGHT_MASTER_BRIEF.md.
```

## Operating Doctrine

### Core Principles

- keep the backlog moving
- do not declare victory after one theme
- ship things users can trust
- back claims with tests, diagnostics, or acceptance evidence
- be honest about what is still unverified

### Approved Workstream Order

Pull from these in order unless blocked:

1. Running-app acceptance proof
2. Layer effects hardening
3. Effect rendering edge cases
4. Non-source-over behavior
5. Layer undo/redo completion
6. Layer tool consistency
7. Tool option consistency
8. Restrict-To-Layer edge cases
9. Preview/render parity
10. Performance audit
11. Preview responsiveness
12. PSD import/layer lifecycle
13. Layer panel correctness
14. Selection pipeline
15. Spatial mask and layer interop
16. Render result fidelity
17. Diagnostics and debug modes
18. Stress testing
19. UI clarity
20. Acceptance documentation
21. Playwright/Electron automation
22. Exotic prototype
23. Bockwinkel audit lane
24. Pillman chaos lane
25. Raven cleanup lane

### Assignment Defaults

- Heenan owns scope, delegation, integration, and final verification.
- Flair gets the hardest correctness path first.
- Windham gets broad fix sweeps and consistency passes.
- Luger floats to unblock and integrate.
- Sting gets visible workflow friction and polish.
- Hawk and Animal tag-team performance and cross-stack issues.
- Street gets one exotic lane only after the core stability tracks are healthy.
- Bockwinkel audits, designs acceptance criteria, and grows the regression net.
- Pillman attacks assumptions and weird edge cases.
- Raven cleans and simplifies late in the sprint.

### Definition Of Done

The sprint is only truly done if:

- the app is measurably more trustworthy than at the start
- the Family kept pulling from the backlog for the full session
- key fixes are verified, not just claimed
- final handoff clearly separates shipped, verified, unverified, and deferred work

## Workstream Guide

### Workstream 1: Running-App Acceptance Proof

Intent:
Prove the real app behaves correctly, not just the source tree.

Suggested owners:
- Heenan
- Bockwinkel
- Sting

Expected outcomes:
- a real acceptance checklist
- one reproducible smoke path
- real fixture files
- app-level confidence

### Workstream 2: Layer Effects Hardening

Intent:
Make effects behave like first-class document state.

Suggested owners:
- Flair
- Heenan

Expected outcomes:
- safer effect editing
- safer merge and flatten behavior
- cleaner undo semantics

### Workstream 3: Effect Rendering Edge Cases

Intent:
Catch clipping, ordering, and baking issues before users do.

Suggested owners:
- Flair
- Bockwinkel
- Pillman

### Workstream 4: Non-Source-Over Behavior

Intent:
Make styled layers on unusual blend modes less surprising.

Suggested owners:
- Flair
- Animal

### Workstream 5: Layer Undo/Redo Completion

Intent:
Close the remaining document-history holes.

Suggested owners:
- Flair
- Windham

### Workstream 6: Layer Tool Consistency

Intent:
Make paint-like tools obey the same mental model.

Suggested owners:
- Windham
- Sting

### Workstream 7: Tool Option Consistency

Intent:
Make tool settings trustworthy and explain when they are not used.

Suggested owners:
- Windham
- Sting

### Workstream 8: Restrict-To-Layer Edge Cases

Intent:
Push the layer-local matching system into awkward real-world territory.

Suggested owners:
- Flair
- Bockwinkel
- Pillman

### Workstream 9: Preview/Render Parity

Intent:
Make preview, render, and export paths align more closely.

Suggested owners:
- Flair
- Animal

### Workstream 10: Performance Audit

Intent:
Find the real hotspots and ship safe wins.

Suggested owners:
- Hawk
- Animal
- Bockwinkel

### Workstream 11: Preview Responsiveness

Intent:
Reduce stale, duplicate, or wasted preview work.

Suggested owners:
- Hawk
- Sting

### Workstream 12: PSD Import/Layer Lifecycle

Intent:
Make imports and late-arriving rasterized layers safer and more predictable.

Suggested owners:
- Windham
- Luger

### Workstream 13: Layer Panel Correctness

Intent:
Keep the panel state honest after operations.

Suggested owners:
- Sting
- Windham

### Workstream 14: Selection Pipeline

Intent:
Make selections behave consistently across layers and operations.

Suggested owners:
- Windham
- Flair

### Workstream 15: Spatial Mask And Layer Interop

Intent:
Verify mask systems compose instead of fight each other.

Suggested owners:
- Flair
- Animal

### Workstream 16: Render Result Fidelity

Intent:
Make the render result cards reflect reality and not stale sources.

Suggested owners:
- Sting
- Luger

### Workstream 17: Diagnostics And Debug Modes

Intent:
Give the team better visibility into tricky failures.

Suggested owners:
- Bockwinkel
- Raven

### Workstream 18: Stress Testing

Intent:
Find the pain points under heavy PSD/layer loads.

Suggested owners:
- Hawk
- Animal
- Pillman

### Workstream 19: UI Clarity

Intent:
Reduce user confusion around active target and destructive actions.

Suggested owners:
- Sting
- Raven

### Workstream 20: Acceptance Documentation

Intent:
Leave a usable checklist behind, not just a memory of the sprint.

Suggested owners:
- Bockwinkel
- Heenan

### Workstream 21: Playwright/Electron Automation

Intent:
Get at least one real running-app smoke path into repeatable automation.

Suggested owners:
- Bockwinkel
- Luger
- Sting

### Workstream 22: Exotic Prototype

Intent:
Ship one Shokker-only "holy shit" workflow boost if the core tracks are healthy.

Suggested owners:
- Street
- Sting

### Workstream 23: Bockwinkel Audit Lane

Intent:
Keep the Family honest and keep surfacing the next real issue.

Suggested owners:
- Bockwinkel

### Workstream 24: Pillman Chaos Lane

Intent:
Stress weird interaction sequences and adversarial workflows.

Suggested owners:
- Pillman

### Workstream 25: Raven Cleanup Lane

Intent:
Leave the codebase and handoff cleaner than the brawl left it.

Suggested owners:
- Raven

## Full Numbered Backlog

### Workstream 1: Running-App Acceptance Proof

1. Build a reproducible PSD fixture set for manual and app smoke checks.
2. Build a minimal "numbers over base paint" overlap PSD fixture.
3. Build a blended-layer PSD fixture.
4. Build a styled-layer PSD fixture.
5. Build a large 20+ layer PSD fixture.
6. Define transform undo acceptance steps.
7. Define restrict-to-layer acceptance steps.
8. Define merge-down-with-effects acceptance steps.
9. Define duplicate styled layer acceptance steps.
10. Define flatten acceptance steps.
11. Define preview-vs-render acceptance steps.
12. Define export-to-Photoshop acceptance steps.
13. Script launch and load flow if possible.
14. Script PSD import if possible.
15. Script transform action if possible.
16. Script Ctrl+Z and Ctrl+Y if possible.
17. Capture before and after screenshots automatically if possible.
18. Write acceptance checklist markdown.
19. Write "known non-automated checks" list.
20. Produce one canonical acceptance runner.

### Workstream 2: Layer Effects Hardening

21. Verify drop shadow survives duplicate.
22. Verify outer glow survives duplicate.
23. Verify stroke survives duplicate.
24. Verify bevel survives duplicate.
25. Verify color overlay survives duplicate.
26. Verify drop shadow survives mirror clone.
27. Verify stroke survives mirror clone.
28. Verify merge-down bakes lower effects correctly.
29. Verify merge-down bakes upper effects correctly.
30. Verify merge-visible bakes multiple effect stacks.
31. Verify flatten bakes all visible effects.
32. Verify clear-all-effects undo correctness.
33. Verify effect session redo correctness.
34. Verify close dialog without edits creates no history spam.
35. Verify open dialog without edits creates no bad state.
36. Verify effect slider drag coalesces to one undo step.
37. Verify effect checkbox toggles coalesce sensibly.
38. Verify effect color picker updates preview.
39. Verify effect opacity slider updates preview.
40. Verify effect edits invalidate thumbnails correctly.

### Workstream 3: Effect Rendering Edge Cases

41. Test large drop-shadow clipping in merge-down.
42. Test large drop-shadow clipping in merge-visible.
43. Test outside stroke clipping.
44. Test outer glow clipping on small source layers.
45. Test bevel rendering after transform.
46. Test effect rendering on tiny layers.
47. Test effect rendering on near-full-canvas layers.
48. Test multiple effects enabled together.
49. Test effect order assumptions.
50. Test transparent source with stroke only.
51. Test transparent source with glow only.
52. Test effect baking after layer opacity change.
53. Test effect baking after layer blend change.
54. Test effect baking after reorder.
55. Test effect baking after rotation.
56. Test effect baking after fit-to-canvas.
57. Test effect baking after center-on-canvas.
58. Test effect baking after rename.
59. Test effect baking after visibility toggle.
60. Write regression tests for the above high-risk cases.

### Workstream 4: Non-Source-Over Behavior

61. Verify effects on multiply layers.
62. Verify effects on overlay layers.
63. Verify effects on screen layers.
64. Verify effects on destination-out or knockout layers.
65. Verify merge-down semantics with a multiply upper layer.
66. Verify merge-visible semantics with mixed blend modes.
67. Verify preview vs render with styled multiply layer.
68. Verify opacity plus blend plus effects combination.
69. Decide intended semantics for non-source-over effects.
70. Document current behavior.
71. Normalize inconsistent effect behavior if needed.
72. Add test for multiply plus stroke.
73. Add test for overlay plus glow.
74. Add test for screen plus shadow.
75. Add test for knockout plus effects.
76. Audit renderLayerEffects assumptions.
77. Add comments where behavior is intentional.
78. Add guardrails for unsupported combos if needed.
79. Surface warning if a combo is unsupported.
80. Re-test all supported combos.

### Workstream 5: Layer Undo/Redo Completion

81. Verify transform undo.
82. Verify transform redo.
83. Verify reorder undo.
84. Verify reorder redo.
85. Verify opacity undo.
86. Verify opacity redo.
87. Verify blend undo.
88. Verify blend redo.
89. Verify delete undo.
90. Verify delete redo.
91. Verify merge-down undo.
92. Verify merge-down redo.
93. Verify flatten undo.
94. Verify flatten redo.
95. Verify duplicate undo.
96. Verify duplicate redo.
97. Verify visibility undo.
98. Verify visibility redo.
99. Verify rename undo.
100. Verify rename redo.

### Workstream 6: Layer Tool Consistency

101. Audit clone layer-local behavior.
102. Audit recolor layer-local behavior.
103. Audit smudge layer-local behavior.
104. Audit history brush layer-local behavior.
105. Audit blur brush layer-local behavior.
106. Audit sharpen brush layer-local behavior.
107. Audit dodge layer-local behavior.
108. Audit burn layer-local behavior.
109. Audit pencil layer-local behavior.
110. Audit fill layer-local behavior.
111. Audit gradient layer-local behavior.
112. Audit delete-selection layer-local behavior.
113. Audit fill-selection layer-local behavior.
114. Verify active-layer targeting message clarity.
115. Verify locked-layer behavior across all tools.
116. Verify invisible-layer behavior across all tools.
117. Verify no-selected-layer fallback behavior.
118. Verify undo labels are clear for all tools.
119. Normalize tool gating helpers.
120. Add tests for highest-risk tool-routing cases.

### Workstream 7: Tool Option Consistency

121. Audit opacity support by tool.
122. Audit hardness support by tool.
123. Audit flow support by tool.
124. Audit spacing support by tool.
125. Audit symmetry support by tool.
126. Audit cursor feedback by tool.
127. Audit preview overlay by tool.
128. Audit drag-start behavior by tool.
129. Audit tool cancel behavior by tool.
130. Audit tool-switch-mid-stroke behavior.
131. Normalize option bar visibility rules.
132. Disable irrelevant controls per tool.
133. Add UI hint when a control is ignored.
134. Fix dead spacing controls if present.
135. Fix inconsistent flow handling if present.
136. Fix symmetry bypasses if present.
137. Fix stale cursor modes if present.
138. Add tests for option consistency where practical.
139. Add manual acceptance notes for tool feel.
140. Re-run focused tool smoke checks.

### Workstream 8: Restrict-To-Layer Edge Cases

141. Test fully opaque higher layer blocking.
142. Test semi-transparent higher layer blocking.
143. Test same-color overlapping layers.
144. Test same-color identical pixels.
145. Test partially transparent source layer.
146. Test source layer with holes.
147. Test multiply source layer.
148. Test overlay source layer.
149. Test layer with effects enabled.
150. Test hidden source layer behavior.
151. Test locked source layer behavior.
152. Test deleted source layer reference.
153. Test duplicated source layer reference.
154. Test reordered source layer reference.
155. Test source layer after transform.
156. Test source layer after merge.
157. Test source layer after flatten.
158. Test source layer after visibility toggle.
159. Add diagnostics for source-layer payload.
160. Add tests for the top 5 edge cases.

### Workstream 9: Preview/Render Parity

161. Compare preview and render for a plain layer-local zone.
162. Compare preview and render for a styled source layer.
163. Compare preview and render for a transformed source layer.
164. Compare preview and render for a duplicated source layer.
165. Compare preview and render for a hidden-above-layer case.
166. Compare preview and render for semi-transparent overlap.
167. Compare preview and render for blend-mode overlap.
168. Compare preview and render for multi-color zone.
169. Compare preview and render for hard-edge zone.
170. Compare preview and render for spatial mask plus source layer.
171. Compare preview and render for export-to-Photoshop.
172. Add parity diagnostic logging toggle.
173. Add one helper to dump normalized zone payload.
174. Add one test covering parity assumptions.
175. Ensure render result card uses final render output.
176. Ensure preview cache invalidates on sourceLayer change.
177. Ensure preview cache invalidates on layer stack change.
178. Ensure preview cache invalidates on effects change.
179. Ensure preview cache invalidates on visibility change.
180. Re-test parity after perf tweaks.

### Workstream 10: Performance Audit

181. Inventory all getImageData hotspots.
182. Inventory all putImageData hotspots.
183. Inventory all full-canvas temp canvases.
184. Inventory all layer recomposite triggers.
185. Inventory all preview render triggers.
186. Audit willReadFrequently candidates.
187. Add willReadFrequently where safe.
188. Measure PSD import recomposite cost.
189. Measure transform preview cost.
190. Measure layer mask generation cost.
191. Measure effect slider drag cost.
192. Measure merge-down cost.
193. Measure flatten cost.
194. Measure duplicate styled layer cost.
195. Measure preview render cadence under rapid edits.
196. Find redundant preview renders.
197. Find redundant recomposites.
198. Find redundant thumbnail invalidations.
199. Write perf findings doc.
200. Ship the top 3 safe perf wins.

### Workstream 11: Preview Responsiveness

201. Throttle redundant preview calls.
202. Debounce effect slider preview where needed.
203. Avoid double render on closeLayerEffects.
204. Avoid double render on transform commit.
205. Avoid double render on visibility toggle.
206. Avoid double render on opacity slider.
207. Avoid double render on blend change.
208. Avoid double render on reorder.
209. Avoid double render on duplicate.
210. Avoid double render on merge.
211. Avoid double render on flatten.
212. Avoid stale pending preview after cancel.
213. Ensure the last user action wins.
214. Ensure in-flight preview results cannot overwrite newer state.
215. Add preview revision tokens if needed.
216. Add console diagnostics for dropped stale preview jobs.
217. Add perf test notes.
218. Add regression checks for preview invalidation.
219. Verify live preview remains correct.
220. Re-test under rapid UI interaction.

### Workstream 12: PSD Import/Layer Lifecycle

221. Test import of large PSD.
222. Test import while toggling layer visibility.
223. Test import while switching selected layer.
224. Test import with grouped layers.
225. Test import with hidden layers.
226. Test import with turn-off-export layers.
227. Test import with weird names.
228. Test import with empty layer.
229. Test import with fully transparent layer.
230. Test import with duplicate names.
231. Verify rasterize-all async consistency.
232. Verify no overwrite after import completes.
233. Verify visibility toggles before load persist.
234. Verify selected layer survives import updates.
235. Verify sourceLayer references survive import.
236. Verify recomposite after import is correct.
237. Add tests for the most fragile import cases.
238. Add import diagnostic logs if needed.
239. Document known import limitations.
240. Re-test with a real customer PSD.

### Workstream 13: Layer Panel Correctness

241. Verify panel updates after transform.
242. Verify panel updates after merge.
243. Verify panel updates after flatten.
244. Verify panel updates after duplicate.
245. Verify panel updates after mirror clone.
246. Verify panel updates after rename.
247. Verify panel updates after opacity change.
248. Verify panel updates after blend change.
249. Verify panel updates after effects edit.
250. Verify panel updates after visibility change.
251. Verify selected row consistency after delete.
252. Verify selected row consistency after merge-down.
253. Verify selected row consistency after flatten.
254. Verify selected row consistency after duplicate.
255. Verify selected row consistency after reorder.
256. Verify drag affordances remain correct.
257. Verify lock state affordances remain correct.
258. Verify effect badge stays accurate.
259. Add tests or assertions where practical.
260. Polish any obvious panel-state drift.

### Workstream 14: Selection Pipeline

261. Verify rect selection to layer fill.
262. Verify lasso selection to layer fill.
263. Verify ellipse selection to layer fill.
264. Verify magic-wand selection to layer fill.
265. Verify edge-detect selection to layer fill.
266. Verify select-all-color selection to layer fill.
267. Verify delete selection on active layer.
268. Verify new layer via copy from each selection type.
269. Verify selection after layer visibility changes.
270. Verify selection after reorder.
271. Verify selection after transform.
272. Verify selection after merge.
273. Verify selection after flatten.
274. Verify selection plus sourceLayer interaction.
275. Verify selection plus spatial mask interaction.
276. Add helper for active selection target semantics.
277. Add tests for fill and delete selection routing.
278. Add tests for new-layer-via-copy.
279. Document intended Photoshop parity.
280. Re-test the top 5 selection flows manually.

### Workstream 15: Spatial Mask And Layer Interop

281. Verify spatial include with source layer.
282. Verify spatial exclude with source layer.
283. Verify spatial erase with source layer.
284. Verify source layer plus region mask plus spatial mask together.
285. Verify remainder zone plus source layer behavior.
286. Verify hard-edge plus source layer behavior.
287. Verify multi-color plus source layer behavior.
288. Verify hidden layer plus spatial mask.
289. Verify transformed layer plus spatial mask.
290. Verify duplicated layer plus spatial mask.
291. Verify merged layer plus spatial mask.
292. Add regression tests for high-risk combinations.
293. Add debug visualization option for combined masks.
294. Verify preview parity for combined masks.
295. Verify render parity for combined masks.
296. Document any intentional precedence rules.
297. Surface warnings for unsupported combos if needed.
298. Clean up any ambiguous variable naming.
299. Re-test after engine changes.
300. Add to acceptance checklist.

### Workstream 16: Render Result Fidelity

301. Verify paint result card reflects final TGA-derived output.
302. Verify spec result card reflects final spec output.
303. Verify result cards after PSD import.
304. Verify result cards after layer edits.
305. Verify result cards after effects edits.
306. Verify result cards after merge.
307. Verify result cards after flatten.
308. Verify result cards after export-to-Photoshop flow.
309. Verify compare and split modes use correct sources.
310. Verify thumbnail cache invalidation for result cards.
311. Fix stale result card state if found.
312. Add tiny regression test if practical.
313. Add logging around chosen preview source.
314. Ensure no old PSD composite leaks through.
315. Verify bottom render cards match disk outputs.
316. Verify in-game workflow assumptions.
317. Add acceptance notes.
318. Clean up any fallback confusion in UI.
319. Verify with a real customer paint.
320. Re-test after perf pass.

### Workstream 17: Diagnostics And Debug Modes

321. Add layer-state dump helper.
322. Add zone-payload dump helper.
323. Add preview invalidation debug flag.
324. Add effect-session debug logging.
325. Add source-layer payload debug logging.
326. Add merge and flatten debug logging.
327. Add transform commit and cancel logging.
328. Add layer-history stack inspection helper.
329. Add selected-layer consistency logger.
330. Add performance timing logger for heavy operations.
331. Make debug toggles easy to enable.
332. Keep logs quiet by default.
333. Add docs for using diagnostics.
334. Add one "collect bug report" helper if easy.
335. Ensure diagnostics do not affect normal behavior.
336. Add tests for helper outputs if appropriate.
337. Use diagnostics to validate one tricky flow.
338. Remove noisy temporary logs.
339. Keep only high-value logs.
340. Summarize the debug toolkit.

### Workstream 18: Stress Testing

341. Create a 25-layer stress fixture.
342. Create a 50-layer stress fixture.
343. Create a styled-layer stress fixture.
344. Create a transformed-layer stress fixture.
345. Create a many-effects stress fixture.
346. Import and measure the 25-layer fixture.
347. Import and measure the 50-layer fixture.
348. Apply effects under load.
349. Reorder layers under load.
350. Merge under load.
351. Flatten under load.
352. Transform under load.
353. Restrict-to-layer under load.
354. Render under load.
355. Preview under load.
356. Watch for memory spikes.
357. Watch for stale preview.
358. Watch for undo corruption.
359. Log the worst hotspots.
360. Produce stress-test notes.

### Workstream 19: UI Clarity

361. Show active target clearly: layer vs composite vs zone mask.
362. Show when fill and delete will hit active layer.
363. Show when a tool is blocked by a locked layer.
364. Show when sourceLayer restriction is active.
365. Show when an effects session is dirty.
366. Show when preview is pending.
367. Show when preview result is stale.
368. Improve tooltips for merge and flatten semantics.
369. Improve tooltip for effect baking.
370. Improve tooltip for mirror clone semantics.
371. Improve tooltip for duplicate styled layers.
372. Improve tooltip for restrict-to-layer.
373. Improve tooltip for selection fill and delete.
374. Improve undo label clarity in UI.
375. Improve redo label clarity in UI.
376. Add subtle warnings for destructive operations.
377. Keep wording Photoshop-familiar.
378. Avoid UI clutter while clarifying behavior.
379. Verify text against actual behavior.
380. Re-test key confusion points.

### Workstream 20: Acceptance Documentation

381. Write layer-system acceptance checklist.
382. Write effects acceptance checklist.
383. Write restrict-to-layer acceptance checklist.
384. Write tool consistency checklist.
385. Write preview and render parity checklist.
386. Write PSD import checklist.
387. Write merge and flatten checklist.
388. Write transform checklist.
389. Write stress-test checklist.
390. Write performance checklist.
391. Add exact repro steps for top prior bugs.
392. Add expected vs actual columns.
393. Add screenshot placeholders.
394. Add "must pass before release" section.
395. Add "manual-only" section.
396. Add "future automation targets" section.
397. Keep docs concise enough to use nightly.
398. Link to test files.
399. Link to fixture files.
400. Publish one overnight handoff doc.

### Workstream 21: Playwright/Electron Automation

401. Evaluate if packaged app automation is feasible tonight.
402. Evaluate localhost browser automation fallback.
403. Script launch flow.
404. Script PSD import flow.
405. Script select layer flow.
406. Script open effects flow.
407. Script drag slider flow.
408. Script close effects flow.
409. Script Ctrl+Z flow.
410. Script duplicate layer flow.
411. Script merge-down flow.
412. Script flatten flow.
413. Script restrict-to-layer flow.
414. Capture before and after screenshots.
415. Add pass/fail assertions.
416. Make one minimal smoke path reliable.
417. Document flakiness limits.
418. Keep scope minimal and high-value.
419. Hook the smoke path into sprint acceptance if stable.
420. Save artifacts for review.

### Workstream 22: Exotic Prototype

421. Auto sponsor outline wizard.
422. Auto knockout generator.
423. Smart mirror-to-opposite-side workflow.
424. Fast compare variants for styled layers.
425. Auto-fit sponsor to bounding box.
426. Decal cleanup helper.
427. White-fringe reduction helper.
428. Alpha tighten helper.
429. Quick "show car" text-effect preset.
430. Quick "readable at speed" preset.
431. Quick layer-style starter pack.
432. Quick number styling pack.
433. Quick contingency cleanup pack.
434. Quick windshield banner workflow.
435. Quick pitboard workflow.
436. Pick one best prototype.
437. Implement only one tonight.
438. Add tiny test coverage if possible.
439. Add one acceptance demo path.
440. Leave the rest in the backlog.

### Workstream 23: Bockwinkel Audit Lane

441. Audit any remaining layer mutations without history.
442. Audit remaining preview triggers.
443. Audit remaining recomposite gaps.
444. Audit remaining async image races.
445. Audit remaining object-shape bbox usage.
446. Audit remaining sourceLayer payload inconsistencies.
447. Audit remaining effect-persistence gaps.
448. Audit remaining tool-targeting inconsistencies.
449. Audit remaining selection-routing inconsistencies.
450. Audit remaining stale thumbnail paths.
451. Produce ranked findings.
452. Mark critical vs medium vs low.
453. Cross-check tests against findings.
454. Add missing tests where easy.
455. Hand unresolved findings to Heenan.
456. Re-audit after fixes land.
457. Keep audit notes updated.
458. Flag overstated claims in worker reports.
459. Keep the Family honest.
460. Publish final audit summary.

### Workstream 24: Pillman Chaos Lane

461. Try weird order of operations on layers.
462. Try fast undo and redo spam.
463. Try closing the dialog mid-effect-edit.
464. Try merge during odd states.
465. Try flatten after rapid effect changes.
466. Try reorder after transform.
467. Try hide and show during drag.
468. Try duplicate then immediate undo.
469. Try merge then immediate undo.
470. Try flatten then immediate undo.
471. Try sourceLayer after deleting the referenced layer.
472. Try sourceLayer after duplicating the referenced layer.
473. Try sourceLayer after renaming the referenced layer.
474. Try selection plus fill while a weird tool is active.
475. Try cancel transform after preview queued.
476. Try load PSD while toggling visibility.
477. Try large PSD plus effects plus render.
478. Try weird blend and effect combos.
479. Report only reproducible breakage.
480. Hand the best breakage cases to Flair and Heenan.

### Workstream 25: Raven Cleanup Lane

481. Remove temporary sprint-only noise.
482. Consolidate helper names if obvious.
483. Consolidate tiny duplicate decode helpers if safe.
484. Clean comments that over-explain.
485. Tighten new test naming.
486. Tighten undo labels.
487. Tighten effect-session flag naming.
488. Tighten layer-target helper naming.
489. Remove dead branches introduced during fixes.
490. Keep diffs readable.
491. Make final files easier to maintain.
492. Check that no unrelated churn slipped in.
493. Check runtime sync still clean.
494. Check touched mirrored files stayed aligned.
495. Prepare concise cleanup summary.
496. Suggest next refactor targets without doing them.
497. Mark anything intentionally deferred.
498. Leave breadcrumbs for the next night.
499. Support final handoff quality.
500. End the night with a cleaner battlefield than it started.

## Final Handoff Template

Use this exact structure at the end of the sprint:

```text
Heenan Family Overnight Sprint - Final Report

What shipped:
- ...

Completed tasks:
- #...

What was verified:
- ...

Manual checks still recommended:
- ...

What remains:
- ...

Blocked tasks:
- #...

Risk notes:
- ...

Recommended next sprint:
- ...

Brutally honest summary:
- ...
```

## Morning Review Note

The morning review should answer:

- what actually shipped
- what was really verified
- what was overstated
- what still feels risky
- what the next night should focus on
