# AI copilot: honest assessment and roadmap (2026-09-30)

Written for the owner after the v3 "read the car" work. Everything marked MEASURED comes from `_easy_claude_work/pw/battery.py` runs on real PSDs (results in `_easy_claude_work/eval/battery/`). Everything marked VERIFIED-WEB was checked against the sources listed at the end on 2026-09-30.

## 0. Build status (updated 2026-09-30 night, after the owner said "start building everything")
BUILT AND PROVEN WITH REAL CLAUDE (2026-10-01, Pepsi brief, 23 turns, honest self-check): Claude MCP bridge + `.mcpb` (own Claude plan, no API cost; `mcp/README.md`); offline brain round 2 (follow-ups, undo, part colours, spec looks); 27+ more car layouts from the owner's PSD library (4,271 PSDs scanned, 62 layouts found; recognition test on 21 real livery PSDs: 21/21 correct layout after the empty-Mask fix); local-model provider (Ollama / LM Studio on 127.0.0.1, AI settings -> "Private option"); stronger-model escalation for repair turns; car-map share/export; measured regression runner (`_easy_claude_work/pw/regress.py`).
BUILT 2026-10-01 night (owner: Easy Mode parked, chat is the showcase): **Chat Studio** front door (PRO | CHAT pill; `js/spb-chat-studio.js`), Versions filmstrip + Compare slider, **Surprise me** (4 designs tried on the car, 2 colour schemes + 2 look-led), **colours from a picture** (drop / paste / pick), `Watch a demo` player (`docs/CHAT_STUDIO_DEMO_SCRIPT.md`), 74 theme palettes, **looks with no AI** (carbon fiber, camo, flames, galaxy, holographic, candy, pearl... from a curated table + the 4,800-look catalogue), **numbers / sponsors layer edits**, **number readability checker + fix**, single elements (pinstripe / racing stripe), start over, how-to answers from the built-in manual, Brain picker (Fast / Sonnet 5.5 / Opus 5.5 / Fable 5.1 over OpenRouter; with the Claude plan the model is picked in Claude itself).
STILL NOT BUILT / OPEN: stadium-truck, dirt late model, midget / sprint and road-racing layouts are unlabelled (UV wireframes alone cannot be read safely: needs a painted livery of each to tell hood from roof and front from rear; the teach flow covers them meanwhile); Spanish / other languages in the offline brain; a Claude MCP "fast path" (one-call design) belongs to the Codex MCP lane.
NOT BUILT (needs the owner or approval): ChatGPT "Sign in with ChatGPT" (OpenAI approval form for paid apps); Shokker-hosted AI credits (needs a server, billing, abuse limits); labelling the remaining ~35 layouts (stadium trucks, dirt midget / sprint, DLM 2023, road-racing cars); scrapping Easy Mode (owner mused about it, not decided); flames / chevrons / swooshes in the design library.

## 1. Where it really stands

MEASURED (40 buyer-style scenarios, 6 templates, `deepseek/deepseek-v4.1-flash`):
- Cost per answer: median $0.0028, mean $0.0034, p90 $0.0060, max $0.0095. About 5 model calls and 24 s (p90 41 s) per answer. Today's total on the local counter was $1.52 for 2,419 calls (30 M prompt tokens: almost all of the cost is the long system prompt, not the answers).
- Livery schemes (Gulf, Martini, Pepsi, Halloween, retro neon, red racing stripe, two-tone, pink sides / blue front, left red / right blue) land on the right named parts on every layered template tested, with numbers and sponsors intact. Spec-only requests change only the spec (paint diff < 1%). Multi-step follow-ups (thinner stripe, then matte black hood) work. Undo restores the previous picture exactly. With no AI key, schemes, single-part colours and spec looks still work.

