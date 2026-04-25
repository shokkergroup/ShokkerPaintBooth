# HEENAN FAMILY BOARD MEETING — Shokker Paint Booth

**Date:** 2026-04-19
**Convened:** Heenan
**Attendee of record:** Ricky Hubbard (Big Boss)
**Subject:** Make SPB the kind of product people gladly pay $55 for tomorrow,
talk about constantly, recommend to friends, and associate directly with
Ricky as **the name** in painting tools.

---

## 1. Board Meeting Opening

**Heenan:** Quiet down. Ricky's in the room and he's not here for theater.
We've been shipping correctness for weeks. Engine audit reads 0 broken,
0 GGX, 0 spec-flat, 623 tests green, validator at zero problems. By the
numbers, SPB is in the best technical shape it has ever been in.

That is exactly why this meeting is dangerous.

We are at the point where a healthy codebase makes us think the product
is healthy. It is not the same thing. A painter doesn't open `pytest`.
A painter opens the app, looks at it for ninety seconds, and decides
whether it feels like a real tool or a hobby project. We have not
audited that ninety seconds. We have audited bytes.

Ricky's question is not "is the engine clean?" It is: **why would a
painter open Trading Paints, see SPB cost fifty-five dollars, and pay
without thinking twice?** Today the answer is "they wouldn't, mostly
because they wouldn't know it exists, and if they did know, the first
ninety seconds would not close the sale." That's the problem on the
table.

Rules of order: argue from your lane, no fake consensus, no coddling.
If you think a sibling is wrong, say so on the record. Ricky, you'll get
the unfiltered version. We'll clean it up afterwards if you want.

Let's go.

---

## 2. Roll Call

| Agent | Lane |
|---|---|
| **Heenan** | CEO, integrator, scope discipline, anti-idle, board chair |
| **Flair** | Hardest correctness work — layer/tool/selection semantics, subtle parity |
| **Bockwinkel** | The professor — research, audit matrix, acceptance criteria, evidence |
| **Windham** | The workhorse — tool consistency sweeps, every-similar-bug-fixed-once |
| **Luger** | The total package — full-stack blocker relief, JS↔Python integration |
| **Sting** | The visible one — tool feel, cursor feedback, painter confidence, UX |
| **Pillman** | The loose cannon — adversarial sequences, weird user behavior, hostile QA |
| **Street** | The exotic specialist — one premium painter wow-feature, only after trust |
| **Hawk** | Frontend perf — canvas latency, paint loop, preview invalidation discipline |
| **Animal** | Backend perf — render/preview parity, server-side workflow trust |
| **Raven** | Cleanup and simplification — remove sprint noise, kill dead surface area |
| **Hennig** | Mr. Perfect — perfection gate, rejects clunky wording and partial fixes |

---

## 3. Board Meeting Transcript

### Round 1 — Diagnose. One headline gripe each.

**Sting:** I'll go first because mine is the easiest to ignore and the
most expensive to leave alone. Open the app cold and tell me what a
painter sees. They see roughly **eighteen hundred picker tiles** spread
across multiple registries. Eighteen hundred. There is no human on Earth
who walks into a room of eighteen hundred paint chips and goes "oh good,
let me browse." They go "this is too much, where do I start." We have
won the engineering. We have lost the entrance.

**Pillman:** *[laughs]* I love how you said "eighteen hundred picker
tiles" like it was the worst thing in the room. The worst thing in the
room is that **nobody on this team has actually painted a real iRacing
livery in this app start to finish in the last six weeks**. We have a
"PSD Painter Gauntlet Overnight" doc with ten manual acceptance items
that have been "still requires manual painter proof" for three shifts in
a row. We are auditing the engine for finishes a painter never sees and
ignoring the ten things they will hit in the first hour. That's the
real failure.

**Flair:** Pillman is right and I want to extend it. The active-layer
routing fix this shift was good engineering. Five mutators now route
correctly. But there are *dozens* of other places where the painter's
mental model and the code's mental model don't match yet. Selection
move vs. layer move. Transform selection vs. transform layer. Restrict
zone to a deleted layer. Until those are *all* correct, painters who
came from Photoshop will trip and every trip is a trust withdrawal.

