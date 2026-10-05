# DEEP-SHIP (2026-10-03)
- build_cards_js.py: row field index 18 = null or {c:look_close,f:look_far,l:light,s:stack,n:not,p:placement,w:with_numbers,q:confidence} (asks/avoid_asks/qa_fix/variants_note not shipped). Indexes 0-17 unchanged.
- Size: spb-ai-cards-data.js 3,189,305 -> 5,074,261 B (+1.89 MB); spb-lsa-data.js unchanged 1,545,957.
- spb-ai-cards.js: SpbAICards.deep(key) (object or null); card(key).deep; default data token 20261003deepship.
- spb-pro-ai.js finish_details: returns d.deep (look_close, look_far, light, stack, not, placement, with_numbers) + description clause. mcp/server/tools.json spb_finish_details clause added. Advisor card line skipped (optional).
- Proof: _easy_claude_work/deep_test.js 9/9. tool_test 15/15, convo_test 52/52, stack_test 61/64 (same 3 SINGLE-unchanged snapshots as before, card data changed; not re-snapped), adv_fp 0 claimed.
- Not verified: live browser load time of the 5 MB file; .mcpb / live server not rebuilt/restarted.
