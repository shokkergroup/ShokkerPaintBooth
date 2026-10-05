# SPB Encyclopedia: blind buyer usability test (2026-10-05)

Tester: Claude (Sonnet 5.5), blind, buyer-style. Server 127.0.0.1:59879 only, own Chrome on CDP 9813 + Playwright. Desktop 1440x900, then 1100x800 re-checks.
Raw per-task log: `_easy_claude_work/enc_ux/tasks.jsonl` (20 lines). Screenshots: `_easy_claude_work/enc_ux/*.png`. Sweep data: `sweep_1440.jsonl`.

## Result: 12 of 20 tasks fully succeeded, 8 partial, 0 failed

| # | Task | Result | Clicks / time |
|---|------|--------|---------------|
| 1 | clearcoat explained + set a satin look | yes (clunky) | ~8 / 3 min |
| 2 | export to iRacing + where files go | yes (2 searches) | 3 / 2 min |
| 3 | "spec map looks wrong in the sim" | partial | 2 searches |
| 4 | compare two chrome finishes | yes | 4 / 1.5 min |
| 5 | stealth / murdered-out recipe, try it | partial | ~6 / 4 min |
| 6 | zone priority | yes | 2 / 1 min |
| 7 | finish lesson 1 of a learning path | yes | 5 + long scroll / 3 min |
| 8 | "what is a mask" | partial | 1 / 1 min |
| 9 | Trading Paints upload steps | yes | 2 / 1 min |
| 10 | make numbers stand out | partial | 2 searches |
| 11 | what roughness 0 means | yes | 1 / 20 s |
| 12 | how to undo | yes | 1 / 15 s |
| 13 | typos "clearcaot", "tradng paints" | partial (1 of 2 typos fails) | 1 each |
| 14 | find something by browsing only | partial | 5 / 3 min |
| 15 | Spec Explorer | partial (not searchable) | 3 |
| 16 | paint does not show in iRacing | yes | 2 / 1 min |
| 17 | look up "monolithic" | yes | 1 |
| 18 | Shokk Drop + keyboard shortcuts | yes (search only) | 1 each |
| 19 | "Show me in the app" Do-it buttons | partial | 2 |
| 20 | repeat worst tasks at 1100 wide | yes | - |

Automated sweep of 259 articles (Contents tree, 1440 wide): 0 broken images, 0 horizontal overflow, 0 slow opens (each under 1.5 s), 0 console errors from the reader itself. The reader is technically solid. The pain is in search ranking, wrong pictures, hand-off buttons and a few leaked internals.

## Top 10 problems, ranked by buyer pain

1. **Typo search can return pure garbage with a confident count.** "clearcaot" works, but "tradng paints" returns 23 results led by "Reading a spec picture by colour" and Triangle finishes; "iracng folder" returns "Steer a finish's colour...". No "no good match" or "Did you mean Trading Paints?". The Trading Paints article exists and is one correct letter away. Evidence: `s38_typo_tradng.png`.
2. **Spec Explorer (the flagship interactive) cannot be found by search.** "spec explorer" returns "File Picker: ... Windows File Explorer" and nothing else relevant. It is reachable only through an in-article button or Contents Part VIII. Evidence: `s43_specexplorer.png`. Same family: the Compare tool is not found by "compare finishes" / "compare two chrome finishes" (it is in Contents and on finish pages).
3. **Do-it buttons do something other than the article promised, and the Encyclopedia vanishes.**
   - The stealth recipe's "Flat Black" tile opens the guided builder titled "Flat Black finish on the whole car", but no look is highlighted in the grid (an unrelated "Holographic Drift" has the orange ring). Run changes only the shine, so the car stays bright cyan, not black. The article's own steps need colour #0a0a0c as well. (`s23`, `s24_flatblack_card`, `s25_flatblack_run`)
   - The clearcoat article's Do-it row offers Wet Look / Candy / Soft Matte, no Satin. Clicking Soft Matte closes the reader entirely; I had to pick Satin in a cramped scrolling card, then Run. (`s04_doit`, `s05`, `s07`, `s08`)
   - After any Do-it the reader is gone and the left-panel "Encyclopedia" chip is replaced by a tiny book icon in the Step builder; the top-bar Encyclopedia button sits behind the "Colours from a picture" button in the default window (button exists at x=669,y=60 but `elementFromPoint` hits `.spb-cs-btn`).