**Bockwinkel:** Let me put numbers under what Sting and Pillman said.
We have **twelve hundred and thirty-seven entries with id+name+desc** in
the catalog. Of the four registries, only the BASES tier has real
curation. PATTERNS, MONOLITHICS, SPEC_PATTERNS are essentially a
firehose. The ratio of "shippable signature finish" to "experimental"
across the SHOKK Series is roughly **20-out-of-25 dedicated, 5-out-of-25
generic stand-ins**. That last 5 are in the brand namespace. Painters
will notice. Painters always notice.

**Windham:** The asymmetric outliers are what kill the perception of
craft. Eight legacy cross-registry id collisions still tolerated.
`gunmetal_satin` with R=145 promising satin and rendering matte.
`fine_silver_flake` at M=160 which is "muted aluminum" not "silver."
`clear_matte` registry says R=220 but the audit measures R=160 so we
don't even know which one is true. This is the stuff that, taken one at
a time, looks pedantic. Taken together, it's why a serious painter says
"this isn't quite right" without being able to articulate why.

**Animal:** Server-side, the truth is uglier than the dashboard. Render
times in the audit are sub-100ms because we test against a 512×512 grey
buffer. **A real iRacing TGA is 2048×2048 with a real spec map.** I
don't have a measured number for end-to-end render-to-preview on a real
car under realistic load, and I should. We don't have a perf budget for
"painter clicks Render and waits N seconds." We should. Without it,
nobody on this team can defend the experience.

**Hawk:** Frontend. Same problem inverted. Paint stroke latency on a
2048×2048 canvas with a PSD layer selected — I haven't measured it
post-TF1-TF8. The active-layer routing changes added a `getImageData` /
`putImageData` round-trip per adjustment. That's fine for one button
press. It's not fine if it stutters on a brush stroke. **Until the perf
is measured under realistic load, we don't know if our trust fixes
helped or made things worse for the workflow that matters most.**

**Luger:** Two things will kill the sale faster than anything else, and
both are integration-layer. One: PSD round-trip. We "shipped" W14 and
TF14 added a runtime test, but Pillman is right — nobody opened a real
PSD in the running app and exported it and re-opened it in Photoshop and
verified the layers came back coherent. Two: the canonical 3-copy sync
is fragile. We have a separate `paint-booth-app.js` legacy bundle still
on disk that we marked dead but didn't delete, plus a 4th-copy in
`electron-app/dist/win-unpacked/` that the build pipeline regenerates.
**Painters will not see this; reviewers will. One git history dive and
your "professional tool" claim collapses.**

**Street:** Everyone is talking about subtraction. I want to talk about
the one thing we could add that would make a paid customer *evangelize*
this product. Not features plural. **One feature that gives SPB a story
nobody else can tell.** We have a real-time spec-map preview on car
shape. No competitor has that. We have not made it the headline.
Painters who see SPB do that for the first time should be ruined for
every other tool. Today the demo doesn't lead with it.

**Raven:** Street wants to add. I want to remove. We have ~1,800 picker
tiles. We have a ★ Enhanced Foundation tier and a (Foundation) tier and
a regular Foundation tier — three tiers of basically the same thing.
We have decade_60s_opart_illusion and 12428555_4988298 as separate
finishes when one of them is a stock-asset-id with a numeric filename
masquerading as a paint. **Cut the catalog by 40 percent and the
remaining 60 percent will look intentional.** Right now it looks like a
hard-drive dump.

**Hennig:** I will speak last because I am the gate. A painter walking
in cold notices three things in their first ninety seconds, in this
order: **does it feel polished, does it feel fast, does it feel
trustworthy.** We have done excellent work on the inside of "does it
feel trustworthy." We have not done the outside work — the wording, the
labels, the spacing, the toast messages, the order of things. Sting is
right. The product currently telegraphs "lots of work has been done
here" but does not telegraph "by people who care about how this looks."
That is fixable in two weeks of focused polish without writing a single
new feature.