Honest limits:
1. **The owner's exact PSD was never loaded.** I tested on the ARCA PSD (same layout family, 98% fingerprint match with their sheet), the Gen 6 Camaro, Next Gen, Silverado and DLM templates. Their layer names (Yellow Base...) are handled, but their file is the real test.
2. **The cheap model still misreports.** It sometimes says "blue hood" when the zone it made is red. The receipt now lists what was REALLY applied (from the zone specs), and the app measures the result, but the chat text can still be wrong. A stronger model fixes most of this at 10-30x the price.
3. **Car coverage is the moat and it is thin:** 6 layout families are hand-checked. Everything else uses the one-minute "show me" flow. Flat TGAs cannot separate numbers and sponsors from the body, so the app recolours the body colour only: good, not perfect.
4. **Vision cannot read UV sheets** (5 models tested; best 9/22 boxes). The vision judge is advisory only (17 of the 40 answers carried a visual-check note, and most of the ones I could verify by eye were wrong: it called pink "cyan" and a lengthwise stripe "sideways"). The measured checks are what we trust.
5. **Design quality is "clean professional flat liveries", not artist work.** No flames, chevrons, swooshes, per-panel gradients or geometry yet (the design library has bands, stripes, blocks, bumpers).
6. **Engine quirks found:** mask-less "everything" zones do not repaint pure white; Pro's undo snapshots omit region masks. Both are worked around in the copilot, not fixed in the engine.
7. **Latency 24 s median** feels slow next to the offline path (instant).
8. Only I have tested it. No buyer has.

## 2. Can a Claude or ChatGPT subscription power it instead of API spend?

**Claude: not by logging the user in, but yes through MCP.**
- VERIFIED-WEB: Anthropic's Feb 19 2026 documentation update says subscription OAuth tokens (Free/Pro/Max) are only for Claude Code and Claude.ai; using them in any other product or tool is a terms violation, and enforcement started in Jan and was tightened on April 4 2026. A "Sign in with Claude" button inside SPB is not allowed, and would break without notice.
- VERIFIED-WEB: the allowed route is the other direction. Claude Desktop installs local MCP servers (.mcpb "desktop extensions", one-click) and supports remote MCP "custom connectors" on every plan; usage counts against the user's normal Claude plan limits, with no API charge. So SPB can ship a small **SPB MCP server** (it already has the zone kit, car library, design library and preview): the buyer chats in Claude Desktop (or Claude Code) with their own subscription and Claude drives SPB through tools. Pros: zero AI cost to anyone, strongest model, great demo ("talk to your paint booth"). Cons: the zone kit, car library and preview live inside the app's page, so the MCP server needs a bridge into the running app (the page opens a local websocket to it, or Electron IPC): a few days of work, not a weekend hack; the chat lives in Claude Desktop, not in SPB's panel; the buyer needs Claude Pro or Max; Claude does not get the SPB panel UI (teach flow would need a tool that opens the picker); tool results can carry preview images.

**OpenAI / ChatGPT: possible, needs their approval for a paid app.**
- VERIFIED-WEB: "Sign in with ChatGPT" (announced at OpenAI DevDay) lets a user grant an app permission to use their ChatGPT plan allowance for eligible Responses API requests, no API key and no extra charge; the user can set weekly caps per app. Launch partners include OpenCode, Devin, Amp, Warp, Notion, Vercel.
- VERIFIED-WEB: today it is open to **open-source and locally hosted** apps; for a **paid or remotely hosted** app OpenAI asks developers to complete an interest form. SPB is a paid local app, so we would have to apply and be approved. I could not confirm which models or how much allowance a plan gives, and whether an Electron app with a loopback OAuth redirect is accepted. It is a free option worth applying for: build the sign-in behind a provider interface so it is a one-day add if approved.

