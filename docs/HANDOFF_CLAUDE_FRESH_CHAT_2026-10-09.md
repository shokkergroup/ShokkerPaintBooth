# Fresh SPB Claude chat: paste this as the first message

Copy everything inside the box into a new chat in the Shokker Paint Booth project:

```
You are the SPB orchestrator, continuing from the 2026-10-09 chat (session local_591f610e-e20a-4fac-adb0-067234f846e4).
1. Read C:\Users\Ricky's PC\.claude\handoffs\live\SPB_CURRENT.md and follow its "New chat on start" steps: rename this chat "SPB orchestrator - <YYYY-MM-DD HH:MM>", archive the previous session named there, and move this chat into the sidebar group named there.
2. Read the resume card it points to (C:\Users\Ricky's PC\.claude\handoffs\live\63d7718c-16cf-4503-af96-4728de5fabf9.md). It has the goals, the state of everything shipped today, the gates, the traps and the owner decisions. Do not re-ask decisions listed there.
3. Continue from the card's "Next steps", in order. Start with step 1: ask me how the new tool-options band above Source / Live Preview looks, and offer to move the panes up into the empty space under it.
Rules: keep context small (read surgically, filter output), use Haiku helpers for mechanical work and Sonnet for judgement, pass `model` explicitly, no commits, no rm/del in the shell, never kill processes by name.
Note: a separate ChatGPT/OpenAI agent is building SPB's ChatGPT connection from docs/HANDOFF_CHATGPT_MCP_2026-10-09.md, in its own folder mcp/chatgpt/. Don't touch that folder. If it files requests in mcp/chatgpt/REQUESTS_FOR_CLAUDE.md, review them with the APPCHAT owner rules in mind.
```

What the new chat inherits (all live, synced, each change behind an off switch):
- Tools rebuilt on PhotoCraft engines (selection, strokes, transform, magnetic lasso, Color Range, brushes, Quick Select), with the tool-check fixes applied.
- PhotoCraft bundled, with the "Edit in PhotoCraft" round trip.
- The toolbar split: main controls above Source / Live Preview, the rest at the bottom.
- The helper can move patterns, and the engine's Position X/Y works at 100% opacity.
- Helper scores: hidden reworded set 209/541 (36 harmful); the other gates are on the card.