### Round 2 — Debate. Where do we disagree?

**Heenan:** OK, that's the diagnosis. Now where do we disagree about
priorities? Street wants one big feature. Raven wants to cut. Sting
wants polish. Animal and Hawk want measurement. Pillman wants a real
painter to actually use the thing. Pick fights.

**Raven:** Street, your "one big feature that nobody else has" is
already shipped. It's the real-time spec-map preview. You want to *add*
something on top of an already-overwhelmed surface area. I want to
*reveal* the thing we already have by clearing the noise around it. We
do not need a new headline. We need to stop hiding the headline behind
1,800 chips.

**Street:** Raven, I hear you, and you're partially right. But "real-time
spec map preview on car shape" is a developer's headline. A painter's
headline is "I made this thing in 90 seconds and it looks like a magazine
cover." Until the workflow produces a finished result that *looks like a
finished result fast*, your real-time preview is a tech demo.

**Sting:** Street is right about one thing — a painter doesn't get
excited about technology, they get excited about output. But here is
where I'll fight Street: the wow-feature you want costs 90 days minimum
and every day it isn't shipped, the existing product is bleeding
credibility. **Polish ships in 14 days and converts the existing product
from "interesting" to "buyable" without depending on a new build.**

**Bockwinkel:** Sting, prove it. "Polish in 14 days." What does done
look like? Acceptance criteria.

**Sting:** Fine. (1) First 90 seconds: blank canvas to painter
applying their first visible finish to a recognizable car. Today this
is hostile because the picker dumps everything at once. Done means a
"start here" curated row of 12 finishes that any painter immediately
understands. (2) Picker organization: every finish reachable in ≤3
clicks from the entry point. Today some live in tabs that need scrolling
plus filtering. (3) Toast wording: every error message tells the painter
what to do next, not just what failed. (4) Naming consistency: kill the
"V2" in customer-facing display names everywhere, not just one. (5)
Onboarding tooltip on every left-rail tool that fires on first hover only,
explaining what the tool does, dismisses on second use. Five things. I
can write the acceptance for each one tomorrow.

**Pillman:** Sting, that is the easiest sale to make in this room and I
still think you're wrong about the order. Polish a product that doesn't
work end-to-end in the running app and you've polished a corpse. **Until
somebody on this team imports `Heatwave-base.psd` into the running app,
paints on a sponsor layer, exports back to Photoshop, opens it, and
verifies pixel parity, NOTHING ELSE MATTERS.** That is the test that
either validates two months of trust work or invalidates it.

**Flair:** Pillman is right. I'll add: even the runtime tests we shipped
this shift are *runtime against stubs*. Real V8, real function bodies —
yes. Real PSD parser, real Adobe-readable .psd output — no. The gap is
documented. The gap is not closed. If we ship at $55 and one painter
posts on a forum that "PSD export breaks layer order on save," we lose
the next 50 sales.

**Hawk:** Defending Sting partially. Polish work is parallelizable with
PSD verification. I can run a realistic perf measurement TODAY on a
2048×2048 canvas while Sting writes the first 90-seconds storyboard
while Luger sets up the real-PSD round-trip rig. **These are not the
same person's time.** The mistake would be to sequence them.

**Animal:** Hawk's right that they're parallelizable, but I want to
push back on "polish converts the product to buyable." Polish converts
*existing visitors* to buyers. It does not get them in the door. **Right
now the door problem is a marketing problem, not a polish problem.** No
amount of finish-browser cleanup will matter if no painter has heard of
SPB. Heenan, this is a question for Ricky too — what is the
distribution plan?

**Heenan:** Hold that. We'll talk distribution in the roadmap section.
Stay on product. What else.

**Windham:** I want to throw cold water on Street's "one big feature."
The previous shifts found 22 silent-stale bugs (TF1-TF22) and the shift
before that found 14 (W1-W14). The pattern is consistent: every time we
audit a part of this app, we find latent bugs. **The codebase is a
constant trickle of small failures we keep discovering.** Until that
trickle slows down, adding a big new feature means adding a big new
trickle. Stabilize first. Add later.