4. **Wrong or irrelevant pictures.** The Chrome finish page shows a blue tie-dye "Moonstone" ARCA car captioned as the Foundation shelf (`s18_chrome_finish_a.png`). The stealth / murdered-out article shows a bright blue sparkly "Abyss Blue" car (`s22b_stealth_pic.png`). Trading Paints, Where-the-files-go and "File Picker" articles all open with the same two generic figures ("Header: User ID..." and "The whole window, labelled"), which illustrate nothing in those articles (`s35`, `s43`).
5. **Raw internal names leak into buyer UI.** Do-it buttons read "Show me in the app: btnRender" (also carPickBtn, deployRowToggle; 4 of 259 articles). Every article footer prints "id workflows.how_paint_gets_on_car". Clicking "Show me ... btnRender" closes the reader and highlights nothing visible in the default Chat window (`s46_rawname.png`, `s47_showme_click.png`). (The specific "rpTabLayers" I was told to look for did not appear.)
6. **A-Z index is polluted.** The "#" bucket has ~53 non-name entries such as "(the color art)", "(the color art) 2", "), which is why it's required", "...or paste / browse the exact car folder...", "< ON-CAR STAGE", "#candy", "+ Add Zone". Evidence: `s37_az_top.png`.
7. **Duplicate / ambiguous finish names.** Two different finishes both titled "Chrome" (Foundation `f_chrome` and base `chrome`, each with a plain grey swatch and different numbers 254 vs 255), two "Anodized" tiles, identical-looking quick-answer + article pairs ("Where the files go", four "Undo" entries, two "Custom Number vs Sim-Stamped Number"). Swatches for most finishes are flat grey gradients and tell the buyer nothing.
8. **Browse-only is slow to the goal.** "Every finish, shelf by shelf" gives 59 chips; the candy and chrome families live inside "More Bases" (449 tiles, not alphabetical, no filter). Swatch thumbnails lazy-load: 365 of 449 still pending after 4 s, first rows blank for ~3 s (`s42_more_bases.png` vs `s42b_more_bases_wait.png`). Clicking a Part header in Contents expands it above the viewport because the sidebar keeps its scroll, so it looks like nothing happened (`s40_part6.png`).
9. **Search ranking favours definitions over symptoms / intent.** "spec map looks wrong in the sim" ranks "What the spec map is" first and the diagnostics (#3 "My colours look different in iRacing"). "make the numbers stand out" ranks pack-level "Stand out in a pack" above "Matching numbers to the body: contrast". "what is a mask" returns the template Mask layer first with no "which mask?" chooser. Several result cards also show a repeated unrelated "Q: Where do I find Zone order..." sub-snippet (`s26_zone_priority.png`).
10. **Screens in articles do not match the default window.** Articles describe a PRO window (ZONES column, PRO/CHAT pill, RENDER button); a buyer who just opened the app sees Paint / Shine / Car parts, "Render & save", "Full editor". Plus small visual bugs: plain words "YOUR", "SAME", "SYMPTOM", "CAUSE" drawn as boxed control-name chips (`s49_notshowing.png`); Spec Explorer's "coat ball" uses metal 150 / roughness 110, not the slider values, and the Matte preset ball still looks glossy (`s45_explorer_matte.png`); lesson 1 is the full mega-article with its quiz at the very bottom, and "Next lesson" is offered even after a wrong answer.

Also seen: the page's own JS calls `localhost:59876` (build-check, api/swatch-*, iracing-paint-cars) from the 59879 test instance and gets 403s; `/api/finish-preferences` and `/api/user-imports` give 403 on 59879; `data/encyclopedia/_alias_overlay.json` is a 404 (possibly why alias/typo search is weak).

## Top 5 things that impressed me

1. Search is fast and mostly smart: "stealth murdered out", "zones priority", "roughness 0", "undo", "it doesn't show up in iracing", "trading paints upload" all put the right article first (typed live, ~2 s end to end).
2. Article template: summary, "when you need it", numbered steps, labelled screenshots, common-mistake tables (YOU SEE / WHY / FIX), Q and A, Related. Troubleshooting article "My paint does not show up in iRacing" is genuinely better than most docs.
3. Compare view (Chrome vs Satin Chrome): one-line plain-words difference, bars for metal/roughness/clearcoat, paint advice, "Try" buttons (`s20_compare.png`).
4. Spec Explorer: sliders, 10 real-finish presets, rendered balls, channel strip that updates live (`s44`, `s45`).
5. Learning path with "Check yourself" quiz (wrong answer says "Not quite", right answer gives "Lesson 1 complete", progress dots) and honest answers (Shokker does not upload to Trading Paints, .mip requirement). Layout also holds at 1100 wide: TOC turns into a chip row, no horizontal scroll (`w1100_a_stealth.png`, `w1100_d_morebases.png`).

## Concrete fix suggestions

1. Search: add a "no good match, did you mean X?" step (edit distance 1-2 against titles / glossary terms, minimum score gate); alias-index "spec explorer", "compare finishes", "compare" to the tool pages; fix the 404 `_alias_overlay.json`.
2. Do-it handoff: pre-select the named look in the builder grid, add Satin to the clearcoat Do-it row, make recipe tiles (stealth) set colour as well as shine, and keep the reader open (or add "Back to Encyclopedia") after a Do-it. Add a visible Encyclopedia button that is not covered in the Chat window.
3. Replace raw ids in Do-it labels with human names (`btnRender` -> RENDER, `carPickBtn` -> Car folder picker), hide the footer "id ..." (or move it behind a "for developers" toggle), and make "Show me" visibly pulse the target (or say "not in this view, switch to Full editor").
4. Figures: per-article pictures only; for finish pages render the finish itself on the example car (not the shelf sample); remove the two generic UI figures from articles they do not illustrate; use real swatch renders in search hits and Compare.
5. A-Z: filter entries that do not start with a letter/number title, drop fragments, drop `#tag` entries (or put them in a "Tags" bucket).
6. Disambiguate same-named finishes ("Chrome (Foundation, keeps your colour)" vs "Chrome (base, repaints)") and de-duplicate quick-answer vs article pairs in results (group them).
7. Browse: add a filter box and A-Z sort to shelf grids, a "Candy / Chrome / Carbon / Matte" family chip row at the top of "Every finish", and scroll Contents so an expanded Part header lands in view.
8. Ranking: boost Troubleshooting for symptom phrasing ("looks wrong", "doesn't show", "won't"); boost number-specific articles for "numbers"; for ambiguous nouns ("mask") show a "Which one?" chooser.
9. Regenerate screenshots from the current default window (or show both Chat and Full-editor variants), and style only actual UI terms as control chips (not "YOUR", "SAME").
10. Lessons: split lesson 1 (put the quiz near the top or give a short lesson summary), gate "Next lesson" on the quiz or label it "Skip".

## Environment notes (for the caller)

- Runs against shared test state: tasks 1 and 5 applied "Satin" and "Flat Black" shine-only changes to whatever car is loaded in the 59879 instance (versions "1. Satin", "2. Flat Black"). I did not Undo them.
- My Chrome profile directory was created at `_easy_claude_work/pw/profile9813` (the copied launcher script kept the old `pw` folder), the only write outside `enc_ux/` besides this report.
