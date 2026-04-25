# Shokker Paint Booth — League Templates

This folder is where sim-racing leagues drop their template configurations so drivers can build league-compliant liveries in Shokker Paint Booth (SPB) without guesswork.

## What's a League Template?

A league template is a JSON config file plus a small asset bundle (required logos, contingency stacks, windshield banners) that encodes a league's look-and-feel rules:

- Which body zones must appear (windshield banner, B-pillar contingency, primary-sponsor door, roof stripe).
- Which bases and patterns are approved vs. banned.
- Which color palette is allowed.
- How numbers must be styled.
- How the contingency stack is arranged.
- How liveries must be named and submitted.
- What penalties apply for non-compliance.

Drivers import the config into SPB and the tool enforces the rules automatically: warnings fire on banned bases, required zones block save-to-league until filled, the contingency stack is locked if the league specifies it.

## Using a League Template

1. **Admins:** Copy `league_template_config.json` to your league's shared space. Fill in every field marked `example_`. Replace supplied asset paths with your real logos and decal packs. Distribute to drivers (Discord, shared drive, GitHub).
2. **Drivers:** Download the league's config and assets. In SPB, go to **File → Import League Config** and select the JSON. SPB validates the config, loads the required zones, locks the contingency stack, and applies the palette filter.
3. **Submission:** Once the driver's livery is approved within SPB (all required zones filled, all checks pass), export the final `.shokker` file using the league's naming convention. Submit per the league's process.

## Setting Up a League Config

The template file `league_template_config.json` is heavily commented via its field names. Fill in:

- `league_name`, `league_slug`, `season`, `series_tier` — basic identity.
- `regulations_url` — where drivers read the full rules.
- `contact` — who to reach for approvals.
- `required_zones` — list every zone that must be on every livery. Specify layer, minimum size, and whether an asset is supplied.
- `approved_bases` / `banned_bases` — control the base library the driver sees.
- `approved_patterns` / `banned_patterns` — same for patterns.
- `color_palette` — tight palette = consistent league look. Loose palette = more driver expression.
- `number_style` — size, font, placement for the race number.
- `contingency_stack` — supply a pre-built stack file or specify a layout and let drivers build.
- `naming_convention` — enforce file-naming rules so submissions are easy to sort.
- `submission` — deadline, channel, review duration, max revisions.
- `penalties_for_non_compliance` — what happens if rules are broken.
- `optional_features` — toggle per-league flexibility: allow custom primary sponsors, helmet crossover, custom monolithics.
- `template_liveries_provided` — starter `.shokker` files drivers can import and tweak.

## Sharing With Drivers

Package the template as a zip:

```
example-racing-league-2026-spring.zip
├── league_template_config.json
├── assets/
│   ├── league_logo_windshield.png
│   ├── contingency_stack.shokker
│   ├── series_title_sponsor_roof.png
│   ├── template_clean_stripe.shokker
│   ├── template_split_halves.shokker
│   └── template_minimalist.shokker
└── README.md (brief driver instructions)
```

Upload to your league's Discord pinned message or GitHub release. Link it in the welcome message for new drivers.

## Good League-Template Practices

- **Keep it tight for week-to-week consistency.** Fewer allowed colors = stronger league identity.
- **Keep it loose for personal-expression leagues.** More allowed bases and patterns = happier drivers.
- **Supply templates.** Drivers who have never used SPB will build better liveries when they start from a clean template than from a blank canvas.
- **Enforce the contingency stack.** The B-pillar is where sponsorships live — protect the layout by locking it.
- **Review liveries every week.** Build a rotation of two or three admins who split approvals. Fast turnaround keeps drivers happy.
- **Iterate the template across seasons.** Each season is a chance to refresh the series title-sponsor stripe, refresh approved colors, and clean up banned bases as SPB adds new content.

## Contributing Templates

If your league has a well-tuned config, consider contributing it as an example for other leagues. Submit via pull request or share on the SPB Discord under `#league-templates`. Remove private sponsor references before sharing.

## Multi-Series Leagues

If your league runs multiple series (Open-wheel + GT3, for example), create one config per series. Name them:

```
example-racing-league-openwheel-2026-spring.json
example-racing-league-gt3-2026-spring.json
```

SPB supports switching between active league configs via the league selector in the top bar.

## Feedback

Found a gap in the config schema? Open a feature request on GitHub or post in the SPB Discord `#feature-requests` channel. The schema is versioned (`"schema": "spb-league-config-v1"`) so we can evolve without breaking existing templates.

---

Templates exist so every driver in your league shows up looking like they belong together. Use the power responsibly — a well-designed template turns weekly submissions from chaos into a parade.