**Street:** Windham, with respect: you're describing a maintenance mode.
Maintenance mode is how products die slowly. Every shift we do should
be 80% trust + 20% advance. Right now we're 100% trust. Painters who
*already* love the tool need a reason to stay excited. New users need a
reason to talk about it. "It got slightly more reliable this month" is
not a reason anybody talks about anything.

**Hennig:** Street, what's the feature?

**Street:** *[leans in]* Here's the pitch. Every painter who imports an
iRacing template wastes 20 minutes laying out base zones — hood, doors,
roof, fenders, splitter. Every car. Every time. Boring. We already have
the zone system. We have a per-car geometry. **Ship a "Common Zones"
button per car that places the standard 8 zones automatically, named
correctly, with sensible default base/finish/color slots ready to fill.
One click. New painter to "ready to paint" in 60 seconds.** That's the
demo video. That's the word-of-mouth moment. "Watch this guy go from
nothing to liveried in two minutes." Nobody else has the per-car
geometry to do this honestly.

**Bockwinkel:** Street, that's actually credible. It uses what we have.
It doesn't require new engine work. Cost estimate?

**Street:** Two weeks of focused work for the top 8 iRacing cars by
popularity. Maybe a week if Luger's PSD round-trip rig overlaps with my
zone-template fixture pack.

**Luger:** I can do the rig in 4 days if I drop the dist-folder cleanup.

**Heenan:** Park the feature debate. I want one more round on what
*today* destroys trust before we go to roadmap.

### Round 3 — Trust killers. Brutal.

**Pillman:** First five minutes of cold use. (1) Open app. (2) Picker
shows 1,800 finishes with no clear "start here." (3) Pick a finish.
Click on car. Wait. Was anything supposed to happen? (4) Look for
"Render" button. There are three buttons that could be it. (5) Realize
you needed to assign a zone first. (6) Open the zone panel. Discover
zone names like "Zone 1 / Zone 2 / Zone 3" by default — not "Hood /
Doors / Roof." (7) Quit. **Six steps to abandonment.** That's the
adversarial baseline.

**Sting:** Pillman just described the entire onboarding gap in seven
sentences and that is exactly why I'm fighting for the first-90-seconds
storyboard. We have invested *months* in active-layer routing for an
adjustment that 3% of painters will discover. We have invested *zero
weeks* in fixing the path that 100% of painters take.

**Hawk:** Trust killer I haven't said yet: the render preview that takes
a couple of seconds and shows nothing changing. Painters click finish,
nothing happens, click finish again, still nothing, then see the
preview update. **Until the click-to-visible-feedback latency is under
200ms, the tool feels broken even when it isn't.** I don't have a
measured number for this either. That should make us all nervous.

**Animal:** Trust killer on my side: server crashes are silent.
`server.py` is 4,481 lines. If it dies, the JS keeps polling and the
painter sees a perpetual "rendering..." spinner with no error. **Failure
modes are invisible.** That's worse than a crash.

**Flair:** Trust killer: the undo stack. We have FOUR undo stacks
(zone, region, pixel, layer × undo + redo = 8 directions). The painter
hits Ctrl+Z and which one fires is non-obvious. We routed selection
modifiers through `pushZoneUndo` in TF9-TF11 + TF21 + TF22 — that helped.
But the painter's mental model is "Ctrl+Z undoes the last thing I did."
Ours is "Ctrl+Z undoes the last thing in *this* stack." We need a
unified undo that the painter never has to think about.

**Hennig:** Trust killer: every error message in the app uses a
different tone of voice. Some are friendly, some are dev-speak, some are
just function names like "TGA decode error." A premium tool talks like a
human. SPB sometimes talks like a stack trace.

**Raven:** Trust killer: the file picker. We have a file-picker dialog
that asks the painter to type or paste a full file path. In 2026. **The
painter is doing this because we wrap an Electron app, but the painter
doesn't know we're an Electron app and doesn't care.** Make the file
picker feel native. Drag-and-drop is shipped. Highlight it. The "type a
path" fallback should be a "hidden devmode" thing, not the default UI.

