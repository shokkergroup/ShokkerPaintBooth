# SPB 2048 Visual Scale Rules

These are hard visual rules for SPB finish rebuilds. They exist because a finish
that looks dramatic as a full square can look crude once wrapped across a car.

## Scale Law

- Default to microscopic and fine detail first. If a visible element is not an
  intentional hero feature, it should read as texture at 2048, not as a giant
  poster shape.
- When a finish seems detailed enough, push the detail density another 25-40%.
- Large panels, checkerboards, halos, bubbles, blocks, stripes, rings, cells, or
  grids are failures unless the finish name specifically demands a large form.
- Repeating one generator with swapped colors is a failure. Shared helpers are
  allowed only when every finish receives a distinct field, rhythm, focal logic,
  and spec response.
- Specs must follow the paint. The M/R/CC channels should trace meaningful
  structures, hot edges, recessed shadows, microflake, scratches, gloss pockets,
  and local material changes. Flat two-color green/yellow spec maps are failures
  for expressive finishes.
- Hidden spec motifs and Easter eggs must obey car-scale physics. They should be
  faint, fine, and angle-revealed through metallic, roughness, or clearcoat
  response, not giant poster art that dominates the car.
- Larger hidden shapes must be built from microstructure: flecks, etched strokes,
  polish direction shifts, clustered sparkle, relief dots, contour ticks, or
  channel variance. The viewer should discover them, not read them instantly.

## Render Budget

- Under 3 seconds at 2048 is preferred.
- Over 5 seconds at 2048 is a red flag and needs a redesign or cache-aware
  optimization.
- Do not buy quality with brute-force per-pixel loops when vectorized fields,
  cached low-resolution carriers, masks, or seeded texture layers can do it.

## Audit Gate

For expressive finishes, Workbench/scorecard warnings are actionable:

- `macro-dominated/too-large`: big forms are carrying the look.
- `needs 2048 micro-detail`: fine residual detail is too weak.
- `blocky/coarse field`: visible repeated blocks or panels.
- `flat metallic channel`: the spec map is not contributing enough.
- `pasted hidden motif`: the Easter egg is obvious surface art instead of a
  material-driven light reveal.

Any category rebuild that produces these warnings should not be handed to owner
review as "done" unless the finish is intentionally quiet or industrial.
