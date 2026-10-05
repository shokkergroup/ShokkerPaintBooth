# EDIT-BATTERY (2026-10-03, CDP 9671, server 59879)
Logs: _easy_claude_work/eval/editbat_t246.log, editbat_t248.log, editbat_t251.log. The scripts print, they do not assert; verdicts below are my reading.
- t246 (5 paints x 13 sentences): 65/65 ran, no crash, no zone with vis<60% of share. 0 zones on 8 sentences, all by design (colour list; ram2 numbers ask-first; dlm stripes ask which colour; ram2 "pink pink" asks).
- t248 arca stack: completes, undo x2 ok. Anomaly: "make the white purple" claims 17% but preview purple share = 3.6% (then 9.9 after numbers purple).
- t251 legacy: 15/15 ran. Defect: "show the numbers" after "hide the numbers" returns the advisor card ("you want clean edges...") instead of un-hiding, zones []. Likely PARSER (WP7: "show" read as show-me/advice).
- Side note: "make the black purple" on f150 warns numbers contrast 1.6:1 (expected behaviour).
- No screenshots taken (script PNG output not produced).
