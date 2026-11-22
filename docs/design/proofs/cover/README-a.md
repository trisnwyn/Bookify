# Part A — four disposable cover-layout proofs

**Status:** disposable reference study for user review. Not approved, not a
production cover, not wired into the Bookify build. This directory is shared
with another proof agent; every file here uses the unique `part-a` prefix.

## What this is

Four A4 cover pages built from the **composition topology only** of pages 1–4
of `/home/tris/Downloads/Cover.pdf`:

1. centred top metadata; illustration above the title, offset right; title and
   secondary metadata in the lower-left half; centred foot metadata;
2. centred top metadata; centred illustration upper/middle; centred title and
   supporting metadata below; centred foot metadata;
3. centred top metadata; title around the upper-middle with supporting metadata
   above and below; a second metadata line low on the page; centred foot
   metadata; no illustration;
4. centred top metadata; title and supporting metadata near the top; a wide
   illustration after the title; centred foot metadata.

**Not taken from the reference:** no measurement, page position, font family,
font size, leading, colour, image asset or copy. The reference's display-scale
illustrations, sans-serif type and near-edge top margin are not reproduced.
Everything is reflowed inside the current Bookify 60 pt A4 text block.

**Placeholders only:** `Cover`, `Additional information`,
`Decorative illustration`. No title, author, date, institution, course, ISBN,
edition, city or other factual content is invented. The illustration is a local
proof-only vector panel (pale fill, hairline border, two diagonals, searchable
label); there is no raster asset.

## Files

| File | Purpose |
| --- | --- |
| `part-a.typ` | Standalone proof source. Imports the current theme read-only. |
| `part-a.pdf` | Four-page A4 proof, one composition per page. |
| `pages/part-a-page-1.png` … `-4.png` | 150 dpi renders for inspection. |
| `part-a-contact.png` | 2 × 2 contact sheet, pages 1–2 top, 3–4 bottom. |
| `part-a-measure.py` | Disposable measurement helper; writes `part-a.json`. |
| `part-a.json` | Tokens, per-object boxes, margins, overlap checks, hashes. |
| `README-a.md` | This review record. |

## Current Bookify values used

Read from `typst/theme.typ` and the A4 page setup at this checkout. The theme,
templates and product cover were not edited.

| Value | Current value | Use in this proof |
| --- | --- | --- |
| Paper | A4, **595.276 × 841.890 pt** | All four pages |
| `tokens.measure.page_height` | **297 mm** (cover token) | Fixed cover block height |
| `tokens.space.page_margin` | **60 pt** all sides | Reflowed inside the text block |
| Text block | **475.276 × 721.890 pt** | All content is inside it |
| `tokens.measure.body` | **475.276 pt** | Full-measure page-4 panel |
| Font | **Spectral** (Regular / Medium / Italic) | Every visible glyph |
| `tokens.type.cover_title` | **34 pt** | `Cover` |
| `tokens.leading_extra.cover_title` | 18.56 pt extra → **41.0 pt pitch** | Title line |
| `tokens.type.cover_subtitle` | **12.6 pt**, italic | `Additional information` support line |
| `tokens.leading_extra.lead` | 9.40 pt extra → **17.716 pt pitch** | Subtitle line |
| `tokens.type.cover_meta` | **8.4 pt** | Top, secondary and foot metadata; panel label |
| `tokens.leading_extra.small` | 6.46 pt extra → **12.0 pt pitch** | Meta lines |
| `tokens.type.cover_index` | 8.6 pt | Not set as type; only its rule token is used |
| `tokens.rule.figure_stroke` | **0.55 pt** | Panel outline |
| `tokens.rule.cover_index` | **0.4 pt** | Panel diagonals and label chip |
| `tokens.ink.text` | `#000000` | Title |
| `tokens.ink.grey_1` | `#4d4d4d` | Metadata, subtitle, panel label |
| `tokens.ink.grey_3` | `#a8a8a8` | Panel border and diagonals |
| `tokens.ink.pale` | `#e6e6e6` | Panel fill |
| `tokens.space.after_block` | 5.4 pt | Top lift and foot lift |

