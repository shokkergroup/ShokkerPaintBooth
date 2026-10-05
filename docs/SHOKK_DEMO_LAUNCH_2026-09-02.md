# SHOKK DEMO — Market Launch Package

Date: 2026-09-02  
Owner: Shokker Paint Booth  
Launch posture: free Windows demo, truth-first proof, zero Discord gate

## Current local release candidate

- Version: `1.0.0-demo.4`
- Installer: `electron-demo/dist/ShokkerPaintBooth-SHOKK-DEMO-1.0.0-demo.4-Setup.exe`
- Download size: `412,437,205 bytes` (`393.33 MiB`)
- SHA-256: `FF3B3F8413AC3EFFB9E67A898871EF4F806621C924129ED000285E9FF9063075`
- Verification: focused demo suite `93/93`; JavaScript syntax and paid Easy-shell guard passed; live browser interaction QA passed; staged and packaged servers matched `958/958` with zero missing, extra, or hash-drifted files; packaged backend self-check passed.

This is the owner-test build, not yet the public upload. It is still Authenticode-unsigned, and the supplied ARCA/Chevy/sponsor starter art must have documented distribution rights or be replaced with clean fictional SHOKK art before launch.

## Demo.4 launch-polish and QA contract

Demo.4 closes the visible trial-experience gaps that would weaken a public first impression:

- **Truthful finish thumbnails:** every picker card shows the finish's real paint beside its real combined spec; no decorative streak is painted over the pair, and no card may fall back to a generic swatch.
- **Independent Source and Live zoom:** each large preview has its own minus, percentage, plus, and Fit controls; the mouse wheel zooms whichever preview the cursor is over without changing the other.
- **Material-map inspection:** hovering Combined, Metal, Rough, or Coat temporarily puts that map in Live Preview; leaving restores the paint preview. Clicking a map opens its labeled full-screen inspector, with Close and Escape support.
- **Branded Render Recipe:** a successful full Render opens a SHOKKER-branded recipe with paint/spec proof, source and output, number mode, ordered Zones, coverage/tolerances, PSD-layer scope, material, Base Color mode/lock, key strengths, downloads, PayHip, and Discord.
- **Three-logo introduction:** the three owner-supplied logos appear in a short randomized sequence once per app launch. It is skippable, honors reduced-motion preferences, and runs without delaying starter-source initialization.

Final demo.4 release QA must prove all five behaviors with the supplied layered PSD, then repeat clean packaged-app boot/import/render checks and exact source-to-stage/package integrity checks. Fill the installer size, SHA-256, Windows coverage, and final proof summary above only from that rebuilt installer—not from the previous candidate.

## The call

Do **not** require somebody to join Discord before they can download SHOKK DEMO.

The clean funnel is:

```text
CAR-TRANSFORMATION VIDEO
        ↓
$0 PAYHIP PRODUCT PAGE
        ↓
DOWNLOAD → OPEN → FIRST RENDER
        ↓
OPTIONAL: SHOW THE CAR / GET HELP IN DISCORD
        ↓
OPTIONAL: UNLOCK THE FULL PAINT BOOTH
```

That is the whole strategy. Put the payoff first, let people touch the product fast, then invite the people who actually care into the community.

