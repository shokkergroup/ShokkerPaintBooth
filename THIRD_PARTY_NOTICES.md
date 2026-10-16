# Third-party notices

## PhotoCraft (algorithms ported to JavaScript)

- Project: https://github.com/storytold/photocraft
- Licence offered: MIT OR Apache-2.0; **elected: MIT**.
- The ArtCraft / PhotoCraft names and logos are trademarks and are not licensed; no fonts, assets or brand material are used.

Ported files (algorithm -> Shokker Paint Booth file):

- PORT-W3 (2026-10-09): crates/algo/src/transform.rs (warp_surface, Homography, Catmull-Rom) and crates/algo/src/resample.rs (taps, pre-reduction) -> `js/canvas/layer/pc-warp.js`

```
MIT License

Copyright (c) 2026 ArtCraft Team and the PhotoCraft contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## PhotoCraft (external editor for "Edit in PhotoCraft")

- Project: https://github.com/storytold/photocraft (v0.5.0 tested). Licence offered: MIT OR Apache-2.0. Bundled unmodified since 2026-10-09 (owner decision): `tools/photocraft/photocraft.exe` with its LICENSE-MIT, LICENSE-APACHE and the OFL font licences beside it. The painter may still point SPB at their own copy. SPB only writes/reads layered PSD files and launches `photocraft.exe`; no PhotoCraft code is linked or copied by this feature (`server_routes/photocraft_*.py`, `js/canvas/layer/photocraft-roundtrip.js`).
- If a PhotoCraft build is ever shipped with SPB, ship its `LICENSE-APACHE`, `LICENSE-MIT`, `OFL-*.txt` files and this NOTICE text with it:

```
PhotoCraft
Copyright (c) 2026 ArtCraft Team and the PhotoCraft contributors.
Licensed under the MIT License or the Apache License, Version 2.0, at your option
(LICENSE-MIT, LICENSE-APACHE).

The ArtCraft name, wordmark and logos in docs/brand/ are trademarks of the ArtCraft Team. They are
not open source and are not covered by the license above.
```


## Ported files (lane PORT-W1, 2026-10-09)
- crates/algo/src/selection.rs, selection_blur.rs -> js/canvas/pc-selection-core.js (expand/contract/border via Euclidean distance transform, feather, smooth, anti-aliased polygon/ellipse, wand_region span fill + 3x3 edge AA)

- js/canvas/pc-stroke.js and js/canvas/layer/pc-poisson.js (PORT-W2, 2026-10-09): brush stroke coverage model and Poisson healing ported from PhotoCraft crates/paint (retouch.rs, dynamics.rs); same PhotoCraft MIT/Apache-2.0 terms as above.
- js/canvas/zone/pc-magnetic.js and js/canvas/zone/pc-colorrange.js (PORT-W4, 2026-10-09): magnetic lasso and Color Range ported from PhotoCraft crates/algo (magnetic/, colour range); same PhotoCraft MIT/Apache-2.0 terms as above.
- js/canvas/zone/pc-quickselect.js (PORT-W6, 2026-10-09): Quick Select brush ported from PhotoCraft crates/algo/src/segment (quick.rs, gmm.rs, maxflow.rs Boykov-Kolmogorov, mod.rs grid_cut/finish_region); same PhotoCraft MIT/Apache-2.0 terms as above.
- js/canvas/pc-stroke.js additions (PORT-W5, 2026-10-09): Smudge (crates/paint/src/retouch.rs `Smudge`, premultiplied carry buffer), aliased Pencil tip, History Brush mix_premultiplied, solid-colour / tiled-source dabs and the zone-mask eraser on the same coverage-buffer model; rect-marquee feather-new-rectangle-only via js/canvas/pc-selection-core.js; same PhotoCraft MIT/Apache-2.0 terms as above.