No accent colour is used. The placeholder is grayscale, not the reference's
blue-grey fill.

Panel sizes (declared layout boxes):

| Page | Declared panel | Placement |
| --- | ---: | --- |
| 1 | **342.24 × 352 pt** (0.72 × measure) | Right-aligned to the text block |
| 2 | **332.70 × 340 pt** (0.70 × measure) | Centred |
| 4 | **474.726 × 330 pt** (measure − 0.55 pt stroke) | Centred; outer stroke reaches both 60 pt edges |

## Per-page object boxes

All values are points from `part-a.json`, measured from the rendered PDF and
150 dpi PNG. Text boxes come from `pdftotext -bbox-layout` and are **line
boxes** (they include the face's ascender/descender allowance), not glyph ink.
The raster ink boxes are thresholded from the page PNG and are reported
separately.

### Page 1 — reference composition 1

| Object | x0–x1 | y0–y1 | Type size (measured / token) |
| --- | ---: | ---: | --- |
| Top meta | 254.48–340.79 | 62.05–74.83 | 8.67 / 8.4 pt |
| Title `Cover` | 60.00–149.56 | 505.62–557.37 | 34.02 / 34 pt |
| Supporting subtitle | 60.00–179.94 | 558.72–577.89 | 12.68 / 12.6 pt |
| Secondary meta | 60.00–146.31 | 587.83–600.61 | 8.67 / 8.4 pt |
| Panel label | 322.21–406.11 | 292.94–305.73 | 8.67 / 8.4 pt |
| Panel | 193.03–535.12 | 123.08–474.97 | 342.08 × 351.89 |
| Panel outer ink | 192.76–535.39 | 122.81–475.25 | 0.55 pt stroke |
| Foot meta | 254.48–340.79 | 767.19–779.98 | 8.67 / 8.4 pt |

Text bbox 60.00–406.11 × 62.05–779.98. All ink 59.48–535.32 × 64.32–776.13.
Page-trim clearances: left 59.48, right 59.96, top 64.32, bottom 65.76 pt.
The panel is right-aligned; its 0.55 pt centred stroke reaches 0.11 pt past the
nominal text-block edge but 59.96 pt from the trim. No clipping.

### Page 2 — reference composition 2

| Object | x0–x1 | y0–y1 | Type size (measured / token) |
| --- | ---: | ---: | --- |
| Top meta | 254.48–340.79 | 62.05–74.83 | 8.67 / 8.4 pt |
| Panel label | 255.69–339.59 | 278.94–291.73 | 8.67 / 8.4 pt |
| Panel | 131.16–463.64 | 114.92–454.81 | 332.49 × 339.89 |
| Panel outer ink | 130.88–463.92 | 114.65–455.09 | 0.55 pt stroke |
| Title `Cover` | 252.86–342.42 | 499.62–551.37 | 34.02 / 34 pt |
| Supporting subtitle | 237.67–357.61 | 552.72–571.89 | 12.68 / 12.6 pt |
| Foot meta | 254.48–340.79 | 767.19–779.98 | 8.67 / 8.4 pt |

Text bbox 237.67–357.61 × 62.05–779.98. All ink 130.95–463.84 × 64.32–776.13.
Page-trim clearances: left 130.95, right 131.44, top 64.32, bottom 65.76 pt.
The 10 pt gap between title and subtitle removes the line-box collision
measured at 8 pt; the box gap is now 1.35 pt.

### Page 3 — reference composition 3

| Object | x0–x1 | y0–y1 | Type size (measured / token) |
| --- | ---: | ---: | --- |
| Top meta | 254.48–340.79 | 62.05–74.83 | 8.67 / 8.4 pt |
| Title `Cover` | 252.86–342.42 | 161.50–213.25 | 34.02 / 34 pt |
| Supporting subtitle | 237.67–357.61 | 218.60–237.77 | 12.68 / 12.6 pt |
| Low second meta | 254.48–340.79 | 580.71–593.49 | 8.67 / 8.4 pt |
| Foot meta | 254.48–340.79 | 767.19–779.98 | 8.67 / 8.4 pt |

No illustration, matching the reference. Text bbox 237.67–357.61 ×
62.05–779.98. All ink 236.96–357.36 × 64.32–776.13. Page-trim clearances:
left 236.96, right 237.92, top 64.32, bottom 65.76 pt. The title is at ~25 % of
page height and the low meta at ~70 %, preserving the reference's large central
white field at the current 34 pt title size.

### Page 4 — reference composition 4

| Object | x0–x1 | y0–y1 | Type size (measured / token) |
| --- | ---: | ---: | --- |
| Top meta | 254.48–340.79 | 62.05–74.83 | 8.67 / 8.4 pt |
| Title `Cover` | 252.86–342.42 | 93.50–145.25 | 34.02 / 34 pt |
| Supporting subtitle | 237.67–357.61 | 146.60–165.77 | 12.68 / 12.6 pt |
| Panel | 60.16–534.63 | 242.11–571.93 | 474.47 × 329.82 |
| Panel outer ink | 59.89–534.91 | 241.84–572.21 | 0.55 pt stroke |
| Panel label | 255.69–339.59 | 400.94–413.72 | 8.67 / 8.4 pt |
| Foot meta | 254.48–340.79 | 767.19–779.98 | 8.67 / 8.4 pt |

Text bbox 237.67–357.61 × 62.05–779.98. All ink 59.96–534.84 × 64.32–776.13.
Page-trim clearances: left 59.96, right 60.44, top 64.32, bottom 65.76 pt.
The panel is 474.47 pt wide against a declared 474.726 pt (raster rounding);
its outer stroke sits on the 60 pt margins, not through them.

## Verification

Commands used from the repository root, offline:

```sh
./tools/typst/typst compile \
  --ignore-system-fonts --ignore-embedded-fonts \
  --font-path assets/fonts \
  --package-path vendor/typst --package-cache-path .cache/empty-pkg \
  --creation-timestamp 1750000000 --root . \
  build/design/cover/part-a.typ build/design/cover/part-a.pdf

pdftoppm -png -r 150 build/design/cover/part-a.pdf \
  build/design/cover/pages/part-a-page

montage build/design/cover/pages/part-a-page-1.png \
        build/design/cover/pages/part-a-page-2.png \
        build/design/cover/pages/part-a-page-3.png \
        build/design/cover/pages/part-a-page-4.png \
        -tile 2x2 -geometry 620x877+24+24 -background white \
        build/design/cover/part-a-contact.png

.venv/bin/python build/design/cover/part-a-measure.py
```

Measured results:

- `pdfinfo`: **4 pages**, **595.276 × 841.890 pt** (A4), PDF 1.7.
- `pdffonts`: three embedded subset Unicode faces — **Spectral-Regular,
  Spectral-Medium, Spectral-Italic**. No system font. No SemiBold because no
  visible text uses 600.
- `pdftotext`: all four pages expose searchable text. Page 1:
  `Additional information / Decorative illustration / Cover / Additional
  information / Additional information / Additional information`; page 2 and
  page 4 carry the same placeholders with their own counts; page 3 has no
  illustration label, as intended.
- All text line boxes are inside **60 ≤ x ≤ 535.276** and **60 ≤ y ≤ 781.890**.
- **No text–text overlap** and **no text–illustration overlap** (empty arrays in
  `part-a.json`). The panel label is inside the panel and is excluded from the
  collision check, as the deliberate content of the placeholder.
- Raster page-trim clearance is at least **59.48 pt** on every side; no page
  edge is touched, no content is clipped.
- Top text clearance to the 60 pt margin: **2.05 pt**. Bottom text clearance to
  the 781.89 pt text-block bottom: **1.91 pt**.
- The PDF compiles byte-identically on a second run (`cmp` exit 0).

Font-size numbers in `part-a.json` are measured from the `pdftohtml` font table
(1.5 px/pt rounding): 34.02, 12.68, 8.67. The actual theme tokens are **34,
12.6, 8.4 pt**; the difference is the measurement rounding, not a layout value.

## Hashes

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `part-a.pdf` | 24,259 | `d690dbc9a5cfcb90d18a0140b7029b31e434caded0076d8564ec938ffa73ccb3` |
| `part-a.typ` | 7,669 | `0e127fc0acc7a75b4b600d68b41544b9701fc78c541a1dc4d5685a10b7f8e67c` |
| `part-a-measure.py` | 16,715 | `356c38ef64b3d4ae829ceea13389046d6f6e5fecd68add67942a71bcfe58f193` |
| `part-a-contact.png` | 43,567 | `b35d60a41b460c02dc99c0b5e16a2b8e49cd02fd0bb32eb5cd6e24faa837d1b8` |
| `pages/part-a-page-1.png` | 39,599 | `04574794bf44be4ff46516ce771ae0af3e9b2db3037a9671de630858a2509ce6` |
| `pages/part-a-page-2.png` | 34,805 | `0d0dc04081c5d32c4cb560e7a8b4630cff2c1c013f861f005a6ab0b30ac20a09` |
| `pages/part-a-page-3.png` | 28,337 | `981dca4a11f6f7805437f78c687e6d2221cc0f91416011412b59672178f221e6` |
| `pages/part-a-page-4.png` | 48,517 | `ee6196d56389f3fb7e1a8c7fc15c6fcabc252847fdabcc46113dfb4f1bd9e178` |
| `part-a.json` | 18,971 | `ef9b1d192ea8bd32779a63c3ee9b627ba47dc29cbc86b034024b9c64f2849afb` |

`part-a.json` contains the same artifact hashes plus per-object boxes and the
machine-readable checks. The README itself is documentation and is not
self-hashed.

## Observations

- **Page 1** reads closest to reference 1: the asymmetric right-hand panel above
  a left title block, secondary meta under the title, and a centred foot line.
  The current 34 pt title is much smaller than the reference's display type, so
  the composition relies on white space and position rather than scale.
- **Page 2** is the most conventional book-cover arrangement: symmetric panel,
  centred title, one support line, generous lower white field. It is stable at
  the current 475.28 pt measure.
- **Page 3** is the pure typographic variant. With a 34 pt title the page is
  intentionally airy; the low second meta anchors the lower third. It carries
  no illustration, matching the parsed reference.
- **Page 4** puts the title above a near-full-measure landscape panel. The
  current title no longer competes with the panel; the panel is the dominant
  object and the foot meta closes the page.
- The only ornament outside text and the panel is the 0.55 pt panel outline and
  the 0.4 pt diagonals. No cover rule, accent colour or reference colour is
  introduced.
- Because the current cover typography is 34/12.6/8.4 pt, all four pages read
  as quiet, book-like compositions rather than poster-like reference clones.
  That is the intended result of reflowing topology onto current house metrics.

## Boundary record

- Not changed: `typst/theme.typ`, `typst/blocks.typ`,
  `typst/templates/book.typ`, `schemas/`, `src/`, `content/`, `tests/`,
  `packaging/`, `docs/`, the production cover and the product tokens.
- No global package install, no network, no new dependency, no system font.
- `build/` output is disposable. Only `build/design/cover/part-a.*` and
  `build/design/cover/pages/part-a-page-*.png` belong to this proof.
- `part-a.pdf` is an independent proof PDF, not the product cover and not
  included in a book build.