PayHip already supports a genuinely free digital product: the customer enters an email, does **not** enter payment details, and receives the download immediately. PayHip can also collect email consent separately. There is no growth win in putting a Discord account, server join, and second click in front of that experience. ([PayHip: free products](https://help.payhip.com/article/76-how-to-create-a-free-product), [PayHip: email consent](https://help.payhip.com/article/217-email-consent-for-customers))

Discord should feel like the pit box, not the tollbooth:

- Downloading is free and direct.
- Joining Discord gets help, render showcases, finish votes, update notes, and conversation.
- The first Discord invitation appears after the first successful render and on the PayHip download page.
- No mass DMs, mass invites, join-for-join, or invite rewards. Discord prohibits unsolicited bulk messaging and inauthentic engagement, and specifically warns that invite-reward behavior often creates spam. ([Discord Community Guidelines](https://discord.com/guidelines/), [Discord spam guidance](https://discord.com/safety/360044104071-Tips-against-spam-and-hacking))

## The launch promise

> **ONE PAINT FILE. 25 MATERIAL LIVES.**  
> Pick it. Color it. Finish it. Render it. SHOKK DEMO opens ready so you can feel what Paint Booth does before spending a dollar.

The demo is not supposed to explain every feature in the full program. It is supposed to deliver one undeniable moment:

> “That is the same paint file — and it does not look like the same car.”

### Who this is for

Prioritize these audiences in this order:

1. iRacing painters who already work from layered paint files and want material movement without rebuilding every map by hand.
2. Drivers, teams, and leagues who want a stronger-looking car but are intimidated by the full paint workflow.
3. Livery artists who want faster experimentation and a new finish vocabulary for client work.
4. General sim-racing viewers who may not paint yet but will share a spectacular same-car comparison.

### Truth boundary

Say exactly what the demo is. The limitation is part of the pitch because it makes the product easy to understand.

| In SHOKK DEMO | Deliberately reserved for the full product |
|---|---|
| 25 hand-picked selectable finishes | Full finish library |
| Included ready-to-open starter paint | Full project breadth |
| Multiple colors and real Zone controls | Second through fifth base-overlay layers |
| All retained Zone popout sliders | Patterns and spec-pattern overlays |
| Pick and Exclude | Full painting and selection toolset |
| Real Layers panel | Advanced production workflows |
| Source, Live, Combined, Metal, Rough, Clearcoat previews | Everything intentionally removed from the demo |
| Custom or sim-stamped number | — |
| Render to the selected car folder | — |
| FRACTURE THIS PAINT surprise | — |

Use this language everywhere: **25 selectable finishes plus the FRACTURE button**. Do not accidentally advertise FRACTURE as a 26th picker finish.

## Non-negotiable trust gate before public launch

### 1. Use a marketing-safe car

The supplied ARCA/Chevy paint currently shows recognizable racing and sponsor marks. Do not put third-party logos into the installer, PayHip cover, thumbnail, or launch video unless the owner has documented permission to distribute and market them.

iRacing’s current support guidance says the logos, marks, or IP of its licensed partners may not be used, and its EULA says third-party marks in submitted materials require express written permission. This is a marketing-risk warning, not legal advice. The safest launch asset is the same car and same geometry with original SHOKK marks, a fictional number, and fictional sponsor blocks. Never use the iRacing logo as if SHOKK were an official product. ([iRacing partner-logo guidance](https://support.iracing.com/support/solutions/articles/31000176114-can-i-use-iracing-logos-or-the-logos-of-iracing-licensed-partners), [iRacing EULA, section 1(e)](https://ir-core-sites.iracing.com/members/pdfs/20240314-iRacing%20Terms%20of%20Use%20and%20EULA%20dated%20Mar%2014%202024.pdf), [iRacing trademark page](https://www.iracing.com/trademarks/))

Recommended footer:

> SHOKK DEMO is an independent creator tool. It is not affiliated with or endorsed by iRacing.com Motorsport Simulations or any vehicle, series, or sponsor brand shown in user-created paints.

Use “for an iRacing paint workflow” descriptively in body copy. Keep **SHOKK DEMO** as the product name.

### 2. Make a Windows download feel trustworthy

The PayHip page must show:

- Exact publisher/product name that appears in the installer.
- Current version, publish date, download size, and SHA-256 checksum.
- Verified Windows versions and whether internet is required after download.
- One screenshot of the real app and one real output comparison.
- A plain sentence explaining which local folders the app reads and writes.
- Clear uninstall instructions.
- Support email and optional Discord support link.
- Privacy statement: no secret phone-home behavior. If anonymous diagnostics ever exist, make them opt-in and explain them.

Use a signed release installer for the public launch. Test from a clean Windows account, not only the development machine.

### 3. Label every visual honestly

- Put `IN THE FREE DEMO` beside every launch-video finish that is actually included.
- If a paid-only finish appears later, label it `FULL VERSION` on that shot.
- Use the same car, camera, crop, and lighting for the comparison.
- Add `ACTUAL APP OUTPUT — NO POST-ADDED FINISH EFFECTS` only if that statement is completely true.
- Do not fake a material shift with a color-grade transition.

The hero launch video should use demo finishes only. Save the paid-only monsters for a clearly labeled follow-up called “What the full Paint Booth adds.”

## PayHip setup

### Recommended settings

1. Create a **Digital Product** named `SHOKK DEMO — Free 25-Finish Paint Booth`.
2. Set the price to `0`, not `0+`. This is a product trial, not a tip jar.
3. Keep the product **Unlisted** during beta, then make it **Visible** at launch.
4. Connect the payment processor PayHip requires even for a $0 product.
5. Do **not** use a checkout redirect for launch. PayHip warns that a redirect removes the immediate post-checkout download button and sends users to email for the file instead. ([PayHip: product setup and visibility](https://help.payhip.com/article/59-adding-a-digital-product), [PayHip: checkout redirects](https://help.payhip.com/article/97-checkout-redirect))
6. Set email consent to **Always ask for consent**, regardless of country. Delivery email is required; marketing email should be a choice.
7. Add the Discord invitation to the product download page and receipt as a secondary action: `Need help or want to show the car? Join the SHOKK pit box.`
8. Connect GA4 to PayHip and verify its default Purchase event with a test download. PayHip’s built-in conversion report includes free products and reports views, checkout starts, and completed checkouts. ([PayHip: GA4](https://help.payhip.com/article/93-google-analytics), [PayHip: conversion reporting](https://help.payhip.com/article/108-conversion-rate))
9. Enable the cookie banner and consent-aware analytics behavior appropriate to the markets being served. ([PayHip: cookie banner](https://help.payhip.com/article/207-cookie-banner))
10. Run the entire public URL flow in an incognito browser and on a phone before posting it anywhere.

For cold audiences, link to the full product page so they can see proof and requirements before downloading. For existing customers or warm Discord members, PayHip also supports a direct-checkout link, but test it before use. ([PayHip: direct checkout links](https://help.payhip.com/article/126-direct-checkout-link))

### Ready-to-paste PayHip product copy

**Title**

> SHOKK DEMO — Free 25-Finish Paint Booth

**Hero line**

> ONE PAINT FILE. 25 MATERIAL LIVES. PICK IT. COLOR IT. SHOKK IT.

**Description**

> I cut Shokker Paint Booth down to the bone and kept the part that matters: watching a paint come alive.
>
> SHOKK DEMO opens with a ready-to-use starter paint, so you are not dropped onto a blank screen. Pick an area. Add your colors. Choose one of 25 hand-picked finishes. Move the real Zone material controls. Watch Source, Live, Combined, Metal, Rough, and Clearcoat. Then render it to your selected car folder.
>
> You also get the FRACTURE THIS PAINT button — one click into Soul Core Emerald/Pink Flash.
>
> This is a real working taste of Paint Booth, not a slideshow and not a timed trial.

**What is inside**

- 25 selectable finishes.
- Ready-to-open starter paint.
- Multiple colors per Zone.
- Real Zone popout sliders.
- Pick and Exclude tools.
- Full right-side Layers panel.
- Custom number or sim-stamped number.
- Source, Live, Combined, Metal, Rough, and Clearcoat views.
- Render and car-folder output.
- FRACTURE THIS PAINT.

**What is intentionally not inside**

- No second through fifth base overlays.
- No pattern system.
- No spec-pattern overlays.
- No giant production tool wall.

> Free download. No payment details. Email is used to deliver the file; marketing updates are optional.  
> Windows: `{VERIFIED WINDOWS VERSIONS}`  
> Version: `1.0.0-demo.4`  
> Download: `393.33 MiB (412,437,205 bytes)`  
> SHA-256: `FF3B3F8413AC3EFFB9E67A898871EF4F806621C924129ED000285E9FF9063075`

**Buttons / final CTA**

> **DOWNLOAD SHOKK DEMO FREE**  
> Made something wild? **SHOW YOUR CAR IN DISCORD**  
> Ready for the full library and advanced tools? **UNLOCK SHOKKER PAINT BOOTH**

### The 25-name proof list

Copy these labels from the final built catalog before publishing so the page and app match exactly:

1. Chrome (Foundation)
2. Gloss
3. Frozen (Foundation)
4. Powder Coat (Foundation)
5. Metallic (Foundation)
6. EFX Holographic Drift
7. Shag: Lava Lamp
8. Cherry Polka
9. Field: Frozen Bank
10. Water: Tsunami
11. Frozen: Black Ice
12. HAZ Bloom
13. Chrysina Gold
14. Hematite
15. Glass Slipper
16. Woodcut Block
17. Ground Beetle Obsidian
18. Swallowtail Prism
19. Chocolate Mint
20. Shatter Royale
21. Stained Circuit
22. Neon Rush
23. Fire Fade H
24. Aurora Black Rainbow
25. Herringbone

## The 39-second launch video

### Deliverables from one edit

- `9:16, 1080×1920, 39 seconds`: YouTube Short, Facebook Reel, and native Reddit upload where accepted.
- `16:9, 1920×1080, 39–45 seconds`: normal YouTube video and Facebook-group native upload.
- `1:1, 1080×1080, 12–15 seconds`: later reminder cut, not a same-day duplicate blast.
- One clean 16:9 thumbnail and one 9:16 Short thumbnail.
- Burned-in captions plus an uploaded caption file.

Square or vertical YouTube uploads up to three minutes are categorized as Shorts; URLs in Short descriptions and Short comments are not clickable. Channel-profile links and the Related Video link are clickable. Put the demo as the **first channel-profile link**, and connect the Short to the 16:9 proof/setup video. ([YouTube: three-minute Shorts](https://support.google.com/youtube/answer/15424877), [YouTube: clickable-link locations](https://support.google.com/youtube/answer/13748639))

### Capture rules

- Open on the finished car, not a logo animation.
- Keep every car comparison on the same angle and lighting pass.
- Use hard cuts or a simple wipe; do not manufacture an effect with the transition.
- Show enough UI to prove the workflow, then get back to the car.
- Make it understandable with the sound off.
- Use original music or licensed audio. YouTube points creators to its Audio Library for royalty-free tracks. ([YouTube Shorts upload tips](https://support.google.com/youtube/answer/12921536))

### Shot-by-shot storyboard

| Time | Picture | On-screen copy | Voice / sound |
|---|---|---|---|
| 0.0–1.5 | Three brutal same-angle car cuts: Chrome → Black Ice → Holographic Drift | `THIS IS ONE PAINT FILE.` | Three tight impact hits; no logo bumper |
| 1.5–4.0 | Hold the plain source car, then snap to the first finished render | `ONE PAINT. 25 MATERIAL LIVES.` | “This is one paint file.” |
| 4.0–7.0 | Real app: select a Zone with Pick, add two colors | `PICK IT. COLOR IT.` | “I did not rebuild the wrap.” |
| 7.0–18.5 | Same-angle sequence: Chrome, Water: Tsunami, Frozen: Black Ice, Swallowtail Prism, Aurora Black Rainbow | Finish name plus `IN FREE DEMO` on every cut | Call each finish name; let material sound accents land |
| 18.5–23.0 | Real Zone popout: move Hue/Strength/Scale or another retained slider and show Live Preview respond | `THE REAL CONTROLS WORK.` | “These are the real Paint Booth controls.” |
| 23.0–27.5 | Tap FRACTURE THIS PAINT; cut to Soul Core Emerald/Pink Flash result | `FRACTURE THIS PAINT` | Music drops, then hits hard |
| 27.5–31.5 | Show Layers panel, custom number, Render button, then output | `LAYERS. NUMBER. RENDER.` | “Keep the layers. Set the number. Render.” |
| 31.5–35.5 | Six-result grid, all same car and crop | `25 FINISHES + FRACTURE` | “No blank start. No giant tool wall.” |
| 35.5–39.0 | Strongest finished car with SHOKK DEMO wordmark | `FREE SHOKK DEMO` / `FIRST LINK ON MY CHANNEL` | “Pick it. Color it. SHOKK it. The demo is free.” |

### Voiceover script

> This is one paint file. I did not rebuild the wrap. Chrome. Black Ice. Holographic Drift. Tsunami. Swallowtail Prism. Aurora Black Rainbow. SHOKK DEMO gives you 25 hand-picked finishes, the real color and Zone controls, live material previews, Layers, Render, and one FRACTURE button. No blank start. No giant tool wall. It opens ready. Pick it. Color it. SHOKK it. The free demo is the first link on my channel.

Record it like a builder showing the machine, not an announcer reading an ad.

### Hooks to test

Use one hook per upload. Do not rotate five titles on launch day.

1. `This is ONE paint file. Watch what happens to the material.`
2. `I stripped Paint Booth down to 25 finishes and made it free.`
3. `Chrome. Black Ice. Tsunami. Same car. Same paint file.`
4. `If you paint iRacing cars, I built you a free test drive.`

### YouTube title options

1. `25 Paint Finishes From ONE PSD — Free SHOKK DEMO`
2. `I Built a Free 25-Finish Paint Booth Demo`
3. `Same Car. Same Paint. Chrome to Black Ice in Seconds.`

Recommended launch title: **25 Paint Finishes From ONE PSD — Free SHOKK DEMO**

YouTube’s own guidance says titles should accurately represent the video, stay succinct, and place the important words first; it also advises restraint with all caps and emoji. The thumbnail should be simple and readable at small sizes. ([YouTube title and thumbnail guidance](https://support.google.com/youtube/answer/12340300))

### Thumbnail

- Split one car down the center: Chrome on the left, Aurora Black Rainbow or Black Ice on the right.
- Three words maximum: `ONE PSD. 25 LOOKS.`
- Tiny SHOKK DEMO mark in a corner.
- No app screenshot collage and no wall of tiny finish swatches.

## Platform playbooks and ready-to-post copy

### YouTube

Publish two meaningfully edited versions, not a pile of duplicates:

1. The 9:16 Short for discovery. CTA: `Free demo — first link on my channel.`
2. The 16:9 normal video for trust and a clickable description link. YouTube requires Advanced Features for clickable external links in long-form descriptions/comments. Link the Short to this video as its Related Video. ([YouTube link rules](https://support.google.com/youtube/answer/13748639))

Do not paste the same promotional comment across other creators’ videos. YouTube prohibits high-volume repetitive comments, deceptive traffic tactics, and flooding the platform with near-duplicate content. A few real format variations are fine; a synthetic wall of copies is not. ([YouTube spam policy](https://support.google.com/youtube/answer/2801973))

**Long-form description**

> ONE paint file. 25 hand-picked material finishes. One FRACTURE button.
>
> I built SHOKK DEMO so you can actually touch Shokker Paint Booth instead of watching me tell you what it can do. It opens with a ready starter paint and keeps the real Zone controls, Layers, previews, number workflow, and Render.
>
> GET SHOKK DEMO FREE: `{PAYHIP_UTM_URL}`
>
> Full Paint Booth: `{FULL_VERSION_UTM_URL}`  
> Show your render / get help: `{DISCORD_INVITE}`
>
> Every finish marked `IN FREE DEMO` in this video is included. SHOKK DEMO is an independent creator tool and is not affiliated with or endorsed by iRacing.com Motorsport Simulations.

**Pinned long-form comment**

> I want the honest answer: did the same-car comparison prove the material change, or do you need to see a full start-to-render run? Free demo is here: `{PAYHIP_UTM_URL}`. If you render one, show me the car.

**Short description**

> ONE PSD. 25 finishes. Free SHOKK DEMO → first link on my channel. Every look labeled `IN FREE DEMO` is actually included. #simracing #carpainting

After 24–48 hours, inspect `Shown in feed`, `How many chose to view`, views, likes, comments, subscribers, and retention. YouTube exposes these Shorts metrics in Studio and advises comparing Shorts with Shorts, not with a viral outlier. ([YouTube Shorts analytics](https://support.google.com/youtube/answer/12942217))

### Reddit

Reddit is not a place to copy-paste an ad into every racing community. Its current spam rule prohibits repeated or unsolicited mass engagement and asks people whose contributions are mainly links to their own business to be thoughtful about frequency and community-specific rules. ([Reddit spam policy](https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam))

Current community fit on 2026-09-02:

| Community | Launch posture |
|---|---|
| r/iRacing | Strongest product fit. Current rules require iRacing relevance and forbid referral asks, but do not grant a blanket commercial-post exception. Send modmail first and obey any reply. ([current rules](https://www.reddit.com/r/iracing/about/rules.json)) |
| r/simracing | Current rules explicitly allow reasonable developer/manufacturer product participation and limited creator self-promotion, provided the account contributes beyond advertising. Giveaways require prior modmail. This free-for-everyone demo is not a giveaway, but modmail is still the smart launch move. ([current rules](https://www.reddit.com/r/simracing/about/rules.json)) |
| r/NASCAR | Skip. Current rules prohibit self-promotion and also restrict fantasy-paint show-and-tell. Only post if moderators give explicit written approval for this exact submission. ([current rules](https://www.reddit.com/r/NASCAR/about/rules.json)) |

Rules can change. Re-open the live rules on posting day. Upload the clip natively when the community accepts native video, disclose that you built the product in the first sentence, and stay to answer real questions.

**Moderator message**

> Hi mods — I build Shokker Paint Booth, a Windows paint-finishing tool for iRacing painters. I am releasing a permanently free, heavily stripped demo with 25 finishes and a ready starter paint. I would like to make one launch post with a 39-second native same-car comparison, clearly disclose that I am the developer, and ask for workflow feedback. No referral code, no contest, no required Discord join, and no repeated posting. May I include the $0 PayHip link, or would you prefer the video/discussion without an external link? I will follow whichever format and flair you want.

**r/iRacing draft**

Title:

> I built a stripped, free version of my paint-finishing app — 25 finishes on one included paint

Body:

> Full disclosure: I built this.
>
> I wanted people to be able to judge Paint Booth with their own hands, so I cut it down hard. SHOKK DEMO opens with a ready paint and keeps Pick, Exclude, multiple colors, the real Zone sliders, Layers, the material previews, number workflow, Render, and 25 finishes. Patterns, extra base overlays, and the bigger tool system are out.
>
> The clip uses the same car, camera, and lighting. Every look marked `IN FREE DEMO` is included.
>
> The question I care about: does `Pick → Color → Finish → Render` make sense without me standing over your shoulder?
>
> Free Windows demo: `{PAYHIP_REDDIT_IRACING_URL}`  
> I will be here answering setup questions and taking the rough feedback too.

**r/simracing draft**

Title:

> I cut my paint app down to a free 25-finish demo — here is the same car rendered six ways

Body:

> Developer post, clearly labeled: I built SHOKK DEMO.
>
> The problem I was trying to solve was not “give the car another flat color.” It was “make the material read differently when the light moves” without forcing a new user to learn the entire production app first.
>
> So the demo opens ready, keeps the real color/Zone/material controls and Layers, and removes patterns, extra overlays, and almost every tool. The video is six honest outputs from the same paint and camera.
>
> It is permanently free and does not require a Discord join. Download if you want to break it: `{PAYHIP_REDDIT_SIMRACING_URL}`
>
> I would especially value feedback from painters: which finish reads like a real material, and which one still reads like an effect sitting on top?

Do not post both Reddit submissions at once. Get permission, publish in the best-fit community, participate, then wait at least a day before a separately written post elsewhere.

### Facebook Page / personal profile

**Post copy**

> I FINALLY DID IT.
>
> I cut Shokker Paint Booth down to the bone and built a FREE DEMO people can actually use.
>
> One ready paint. 25 hand-picked finishes. The real color controls. The real Zone sliders. Layers. Live material previews. Render. And the FRACTURE THIS PAINT button.
>
> No pattern maze. No giant wall of tools. It opens with something loaded so you can get straight to the part that matters: making the car come alive.
>
> Watch this — every finish marked `IN FREE DEMO` is in it.
>
> GET SHOKK DEMO FREE: `{PAYHIP_FACEBOOK_PAGE_URL}`
>
> If you render something nasty, I want to see the car. Discord is optional and linked after the download.

Use the native video file. Keep the caption about the thing actually shown and use only a couple of relevant hashtags. Meta says accounts using distracting unrelated captions, excessive hashtagging, or networks of repetitive posts may receive less reach; original, relevant content is the safe lane. ([Meta: cracking down on spammy content](https://about.fb.com/news/2025/04/cracking-down-spammy-content-facebook/))

### Facebook groups

Every group is its own room. Read its rules and Featured posts. Some groups require participant or post approval, and admins can restrict which post formats are allowed. ([Facebook group participation approval](https://www.facebook.com/help/1414053028933409/), [Facebook group post formats](https://www.facebook.com/help/144548630973199/))

**Admin permission message**

> Hi — I am the developer of Shokker Paint Booth. I have a permanently free, stripped Windows demo for painters: 25 finishes, an included starter paint, no required Discord join, and no payment details. I made a 39-second native same-car comparison and would like to share it once, clearly labeled as my own product, then stay in the comments for support. Is that allowed here? If yes, do you want the free download link in the post, in a comment, or omitted?

**Approved group post**

> **ADMIN-APPROVED DEVELOPER POST**
>
> Same car. Same paint file. Six completely different material lives.
>
> I built a heavily stripped, free version of Shokker Paint Booth so painters can try the engine without learning the whole production app. You get 25 finishes, multiple colors, the real Zone sliders, Layers, all material previews, numbers, Render, and FRACTURE THIS PAINT. You do not get patterns, extra base overlays, or the full tool suite.
>
> No card. No required Discord join. It opens with a starter paint so you are not staring at nothing.
>
> Free demo: `{PAYHIP_FB_GROUP_URL}`
>
> I will be in the comments. Tell me which finish wins — and tell me where the workflow fights you.

Customize the first two lines for each group. Never claim admin approval unless it was actually given. Do not paste the same post into a dozen groups in one sitting.

### Discord

Create these five clean channels or threads:

- `#demo-start-here` — download, 3-step quick start, current version.
- `#demo-help` — setup and render support.
- `#show-your-shokk` — user cars; ask permission before reposting externally.
- `#finish-wishlist` — one request per message, vote with reactions.
- `#demo-known-issues` — concise confirmed issues and workarounds.

Create separate invites for `youtube`, `reddit`, `facebook`, `payhip`, and `in-app` so invite use is attributable. Discord’s invite UI defaults links to seven days unless adjusted; set deliberate limits/expiration and audit active invites. ([Discord Invites 101](https://support.discord.com/hc/en-us/articles/208866998-Invites-101))

**Launch announcement**

> ⚡ SHOKK DEMO IS LIVE ⚡
>
> I stripped Paint Booth down to the part you can FEEL: one ready paint, 25 hand-picked finishes, real Zone controls, Layers, six material views, Render, and FRACTURE THIS PAINT.
>
> The demo is free. Discord was never made a gate. Get it here: `{PAYHIP_DISCORD_URL}`
>
> When you make the first render, drop it in `#show-your-shokk`. If something breaks, put the demo version, Windows version, what you clicked, and a screenshot in `#demo-help`. I want the pretty cars **and** the ugly bug reports.

## Rollout calendar

Do not chase a mythical universal “best time.” Launch when the owner can stay present for the next two to three hours and answer people.

### T−7 to T−5: trust and permission

- Freeze the public demo candidate and record version, size, checksum, and supported Windows versions.
- Replace unauthorized logos/marks in the public starter paint and all launch visuals.
- Put the PayHip product in Unlisted mode and complete a clean test download.
- Send the Reddit modmail and Facebook admin requests.
- Create Discord channels and source-specific invites.
- Give the exact installer to five trusted painters with one assignment: open, make one change, render, uninstall.

### T−4 to T−2: proof assets

- Record the same-angle car passes and real UI actions.
- Cut 9:16 and 16:9 versions.
- Add captions and the `IN FREE DEMO` labels.
- Build the thumbnail and six clean stills.
- Upload YouTube versions as Unlisted; verify captions, crop, profile link, related video, and description link.
- Fix only launch-blocking defects. Do not churn the product after the release candidate is frozen.

### T−1: dry run

- Make the PayHip page final but still Unlisted.
- Click every link from a phone and clean desktop browser.
- Confirm download, install, first open, starter paint, one finish, one Render, full-version link, Discord link, and uninstall.
- Pre-fill the platform posts and UTM links.
- Prepare three saved support replies: installer warning, source-paint location, and render-output location.

### Launch day

1. Make the PayHip product Visible and perform one real $0 checkout.
2. Publish the 16:9 YouTube proof video.
3. Publish the Short with the PayHip product first in channel-profile links and attach the Related Video.
4. Post to owned Facebook and announce in the existing Discord.
5. Publish only in communities that approved the post; stagger them so the owner can reply.
6. Pin the current version and known-issues message.
7. Spend the first response block answering questions, not posting to more places.

### T+1 to T+3

- Triage every install/render blocker.
- Ask permission to reshare the first three strong user renders.
- Post one proof image or support tip, not another copy of the launch ad.
- If the same blocker appears three times, pause promotion until it is fixed or clearly documented.

### T+7

- Review the funnel metrics and top five questions.
- Publish a short “What you made with SHOKK DEMO” reel only with creator permission.
- Update the PayHip page around the question people actually asked most.
- Decide whether the next video should be a 60-second setup, a finish battle, or a clearly labeled full-version comparison.

### T+14 and T+30

- T+14: release the winning repeatable format, not a random second launch.
- T+30: decide whether to keep the same 25, swap weak demo finishes, improve onboarding, or change the full-product offer based on activation and support evidence.

## Tracking and attribution

Use one lowercase UTM vocabulary. Google Analytics treats parameter values as case-sensitive and recommends consistent `utm_source`, `utm_medium`, and `utm_campaign` fields. ([Google Analytics UTM guidance](https://support.google.com/analytics/answer/10917952))

Campaign name:

```text
utm_id=shokk_demo_202609
utm_campaign=shokk_demo_launch_2026_09
```

| Placement | UTM source | Medium | Content |
|---|---|---|---|
| YouTube 16:9 description | `youtube` | `organic_video` | `proof16x9_v1` |
| YouTube profile / Short | `youtube` | `organic_video` | `short39_v1` |
| r/iRacing | `reddit` | `organic_social` | `riracing_native39_v1` |
| r/simracing | `reddit` | `organic_social` | `rsimracing_native39_v1` |
| Facebook Page/profile | `facebook` | `organic_social` | `owned_native39_v1` |
| Each Facebook group | `facebook` | `organic_social` | `group_{shortname}_native39_v1` |
| Discord announcement | `discord` | `community` | `launch_announcement_v1` |
| Consent-based email | `email` | `email` | `demo_launch_v1` |
| Demo full-version button | `shokk_demo` | `in_app` | `post_render_unlock_v1` |

Example:

```text
{PAYHIP_PRODUCT_URL}?utm_source=reddit&utm_medium=organic_social&utm_campaign=shokk_demo_launch_2026_09&utm_id=shokk_demo_202609&utm_content=riracing_native39_v1
```

Do not use opaque link shorteners. A full PayHip or owned-domain URL is easier for a Windows-software prospect to trust.

### First-launch success gates

These are **internal experiment targets, not industry benchmarks**. Replace them with SHOKK’s own baseline after the first launch.

| Stage | Metric | First seven-day target |
|---|---|---|
| Video hook | YouTube `How many chose to view` | At least 60% |
| Video proof | Average percentage viewed on the 39-second cut | At least 70% |
| Interest | Measurable link/profile clicks ÷ views | At least 1.5% |
| Product clarity | PayHip checkout starts ÷ product views | At least 30% |
| Download friction | Completed checkout ÷ checkout starts | At least 70% |
| Activation signal | Voluntary first-render confirmations or shared renders ÷ downloads | At least 20%; known undercount |
| Product health | Confirmed install/render blockers ÷ downloads | Under 5% |
| Community quality | Useful bug reports, workflow answers, or renders | At least 10, not raw member count |
| Commercial intent | Full-version clicks ÷ completed demo downloads | At least 5% |

Track this row per post:

```text
date | platform | community | post_url | content_id | views | chose_to_view |
avg_percent_viewed | link_clicks | payhip_views | checkout_starts |
completed_downloads | discord_joins | shared_renders | full_version_clicks |
install_blockers | top_question | notes
```

### Diagnose the leak instead of blaming the platform

| Leak | Likely problem | First response |
|---|---|---|
| People swipe before three seconds | The car payoff is too slow | Open on three transformed cars; remove bumper/logo |
| People watch but do not click | CTA or offer is unclear | Say `FREE WINDOWS DEMO`, show 25 finishes, move CTA on screen earlier |
| People click but do not start checkout | Trust or compatibility is unclear | Improve signed-publisher proof, requirements, real screenshots, size, and no-card language |
| Checkout starts but does not complete | Email step feels unexplained | Say plainly that email delivers the file and marketing is optional |
| Downloads happen but renders do not | Onboarding or install is failing | Improve starter open, 3-step quick start, and output-folder confirmation |
| Renders happen but nobody joins Discord | The community promise is weak | Lead with support, showcases, and finish voting; do not add a gate |
| Demo is loved but full clicks are weak | Upgrade value is vague | Show one honest demo-vs-full workflow and the exact additional capabilities |

## Feedback loop

Use one bug format everywhere:

```text
Demo version:
Windows version:
What I clicked:
What I expected:
What happened:
Screenshot or short capture:
Did a restart reproduce it?
```

Sort feedback into four lanes:

- **Blocker:** install, open, load, render, output, or file-loss risk. Acknowledge immediately; pause promotion if repeated.
- **Friction:** user succeeds but gets lost. Fix onboarding or copy before adding features.
- **Desire:** asks for patterns, overlays, or full tools. This validates full-product interest; answer clearly without pretending the demo includes them.
- **Proof:** strong render or quote. Ask written permission before reposting and credit the creator.

Do not promise dates in comments. Say what is confirmed, what is being investigated, and where the current workaround lives.

### Consent-based follow-up sequence

Only send marketing follow-ups to people who opted in.

- Immediate transactional email: download, 3-step first render, checksum, help link.
- Day 2: one real tip — how to compare Source, Live, and material channels.
- Day 5: ask for one answer — which included finish won and why?
- Day 8: show one user render with permission and explain what the full product adds.
- Day 14: release notes or a useful tutorial, not a generic “buy now” blast.

## Launch checklist

### Product and trust

- [ ] Public installer is the exact signed release candidate.
- [ ] Clean Windows install/open/render/uninstall passed.
- [ ] Version, size, SHA-256, OS support, and internet requirement are published.
- [ ] Starter paint and launch visuals contain only authorized marks/assets.
- [ ] Product name, publisher name, installer name, and PayHip title agree.
- [ ] Demo/full limitations are written plainly.
- [ ] Full-version, Discord, privacy, support, and non-affiliation links work.

### Store

- [ ] PayHip price is `0`, product is Visible, and connected processor is valid.
- [ ] Real $0 checkout requires no payment details and delivers immediately.
- [ ] Marketing consent is optional and always asked.
- [ ] Checkout redirect is off.
- [ ] GA4 and PayHip conversion reporting are verified.
- [ ] Product cover, actual screenshot, actual output, and requirements are live.

### Creative

- [ ] Same car/camera/light used for comparisons.
- [ ] Every finish shown is labeled `IN FREE DEMO` or `FULL VERSION`.
- [ ] No fake transition creates the advertised effect.
- [ ] 9:16, 16:9, thumbnails, captions, and six stills are exported.
- [ ] YouTube profile demo link is first; Short Related Video is attached.
- [ ] All music, footage, logos, and paint assets are authorized.

### Community

- [ ] Live rules rechecked for every subreddit and Facebook group.
- [ ] Moderator/admin permission recorded where required or uncertain.
- [ ] Every post discloses that the owner built the product.
- [ ] Community-specific copy and UTM are used.
- [ ] No mass posting, duplicate-comment spam, unsolicited DMs, or invite rewards.
- [ ] Owner has a response block available immediately after each post.

### Day-one support

- [ ] `#demo-start-here`, help, showcase, wishlist, and known-issues spaces are ready.
- [ ] Three saved support answers are ready.
- [ ] Version-specific known issues are pinned.
- [ ] Bug report template is visible.
- [ ] A stop-promotion threshold is agreed: three repeats of one blocker or a 10% blocker-report rate, whichever arrives first.

## The one-sentence strategy

**Make the car impossible to ignore, make the download impossible to misunderstand, and let the first successful render earn the Discord join and the full-version sale.**