**Other low-cost routes (VERIFIED-WEB, Sep 2026):**
- Google AI Studio free key: Flash models only, about 10 requests/min and 1,500/day for Gemini 3 Flash; permanent free tier; on the free tier Google may use the data to improve products. Fine as a "free tier for hobbyists" option, not something to promise.
- OpenRouter free models: 50 requests/day, 1,000/day after a one-time $10 of credits. Good for testing, flaky for a product.
- A local model (Ollama / LM Studio on the buyer's PC): free and private. The design library turns most requests into "pick a preset, a palette and finishes", which a small local model can do; open-ended chat quality will be lower. No verification needed: it is a standard OpenAI-compatible endpoint on localhost.

## 3. How to keep making it better (in priority order)

1. **Win with the free tier.** The offline design brain is the demo hook and costs nothing. Next: port the Easy TELL language engine (195 tests) into Pro for offline edits ("thinner", "other colour", "undo", "only the sides"), add flames / chevron / swoosh / fade recipes (polygon masks per part), a number-contrast checker, and brand-style palettes (keep names generic: "Pepsi-style", not logos).
2. **Grow the car library, it is the moat.** Add a "Share my car map" export (the teach data is already a small JSON per layout), collect them (opt-in), curate with the overlay check, ship in app updates. Each car takes about 10 minutes with the tooling in `scripts/ai_atlas/`. Start with the cars buyers actually paint: Cup (Camry, Mustang, Next Gen variants), ARCA Ford/Toyota, trucks, the dirt classes.
3. **Regression battery before every release.** `battery.py` is the seed: add pass/fail on MEASURED checks only (zone colours show, art preserved, undo identity, spec-only paint diff), run on 6+ PSDs, record cost. Never trust the vision judge as a gate.
4. **Model strategy.** Keep the cheap model as default, escalate to a stronger one when a measured check fails or the brief is long (router), use vision only when asked, turn on prompt caching and trim the 12 k-token prompt. Benchmark Qwen / DeepSeek / Claude Haiku / GPT mini on the battery with real numbers before choosing.
5. **Small local model for the structured part.** Log (request -> apply_scheme arguments) pairs (opt-in), then a 1-3 B model fine-tuned on them could run fully offline. This is a research bet, not a promise.
6. **Pro-side Easy replacement.** If Easy Mode is scrapped, the copilot must own the first-run experience: open on first launch, "describe your paint" as the first screen, the offline design brain as the zero-key path, a 3-step key setup.

## 4. Ways to spin and price it

- **Free:** offline design brain (no key, no cost). Headline: "describe your paint scheme in words, even offline".
- **Bring your own key:** pennies per paint job (median $0.003 per answer; a heavy evening of 50 answers is about $0.15). Needs a 2-minute OpenRouter setup: real friction for non-technical buyers.
- **Shokker AI credits:** SPB hosts the key (your OpenRouter account) and sells credits or a $3-5/month add-on. At $0.003 per answer, $5 buys about 1,500 answers. Needs a small server, per-buyer limits and abuse protection, and customer support. This removes the setup friction; it is the best conversion path but real operational work.
- **Use your subscription:** Claude via the SPB MCP server (works today, no approval), ChatGPT via Sign in with ChatGPT (needs OpenAI approval). Zero cost to you.
- **Private and local:** local model option for buyers who do not want images leaving the PC.

## 5. Demo video: clips that sell (all reproducible with the battery)
1. "Gulf style" -> full livery in 10 s, numbers and sponsors untouched.
2. "Pink down the sides, blue on the front" -> then "make the roof white" -> then "undo".
3. Spec-only: "make the hood mirror chrome, keep the paint" with the spec map view beside the paint.
4. Unknown car: the copilot asks, you drag four boxes, the scheme lands exactly (remembered next time).
5. Airplane-mode clip: offline design brain.
6. The cost counter under each answer ("about a third of a cent").
7. "Old-school Pepsi Challenger with a twist" as the closer.

## 6. Risks to manage
- Terms of service: never embed a Claude login (VERIFIED-WEB: banned). Use MCP, API keys, or approved sign-in only.
- Privacy: the sheet image and zone data go to the model provider; say so plainly, keep the local-model option, never store keys in files (DPAPI only).
- Trademark: palettes are style families, not brand logos; keep it that way in marketing.
- Model churn: OpenRouter model ids change; keep the router config in one place and the battery as the acceptance test.
- Cost caps: keep the default daily cap low ($2-3) for buyers; the $10 cap was for development.

## Sources (checked 2026-09-30)
- Anthropic subscription OAuth ban: https://winbuzzer.com/2026/02/19/anthropic-bans-claude-subscription-oauth-in-third-party-apps-xcxwbn/ , https://gigazine.net/gsc_news/en/20260220-anthropic-third-party-block/ , https://dev.to/mcrolly/anthropic-kills-claude-subscription-access-for-third-party-tools-like-openclaw-what-it-means-for-3ipc
- Claude Desktop extensions and connectors: https://claude.com/docs/connectors/building/mcpb , https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp , https://4sysops.com/archives/anthropic-claude-connectors-desktop-extensions-vs-local-remote-mcp-servers/
- Sign in with ChatGPT: https://developers.openai.com/siwc , https://developers.openai.com/siwc/token-sharing-open-source , https://thenewstack.io/sign-in-with-chatgpt/
- Gemini free tier: https://tokenmix.ai/blog/gemini-api-free-tier-limits , https://pecollective.com/tools/gemini-free-tier-guide/
- OpenRouter free models: https://costgoat.com/pricing/openrouter-free-models , https://klymentiev.com/blog/openrouter-free-tier
