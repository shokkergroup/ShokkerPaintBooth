# LOAD_TIME - deep cards data (11.7 MB) measured 2026-10-03 - verdict: NO SPLIT
Harness: `_easy_claude_work/pw/lt_measure.py` (private Chrome 9675 via `chrome_up_9675.py`, server 59879, 3 cold [cache cleared+disabled] / 3 warm).
- Download (localhost): spb-ai-cards-data.js 11,743,462 B in 91-146 ms cold; spb-lsa-data.js 1.62 MB in 15-18 ms. Warm = conditional revalidate, 325 B / 319 B, 54-100 ms. Static route sends `Cache-Control: no-cache` + ETag, NO gzip for js (irrelevant on loopback/Electron).
- Both files are fetched in the background by a 4 s boot timer (spb-pro-ai.js ~line 2405), so by the first ask `SpbAICards.ready()` was already true (load_ms 0, search ~20-39 ms, 6/6 runs).
- Worst case, ask inside the first seconds: `SpbAICards.load()` 76-525 ms cold (earlier probe), well under 1.5 s.
- Main thread: long tasks after boot 50-333 ms each, none > 500 ms; cold and warm look the same (parse+index of cards ~190-290 ms), so parse not download is the cost, still under the 500 ms bar.
- Decision: both thresholds (first ask > 1.5 s, parse block > 500 ms) not met -> no split, no code/data change, FACETS rebuild unaffected.
