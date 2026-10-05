---
name: spb-painting
description: Use when a buyer wants to inspect, design, edit or review an iRacing paint in an already-running Shokker Paint Booth through its local MCP bridge. Requires the SPB bridge tools; ordinary image generation and editing unrelated files do not use this workflow.
---

# Shokker Paint Booth painting

Work on the buyer's requested car and document. The existing SPB application owns
the document, render engine, catalog, saved projects and exports. Use its actual
MCP tools and current schemas, including the host's plugin prefix if present.
This package supplies workflows and a local connection; it does not embed SPB
in ChatGPT or create a cloud renderer.

## Connect and understand

1. Call `spb_status` first. If disconnected, explain the returned setup issue.
   The buyer needs SPB running in Pro mode and the assistant bridge enabled in
   the AI panel settings. A cloud-only host cannot launch this local Node server.
2. Read `spb_get_state`, `spb_get_car_map` and `spb_get_zones` as needed, keeping
   requests bounded. Discover tool schemas instead of guessing arguments.
3. Check the actual paint with `spb_preview`. Use named car parts backed by the
   current map. If required parts are missing, use `spb_request_parts` and let
   the buyer supply them before dependent painting. Do not guess UV coordinates.
4. Identify whether the request concerns existing paint, a new scheme, a zone,
   a layer, or material appearance. Preserve existing work outside the request.
   Select stable `zone_id`, unique `zone_name`, or guarded index targets where
   the tool schema supports them. Refresh state after a stale-target error.

## Design and edit

- Find real catalog entries through `spb_find_finishes`, `spb_finish_details`,
  `spb_find_patterns` or `spb_find_spec_patterns`. Use returned IDs. Ask
  `spb_manual` for help with an unfamiliar operation. Never invent finish IDs
  or promise a feature that is absent from tool discovery.
- Inspect `spb_design_recipes` before using `spb_apply_scheme` for a whole-car
  design. Make the requested change using the narrowest suitable zone/layer
  tool. Do not reset the document to accomplish a small edit.
- Respect car orientation, numbers, sponsor artwork and the buyer's supplied
  assets. Do not treat a flat UV preview as proof of alignment on the 3D car.
- Paint changes and material changes are different. Spec channels encode
  metalness, roughness and clearcoat; they are not decorative RGB paint colors.
  Read current material/tool guidance before choosing values. Fine details and
  varied material shades are SPB defaults when applicable, never a reason to
  silently replace an existing approved design.
- A requested spec-only edit must preserve the current paint. The repository's
  October 2 acceptance recorded a `color:"source"` overlay restoring original
  source paint after a repaint. Treat keep-colors behavior as unqualified until
  that acceptance passes. Inspect before/after previews; if the edit changes
  paint unexpectedly, use `spb_undo` for the assistant's own latest change,
  verify restoration and report the failure. Do not overwrite intervening work.
- Let the existing editing lease and disabled-bridge checks govern writes.
  On a lock/takeover error, explain the returned state; do not bypass the lock,
  expose pairing tokens or turn on automatic approvals.

## Verify and report

After a change, obtain `spb_preview` with the appropriate paint/spec/parts options
and inspect the returned images. A successful tool call is not proof that the
appearance is correct. If the model cannot receive or inspect images, say visual
verification is unavailable and use measured state only; never claim to have
seen the paint. Where available, use `spb_look_at_paint` for the requested region.

Report what actually changed and any unresolved visual issue. Verify saved/exported
artifacts before saying they exist. Do not call a `.shokker` project a deployable
paint image. Use discovered app help for supported export workflows; do not
invent a save/export tool. Closing a dialog or finishing a preview is not export
verification. Keep credentials and unrelated buyer files out of tool results.

If the in-app composer remains disabled after an external call, disclose it and
use current SPB support guidance. This pilot inherits app behavior and bugs; its
package tests cannot qualify the entire renderer or export pipeline.