**Bockwinkel:** Trust killer aggregate: we have a `TOOL_TRUST_MATRIX.md`
that the user never sees and a `PSD_PAINTER_GAUNTLET_OVERNIGHT.md` with
ten unverified items. **The trust gap is not a feeling. It's a list. We
just haven't run the list against the running app yet.**

**Windham:** Trust killer specific: the "8 legacy cross-registry id
collisions." Painters can save a finish to a zone, reload the project
later, and silently get a different finish back because BASES_BY_ID and
PATTERNS_BY_ID both hold the id and the JS evaluation order decides
which one wins. **Saved-config corruption is the worst class of bug for
a paint tool because it eats the painter's previous work.** We tolerated
these. We should not.

**Heenan:** Enough. We have the diagnosis. Let's land moves.

### Round 4 — Concrete moves and pushback.

**Heenan:** Each of you, one concrete move with a cost estimate.
Sting?

**Sting:** First-90-seconds storyboard + curated 12-finish "Start Here"
shelf + 5 onboarding tooltips. **8 days.**

**Pillman:** Real PSD painter gauntlet end-to-end on three actual iRacing
templates (Heatwave, Coulby, SimWrap). Document every defect found.
**5 days, blocks Sting's storyboard from claiming "polished."**

**Flair:** Unified Ctrl+Z that walks all four undo stacks in
chronological order. **6 days, requires a unified undo timeline data
structure.**

**Bockwinkel:** Repurpose the existing TOOL_TRUST_MATRIX into a
**"PROVEN AT RUNTIME" badge system in the docs and on the marketing
page**: every tool/feature with green-light runtime proof gets a badge,
every one without gets a flag. Honesty as marketing. **3 days.**

**Windham:** Resolve the 8 legacy cross-registry collisions behind a
release tag with a saved-config migrator. **4 days, one-time payment for
permanent peace.**

**Luger:** Real PSD round-trip rig. Real .psd in, JS+server roundtrip,
.psd out, byte-compare layer order/visibility/effects. **4 days.**

**Sting:** *[interrupting]* Luger, pair with Pillman. His gauntlet
exercises your rig. Don't double-count.

**Luger:** Agreed. **Combined: 7 days for both.**

**Hawk:** Realistic perf benchmark suite — 2048×2048 canvas, 25-layer
PSD, 3 paint tools, 3 adjustments, 3 selections. Each timed. Budget per
operation. **3 days. The number drives every other perf decision.**

**Animal:** Server-side: render-time budget per request, surface
failures as toast errors with retry, structured logs for crashes. **5
days.**

**Street:** Common Zones per-car template for the top 8 iRacing cars.
Painter goes from blank to ready-to-paint in 60 seconds. **10 days,
worth it because it is the demo video.**

**Raven:** 40% catalog cull. Move ~700 of the weakest 1,800 picker tiles
to a "Lab" tier that requires a toggle to expose. Curate the remaining
~1,100 with intent. **6 days, painful but transformative.**

**Hennig:** Polish gate. Every wins-table item from this meeting passes
through me before claiming "done." No partial credit. **Continuous, no
day cost; cost is rejection rate.**

**Heenan:** Costs add to roughly 50 person-days if done sequentially.
Six of us can run two streams in parallel. Calendar runtime ≈ 25 days
to 5 weeks. That's the 30-day plan minus the perf and Common Zones,
which roll into the 60.

**Hennig:** *[stops Heenan]* Wait. Before you do calendar math, ask
Ricky one question.

**Heenan:** *[turns toward the chair]* Ricky?

**Hennig:** Are we shipping a paint tool, or are we shipping *Ricky's*
paint tool? Those are different products. The first one wins on
features. The second wins on a story. Which one is the goal?

---

## 4. What The Big Boss Needs To Hear

Ricky — what follows is what the family will not soften:

