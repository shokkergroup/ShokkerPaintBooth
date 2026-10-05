# WP9 - online AI (DeepSeek v4.1 Flash via OpenRouter) routing check, 2026-10-03

Server 59879, own Chrome CDP 9444. Key configured (`/api/ai/status` configured:true). Raw data: `_easy_claude_work/eval/wp9_deepseek.jsonl` (prompt, mode, tools, reply, zones before/after, cost). Scripts: `_easy_claude_work/pw/wp9_run.py` (A|B|C), `wp9_show.py`.
Cost: 16 online prompts, total today ledger $0.0245 (cap $1). Offline comparison runs are free.

## A. FLAT paint (ARCA chevy25 car_*.tga), 6 prompts - ALL SIX BYPASS THE ASK-FIRST FLOW (defect)
The online model never showed the tinted confirm card (card/Yes/None all false in 6/6). It called `describe_paint` then `refinish` straight away and the zone was applied unconfirmed:
| prompt | tools | result |
|---|---|---|
| numbers purple chrome | describe_paint, refinish(numbers, purple, chrome) | zone "Numbers fill chrome, in purple" applied, no card |
| all the numbers white | describe_paint, refinish(numbers,#fff) | applied, no card |
| sponsors gold | describe_paint, refinish(sponsors,#c9a227,metallic) | applied; reply claims "all 19 of them" |
| stripes matte black | describe_paint, refinish(stripes,#020202,matte) | applied; reply "I found two stripe areas", admits "tiny (<1%)" |
| black matte, leave numbers alone | describe_paint, refinish(black, exclude numbers) | applied; reply "I found the numbers by eye" |
| put the number back | describe_paint, get_state, point_at(numbers) | asked the buyer to drag a box (sensible, no change) |
No invented `mark_elements` boxes (that tool was never called). Classification: 5 x "wrong route: acted without confirm" (the elements are the finder's unconfirmed guess; replies state counts and "by eye" as fact, the model cannot see the paint), 1 x asked sensibly. 0 generic support answers, 0 errors.
Worst replies: "Sponsors are now warm gold ... all 19 of them, kept exactly where they were." and "I found the numbers by eye (this paint has no layers)". Both are invented certainty. Likely fix (not done, outside lane): in the online `refinish` path on a flat paint, for target numbers/sponsors/stripes (or exclude of them) return the same ask-first card as the offline path, and strip "by eye"/counts from the tool-result text the model sees.

## B. PSD car (SPB ARCA V7.psd), 4 prompts, online vs offline (offline_first=1, SpbAI unconfigured)
All four: describe_paint + refinish (the numbers prompt skipped describe_paint, refinish only), zones equal to offline except:
- "make the white glossier": online refinish look "wet look" -> f_gel_coat; offline -> f_soft_gloss (different finish, same zone count).
- numbers purple+metallic: colour #7a2fd6 online vs #6a1b9a offline (both f_metallic).
- black matte / yellow powder coat: identical zone name + finish.
- Reply honesty defect: online replies say numbers/sponsors/tape "left alone / untouched" for "black matte" and "yellow powder coat"; the offline path correctly warns that the colour is also in the numbers and sponsors, so those changed. The zone is identical, so the online claim is false.
- No vision-critic undo in any run (zones present after). 4 correct (1 with a different finish choice).

## C. extras (PSD car; phase C also ran on the PSD car, not flat)
- "numbers gold and sponsors silver": two add_zone layer-region zones (f_metallic, #d4af37 / #c0c0c0), "checked 10/10". Offline gave plain gloss recolours. Correct.
- "make the numbers bigger": no tools, honest "cannot resize" answer (correct).
- "outline the numbers in red": refinish gloss red, reply honestly says a real outline is not possible; offline recoloured fill red with no caveat. Correct.

## Counts (16 online prompts)
correct 7 (B 4, C 3), asked sensibly 1 (A "put the number back"), acted without confirm 5 (A), invented boxes 0, wrong tool 0, error 0, generic support 0. B also has 2 minor deviations from offline (finish choice, colour hex) and 2 misleading "untouched" claims.

## Not verified
Vision-critic path (no vision model configured), flat-paint prompts after a confirm card (no card ever appeared online), real-car correctness of the elements the unconfirmed refinish hit, iRacing render. Test used a single ARCA paint (car_*.tga first file).

## File mtimes (js/)
Only sizes were captured at start (mtime printed as date only): spb-pro-elements.js 325997 -> 326847, spb-pro-ai.js 85329 -> 85346, spb-pro-edit.js 48751 -> 63803. All three changed during the run, so other workers' edits landed mid-run (edit.js +15 KB); results mix versions.