1. **Your engine is healthy. Your product is not yet credible.** The
   audit clean signal (0/0/0/0) means the engine renders without
   blowing up. It does not mean a painter would pay for the experience.
   You have been fixing things you can measure. The things that close a
   sale are mostly things we do not measure.

2. **Nobody on this team has actually painted a real iRacing livery in
   SPB end-to-end in the past six weeks.** That is the single most
   damaging fact in the room. You cannot sell a tool you have not used.
   You cannot demo a workflow you have not run. You cannot fix what you
   have not felt. Until somebody does the full painter gauntlet on a
   real PSD on a real car, every shift we do is structurally blind.

3. **Eighteen hundred picker tiles is a feature that reads as
   amateurism.** Premium tools have curated catalogs. Hobby tools have
   exhaustive catalogs. The fact that everything renders is good. The
   fact that everything is on the front shelf is bad. Painters do not
   judge you on what is in the back room. They judge you on what is at
   the front. Cut the front shelf to ~1,100 with intent or you look
   like you do not know what your own product is about.

4. **The brand needs receipts.** "SHOKK Series" is the brand-defining
   namespace. Twenty of twenty-five entries are flagship. Five are
   wallpaper. Painters who notice will tell other painters. Either
   level the bottom five up to the top twenty's bar, or quietly
   demote them out of the SHOKK namespace. You cannot have a "premium
   tier" with five filler entries in it.

5. **You do not have a $55 story yet.** The market knows free
   alternatives. The market does not know SPB. "Real-time spec preview
   on car shape" is a moat — but a moat in a place no painter has
   visited. The first ninety seconds of the app must lead with that.
   Right now they lead with a wall of paint chips.

6. **The associations are not clear yet.** "Ricky" → "the guy who"
   → ?  Right now there is no completed-sentence ending. People
   talk about products when the sentence ends with something
   memorable. "The guy who built the *real* livery preview." "The guy
   whose tool finally made PSD-to-iRacing actually work." "The guy
   whose paint catalog became the standard." Pick one. Build toward
   it. Today, the catalog is on the table; the workflow trust is
   nearly there; the demo moment is missing. The three weeks of
   focused work below would close that.

7. **The hardest truth: you do not have a marketing channel.** Even if
   we ship every fix in this meeting, nobody hears about SPB unless we
   put it in front of painters. Animal said it bluntly mid-meeting and
   the room went quiet. Distribution is your job, not ours. We will
   build a tool that earns the conversation. You have to start the
   conversation.

---

## 5. Decision Memo

### Top 5 product priorities (ship-or-die order)

1. **Painter Gauntlet Live.** Pillman + Luger run three real iRacing PSDs
   end-to-end through the running app. Document every defect. This becomes
   the authoritative bug list for the next 30 days.
2. **First-90-Seconds Storyboard.** Sting writes + ships the
   entry-experience: blank state, "Start Here" curated finishes,
   guided first-application flow. Every onboarding moment goes through
   Hennig before claiming done.
3. **Catalog Cull.** Raven moves ~40% of the weakest tiles to a "Lab"
   tier behind a toggle. Front-shelf reduces from ~1,800 to ~1,100
   curated finishes. Every remaining tile must justify its slot.
4. **Unified Undo.** Flair lands a single chronological Ctrl+Z that
   spans the four current stacks. Painter never has to think about
   which kind of action they're undoing.
5. **Perf Truth.** Hawk + Animal land measured numbers for the
   five hottest workflows on realistic load. Numbers feed back into
   every UX decision after.

### Top 5 trust-killing problems

1. The painter gauntlet has never been run. Every other claim is
   undefended.
2. Eighteen hundred picker tiles with no curated entry shelf.
3. Render preview latency unknown; "rendering..." spinner with no
   failure path is silently broken when the server dies.
4. Eight legacy cross-registry id collisions silently corrupt saved
   zone configs.
5. The brand-tier (SHOKK Series) ships with 5 of 25 generic stand-ins
   in the flagship namespace.

### Top 5 delight / wow opportunities

1. **Real-time spec-map preview on car shape** — already built, never
   foregrounded. Make it the headline of the first 5 seconds.
2. **Common Zones per car** (Street's pitch) — one click, 60 seconds
   to ready-to-paint. The demo video moment.
3. **Curated SHOKK signature finish** — pick the *one* signature look
   (e.g., Tesseract or Apex) and make it instantly Shokker-recognizable.
   Painters should be able to spot a Shokker car from the grandstand.
4. **PSD round-trip with byte-parity proof** — when this works, no
   competitor can claim it; once we can show it, it's a moat.
5. **Toast voice** — every error message rewritten to be helpful, in a
   consistent tone. Sounds tiny; reads as professional.

### What must happen before we push harder on new features

- All five top priorities above land.
- Painter Gauntlet Live produces a defect list and that list goes to
  zero or near-zero.
- Cross-registry collision count is zero (no more legacy tolerated).
- Perf budgets are set and met for the five hottest workflows.

Until then, every "new feature" is debt. Hold the line.

### What could make SPB feel worth $55 immediately

The first ninety seconds of cold use must produce one moment where the
painter says **"I haven't seen this before."** Today there is no such
moment scripted. With the Five Top Priorities shipped, that moment
becomes:

- Open app → Curated "Start Here" shelf with 12 standout finishes.
- Click any one → Zone auto-applied with a recognizable car shape
  preview. Real spec-map render in under 200ms.
- Paint visible. Painter realizes the preview is *the actual rendered
  car*, not a swatch grid.
- Painter clicks "Common Zones." Eight zones named "Hood / Roof /
  Doors / etc." appear instantly.
- Painter feels they could finish a livery in 10 minutes.

That sequence sells $55 without a sales pitch.

### What could make it feel worth more later

- Common Zones expanded to 30+ cars.
- Curated "Pro Recipe" library — finished liveries sold/shared by named
  painters.
- "Open in Photoshop" round-trip that no other tool ships.
- A Shokker signature look that becomes a community joke ("I see you
  used the Tesseract").
- An iRacing community presence where Ricky is a known good-faith
  contributor, not just a name.

Each of these compounds the product's reputation. Each requires the
foundation in 30 / 60 days first.

---

## 6. Roadmap To Make Ricky The Name

### 30 days — Make the existing product credible

**Week 1-2 (parallel streams):**
- Pillman + Luger: Painter Gauntlet Live on Heatwave / Coulby / SimWrap.
  Defect list published. (Block Sting's "polished" claim until done.)
- Hawk: Realistic perf benchmark suite. 5 numbers, 5 budgets.
- Animal: Server failure modes surfaced. Toast on crash. Structured logs.
- Sting: First-90-seconds storyboard + curated "Start Here" shelf
  (12 finishes, 1 click each).

**Week 3:**
- Flair: Unified Ctrl+Z lands.
- Windham: 8 legacy cross-registry collisions resolved behind release
  tag + saved-config migrator.
- Bockwinkel: TOOL_TRUST_MATRIX → "Proven at Runtime" badges. Becomes
  the public-facing credibility receipt.

**Week 4:**
- Raven: 40% catalog cull. ~700 weakest tiles move to "Lab" tier.
- Hennig: Polish gate over everything above. Ship list approved.

**Outcome at day 30:** SPB is internally credible. We have run it
ourselves. We have measured it. We have curated it. The first 90
seconds works. Saved configs are stable. Trust receipts exist.

### 60 days — Ship the demo moment

**Days 31-45:**
- Street: Common Zones per car for the top 8 iRacing cars. The demo
  video.
- Sting + Street collab: Record actual demo video. 60-90 seconds. Show
  the cold-start to liveried-car flow. No talking head. Just the
  workflow.
- Bockwinkel: Standardize the SHOKK Series. Either level the 5
  generic entries up or quietly demote out of the brand namespace.

**Days 46-60:**
- Animal + Luger: PSD round-trip with byte-parity verification. Make
  this provable, then provable in public.
- Sting: Toast voice rewrite. Every error message audited for tone.
- Hawk: Paint stroke + render latency tuned to budget. Sub-200ms
  click-to-visible.

**Outcome at day 60:** SPB has a sellable demo. The product feels
premium. The brand is honest. The workflow is fast. Distribution
materials exist.

### 90 days — Make Ricky the name

**Days 61-75:**
- Ricky: distribution. Pick three iRacing communities. Show the demo
  video. Offer free licenses to 5 respected painters in each community
  in exchange for honest public feedback.
- Heenan: triage the painter feedback into a defect list. Run a 7-day
  sprint to close the top 10 defects. Public changelog.
- Bockwinkel: publish the "Proven at Runtime" badges page. This is the
  credibility moat — most competitors cannot show this.

**Days 76-90:**
- Street: ship one Pro Recipe library — 10 finished liveries by
  recognized painters, available in-app, attribution preserved. This
  is what painters actually evangelize: *finished work* by names they
  trust.
- Sting: ship a "share my zone setup" feature so painters can publish
  their templates. Community contribution loop opens.
- Heenan + Ricky: announce v1.0 publicly. SPB on iRacing forum, Trading
  Paints subreddit, painter Discords. The "Proven at Runtime" page is
  the headline.

**Outcome at day 90:** The painter community knows Ricky's name and
SPB. There are 10+ named painters using it publicly. There is a
competitive moat (PSD round-trip, real spec preview, Common Zones,
Pro Recipes). The product is buyable at $55 and feels like a bargain.
The sentence "Ricky is the guy who" has an ending.

---

## 7. If We Were Shipping For Money Tomorrow

If SPB had to convince painters to spend $55 tomorrow, all of these
must be true:

1. **The first 90 seconds produces an "I haven't seen this before"
   moment.** Today: false. Closest fix: Sting's curated shelf + first-
   stroke flow. Two weeks.
2. **The PSD round-trip works on a real Photoshop file end-to-end.**
   Today: unverified. Closest fix: Pillman + Luger gauntlet. Five days.
3. **The render preview updates within 200ms of any change.** Today:
   unmeasured. Closest fix: Hawk benchmark + tune. Six days.
4. **The brand-tier (SHOKK Series) renders flagship-quality across all
   25 entries.** Today: 20 of 25. Fix: level the 5 generics or demote.
   Three days.
5. **No saved zone config can silently corrupt due to id collision.**
   Today: 8 known collision ids. Fix: Windham's migrator + rename.
   Four days.
6. **The catalog has a curated front shelf, not a firehose.** Today:
   ~1,800 tiles all on the front. Fix: Raven cull + Sting reorganize.
   Six days.
7. **Every error message tells the painter what to do next.** Today:
   mixed; some are stack-trace-flavored. Fix: Sting toast voice. Three
   days.
8. **Server failures are visible and recoverable.** Today: silent
   spinner. Fix: Animal failure surface. Five days.
9. **The painter can press Ctrl+Z and undo the last thing they did,
   regardless of which subsystem owns it.** Today: four parallel undo
   stacks. Fix: Flair unified undo. Six days.
10. **The "Proven at Runtime" badge page is public, signed, and
    embarrassingly thorough.** Today: TOOL_TRUST_MATRIX exists
    internally. Fix: Bockwinkel publishes. Three days.

Total cost if done sequentially: ~50 days. With six-way parallelism:
~25 days. That's the deadline. Hit it and $55 is a bargain. Miss it
and the price is the wrong conversation.

---

**Hennig's last word:**
*"Ricky, the gap is not technical. It is courage. We have the engine.
We have the catalog. We have the trust scaffolding. What we have not
yet had is somebody on this team — including us — sitting down with
the running app for two hours and writing down everything that felt
wrong. Until that happens, every shift, every fix, every audit is
guess-work in the dark. Open the app tomorrow. Paint a livery. Tell us
what was wrong. We'll fix it. Then ship it for $55."*

---

**Meeting adjourned.**

Filed in repo: `docs/HEENAN_FAMILY_BOARD_MEETING_2026_04_19.md`.
