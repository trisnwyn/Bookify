# A1 layout proof — four compositions (disposable)

**Status:** proof for user review. Not approved, not shipped, not a production
template. A1 remains `brainstorm` in the design map.

This directory holds a standalone Typst proof of the four A1 body-page
compositions in the task brief. Each composition is one A4 page. Only the
**layout/composition topology** comes from the reference description. No font
face, type size, margin or measure is taken from the reference: every visual
value is read from the current Bookify theme (`/typst/theme.typ`).

All prose is neutral *lorem ipsum*. No source asset, factual claim, product
schema, template, source file or product numbering implementation is used or
changed.

## Files

| File | Purpose |
| --- | --- |
| `a1-proof.typ` | Standalone proof source. Imports the current theme read-only. |
| `a1-proof.pdf` | Four-page proof PDF, one composition per page. |
| `pages/page-1.png` … `pages/page-4.png` | 150 dpi renders for inspection. |
| `contact-sheet.png` | 2 × 2 contact sheet: pages 1–2 top, 3–4 bottom. |
| `a1-proof.gaps.json` | Measured heading-to-content white bands. |
| `a1-proof.measure.json` | Derived text/ink bounding boxes and file hashes. |
| `README.md` | This review record. |

## The four compositions

| Page | Composition | What is shown |
| --- | --- | --- |
| 1 | Reference composition 1 | Chapter heading, full-width prose, a **centred visual at 430 pt** (`figure_width`), its caption, full-width continuation. |
| 2 | Reference composition 2 | Same sequence with a **full-measure visual at 475.28 pt** (`plate`), caption, full-width continuation. |
| 3 | Reference composition 3 | Full-width opening paragraph, then prose in the left region beside a **218.63 pt** visual on the right (0.46 × measure). |
| 4 | Reference composition 4 | Visual left, prose right, then a **full-width paragraph below** both columns. |

The placeholder visuals are one stroked pale rectangle plus a text label. There
are no image assets and no charts; the boxes are vector placeholders only.

## Confirmed structural hierarchy

The proof applies the user-confirmed numerical hierarchy as literal sample
content. It is structure, not a change to font, measure or the product's heading
counter.

| Level | Form used | Where |
| --- | --- | --- |
| Chapter title | `Chapter 1: Full-width prose with a centred visual` | Page 1 h1 |
| First-level heading | `1. Full-width opening` | Page 1 h2 (same form on pages 2–4) |
| Second-level heading | `1.1 Centred visual` | Page 1 h3 (same form on pages 2–4) |
| Continuing branch | `1.1.1 Full-width continuation` | Page 1 h3 |
| Terminal branch | `2.1 a) Full-width continuation` | Page 2 h3 |
| Chapter title | `Chapter 2: …`, `Chapter 3: …`, `Chapter 4: …` | Pages 2–4 h1 |
| Later levels | `1.1.1.1`, … when a branch continues | Rule recorded; not instantiated because no shown branch continues past one deeper level |

Numbering is continuous and never omits a level: page 1 shows
`1 → 1.1 → 1.1.1`; page 2 shows `2 → 2.1 → 2.1 a)`; page 3 shows
`3 → 3.1`; page 4 shows `4 → 4.1` and `4.2`. The numbers are typed proof text,
not an implementation of `heading-numbering` or any product counter.

## Fixed blank-line rule

**Rule:** every heading must clear the following content by at least one clearly
visible body blank line. This is applied to all 15 headings, including the
Chapter 1 title and every numbered body subhead.

- Current body line pitch: **15.30 pt** (`10.1 pt` type + `8.63 pt` extra leading).
- Proof-local heading block below: **19.93 pt** =
  `tokens.space.between_paragraphs` (14.03) + `tokens.space.after_block` (5.4) +
  `tokens.space.heading_clearance` (0.5).
- Proof-local Chapter 1 above: **22.40 pt** =
  `tokens.space.before_heading` (17) + `tokens.space.after_block` (5.4), so the
  proof label also keeps a blank line from the chapter title.
- Measured on a 300 dpi raster as the vertical white band between the heading's
  lowest ink and the next content's highest ink. Raster resolution: 0.24 pt.
- **Minimum measured heading-to-content gap: 15.84 pt** (0.54 pt above one body
  line). Maximum: 30.24 pt. All 15 headings pass.
- Preceding bands, including a preceding heading, also clear headings: 17.76–30.24 pt.

| Page | Heading | Following content | Measured gap (pt) |
| --- | --- | --- | ---: |
| 1 | `Chapter 1: …` | `1. Full-width opening` | 30.24 |
| 1 | `1. Full-width opening` | body prose | 15.84 |
| 1 | `1.1 Centred visual` | centred visual box | 19.68 |
| 1 | `1.1.1 Full-width continuation` | body prose | 18.72 |
| 2 | `Chapter 2: …` | `2. Full-width opening` | 30.24 |
| 2 | `2. Full-width opening` | body prose | 15.84 |
| 2 | `2.1 Full-measure visual` | full-measure visual box | 19.68 |
| 2 | `2.1 a) Full-width continuation` | body prose | 17.28 |
| 3 | `Chapter 3: …` | `3. Full-width opening` | 24.72 |
| 3 | `3. Full-width opening` | body prose | 15.84 |
| 3 | `3.1 Prose in the left region …` | two-column grid | 16.08 |
| 4 | `Chapter 4: …` | `4. Visual and prose` | 24.72 |
| 4 | `4. Visual and prose` | `4.1 Prose in the right region …` | 20.88 |
| 4 | `4.1 Prose in the right region …` | two-column grid | 16.08 |
| 4 | `4.2 Full-width paragraph below` | body prose | 15.84 |

The same data is machine-readable in `a1-proof.gaps.json`.

## Current Bookify tokens used

Read from `typst/theme.typ` at the current checkout. The proof does not override
the theme file; it reads its values. Heading blocks are local proof blocks that
reuse the current type/leading tokens.

| Token | Value | Role in proof |
| --- | --- | --- |
| Paper | A4, 595.276 × 841.89 pt | All pages |
| `tokens.space.page_margin` | 60 pt | All four sides |
| `tokens.measure.body` | 475.28 pt | Text measure; full-width prose |
| Font family | `Spectral` | Latin text, headings, captions |
| Body type | 10.1 pt | `tokens.type.body` |
| Body leading | 8.63 pt extra → **15.30 pt total pitch** | `tokens.leading_extra.body` |
| h1 type / pitch | 25 pt / **30.00 pt total** | `tokens.type.h1`, `leading_extra.h1` 13.5 pt |
| h2 type / pitch | 12.6 pt / **16.50 pt total** | `tokens.type.h2`, `leading_extra.h2` 8.18 pt |
| h3 type / pitch | 10.3 pt / **14.00 pt total** | `tokens.type.h3`, `leading_extra.h3` 7.20 pt |
| Caption type / pitch | 8.2 pt / **11.20 pt total** | `tokens.type.caption`, `leading_extra.caption` 5.79 pt |
| Small label type / pitch | 8.4 pt / **12.00 pt total** | `tokens.type.small`, `leading_extra.small` 6.46 pt |
| `tokens.measure.figure_width` | 430 pt | Page 1 centred visual |
| `tokens.measure.plate` | 475.28 pt | Page 2 full-measure visual |
| `tokens.measure.side_fraction` | 0.46 | Side visual = **218.6288 pt** |
| `tokens.space.side_gutter` | 16 pt | Side grid gutter; prose side = **240.6512 pt** |
| `tokens.rule.figure_stroke` | 0.55 pt | Placeholder outline |
| `tokens.ink.pale` | `#e6e6e6` | Placeholder fill |
| `tokens.ink.grey_1` | `#4d4d4d` | Captions and labels |
| `tokens.ink.grey_2` | `#7a7a7a` | Right-hand proof label |
| `tokens.ink.text` | `#000000` | Body and headings |
| `tokens.space.before_heading` | 17 pt | h1 separation above |
| `tokens.space.after_heading` | 4.5 pt | h1 minimum below |
| `heading-below(25 pt)` | **7.454 pt** | Theme-derived h1 below before the proof rule |
| `tokens.space.before_h2` | 32 pt | Section heading above |
| `tokens.space.before_h3` | 25 pt | Subsection heading above |
| `tokens.space.after_block` | 5.4 pt | Figure/label separation |
| `tokens.space.between_paragraphs` | 14.03 pt literal | Theme value: `leading_extra.body + 5.4 pt` |
| Rendered paragraph step | **20.70 pt** | Measured baseline-to-baseline; one 15.30 pt pitch + 5.40 pt |
| `tokens.space.after_figure` | 14 pt | Figure block below |
| `tokens.space.after_caption` | 8 pt | Caption above |
| `tokens.space.heading_clearance` | 0.5 pt | Used in the proof-local heading gap |
| `tokens.figure.caption_align` | `center` | Figure captions |
| Proof-local heading below | **19.93 pt** | 14.03 + 5.4 + 0.5; measured clearance 15.84 pt minimum |
| Proof-local Chapter 1 above | **22.40 pt** | 17 + 5.4; label-to-title clearance 17.76 pt |

The theme's body text is justified; the proof inherits that from `book_base`.
The current theme is used read-only; `typst/theme.typ` itself is not edited.

## Build and reproducibility

From the repository root, offline and vendored:

```sh
./tools/typst/typst compile \
  --ignore-system-fonts --ignore-embedded-fonts \
  --font-path assets/fonts \
  --package-path vendor/typst \
  --package-cache-path .cache/empty-pkg \
  --creation-timestamp 1750000000 \
  --root . \
  build/design/a1/a1-proof.typ \
  build/design/a1/a1-proof.pdf
```

The same command compiled twice produces byte-identical output:
`cmp` exit 0, both files
`675392d935a2aa8e01ab0dd34d8146087cd8756df724e210e6930fa1d754e9b9`.

Toolchain: vendored **Typst 0.15.1** (`tools/typst/typst`), locked in
`toolchain.lock.json`; fonts from `assets/fonts`; no system fonts, network,
global install or new dependency. The PDF creation timestamp is pinned to
`1750000000`.

Page renders and contact sheet:

```sh
pdftoppm -png -r 150 build/design/a1/a1-proof.pdf build/design/a1/pages/page
montage build/design/a1/pages/page-1.png build/design/a1/pages/page-2.png \
        build/design/a1/pages/page-3.png build/design/a1/pages/page-4.png \
        -tile 2x2 -geometry 620x877+24+24 -background white \
        build/design/a1/contact-sheet.png
```

## Verification

- `pdfinfo`: 4 pages, page size 595.276 × 841.89 pt (A4).
- `pdftotext`: all headings, hierarchy numbers, placeholder labels and captions
  are present as searchable text. `A1 LAYOUT PROOF` appears on every page.
- `pdffonts`: four embedded Spectral faces with Unicode maps — Regular, Italic,
  Medium, SemiBold. No system font is used.
- `a1-proof.measure.json`: text boxes come from `pdftotext -bbox-layout`; ink
  boxes come from a 150 dpi raster threshold (`L < 250`). The text box is a word
  box, not a glyph-ink measurement; the raster box is the containment check.
- `a1-proof.gaps.json`: 300 dpi raster scan of the white band under each heading.
- Contained layout: every text box starts at x ≥ 60.00 pt and ends at
  x ≤ 537.36 pt; every page's text ends at y ≤ 709.32 pt against the 781.89 pt
  bottom of the text block. Nothing is clipped.
- The 0.55 pt placeholder outline is centered on the text edge, so the full
  measure/side boxes show raster ink at x = 59.52 pt (0.48 pt of stroke outside
  the nominal 60 pt text-block edge). The 25 pt heading glyphs show optical
  overshoot to x = 59.04 pt. Both remain well inside the A4 trim and are not
  clipped; the layout boxes themselves start at 60.00 pt.

### Hashes

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `a1-proof.pdf` | 59,994 | `675392d935a2aa8e01ab0dd34d8146087cd8756df724e210e6930fa1d754e9b9` |
| `a1-proof.typ` | 9,176 | `d8762e038839777be5c553cc021fadb8466621135df11bec59386cdab555f610` |
| `contact-sheet.png` | 638,380 | `1a72f7894608209e4002a92bc8aa711a4e71e0e23248583512a756c52e297fec` |
| `a1-proof.gaps.json` | — | `c7fdb1964051945fe5fdbb463487bf3210bdf8287c704d96cc740c309548cfac` |
| `pages/page-1.png` | — | `01e3cb975a1c863f17e0d45163b0388fd7fee9be6654f6ca3b1cd18562e7d91a` |
| `pages/page-2.png` | — | `cddbe04f784d92aba44c3755ffff9835d8a1ffa372e80cccaf6172569a4dc155` |
| `pages/page-3.png` | — | `e674c15dccbde6486ca281050a1823a7a53909d3b9e8d1682133e651e0e26dd3` |
| `pages/page-4.png` | — | `f01442860170cf6b4ac2e8499760f97943aeb61c467e73c98bf9ef2dc7fa1979` |

## Per-page inspection notes

Measurements below are from `a1-proof.measure.json`; units are points.

### Page 1 — composition 1 (`figure_width`)

- `Chapter 1: Full-width prose with a centred visual`
- `1. Full-width opening` → two full-width paragraphs
- `1.1 Centred visual` → 430 × 150 pt placeholder, centered, caption
- `1.1.1 Full-width continuation` → two full-width paragraphs
- Text bbox: x 60.00–537.30, y 62.05–679.32.
- Ink bbox: x 59.04–536.64, y 63.84–677.28.
- Heading clearances: 30.24 / 15.84 / 19.68 / 18.72 pt.
- Inspected: proof label clears the Chapter 1 title by 17.76 pt; heading and
  both side margins clear; the placeholder is centered and inside the text
  block; caption sits below the box with the caption token; continuation returns
  to the full measure. No overlap or clipping. Bottom clear space ≈ 164.61 pt.

### Page 2 — composition 2 (`plate`)

- `Chapter 2: The same sequence with a full-measure visual`
- `2. Full-width opening` → two full-width paragraphs
- `2.1 Full-measure visual` → 475.28 × 180 pt placeholder, full measure, caption
- `2.1 a) Full-width continuation` → two full-width paragraphs
- Text bbox: x 60.00–537.30, y 62.05–709.32.
- Ink bbox: x 59.52–536.64, y 63.84–707.52.
- Heading clearances: 30.24 / 15.84 / 19.68 / 17.28 pt.
- Inspected: the box spans the full text measure; its 0.55 pt outline sits on the
  measure edge (0.48 pt raster bleed into the margin, no clipping). Caption is
  centered under the box; continuation is full width. No overlap. Bottom clear
  space ≈ 134.37 pt.

### Page 3 — composition 3 (full-width opening; prose left, visual right)

- `Chapter 3: Full-width opening, then prose beside a right-hand visual`
- `3. Full-width opening` → full-width opening paragraph
- `3.1 Prose in the left region beside the right-hand visual` → left prose
  column, 218.63 × 240 pt placeholder in the right column
- Text bbox: x 60.00–535.28, y 62.05–617.14.
- Ink bbox: x 59.52–535.68, y 63.84–614.88.
- Heading clearances: 24.72 / 15.84 / 16.08 pt.
- Inspected: opening paragraph is genuinely full width; the grid then uses
  240.65 pt prose / 16 pt gutter / 218.63 pt visual, summing to 475.28 pt. The
  right caption stays inside the right column. The `3.1` heading clears the grid
  by 16.08 pt. No overlap or clipping. Bottom clear space ≈ 227.01 pt.

### Page 4 — composition 4 (visual left, prose right; full-width below)

- `Chapter 4: Visual left, prose right, full-width paragraph below`
- `4. Visual and prose` → section heading
- `4.1 Prose in the right region beside the left-hand visual` → 218.63 × 230 pt
  placeholder left, prose right
- `4.2 Full-width paragraph below` → two full-width paragraphs under both columns
- Text bbox: x 60.00–537.36, y 62.05–708.74.
- Ink bbox: x 59.04–537.12, y 63.84–706.08.
- Heading clearances: 24.72 / 20.88 / 16.08 / 15.84 pt.
- Inspected: left visual and right prose share a top-aligned grid row; caption is
  under the visual; the closing heading and prose return to the full measure
  below the row. No collision between the chapter heading and the grid; no
  clipping. Bottom clear space ≈ 135.81 pt.

## Boundary record

- Not changed: `typst/theme.typ`, `typst/blocks.typ`,
  `typst/templates/book.typ`, `schemas/`, `src/`, `content/`, `tests/`,
  `packaging/` and the product's heading-numbering code.
- No global package install, no network, no new dependency, no new agent.
- `build/` is disposable/ignored output; this proof is not wired into the
  product build.
- The only status documents touched, if any, are the A1 working note and the
  design map, and only to record this proof, the confirmed hierarchy and the
  fixed blank-line rule. A1's layout questions remain open; this proof does not
  approve a design.

## What the user is judging

1. Whether each of the four composition topologies matches the reference
   description.
2. Whether the current Bookify A4 grid, measure, type size, leading and side
   fraction read correctly in each arrangement.
3. Whether the confirmed numerical hierarchy is applied correctly in the sample
   headings (`Chapter n:` → `n.` → `n.n` → `n.n a)` / `n.n.n`).
4. Whether every heading now clears its following content by at least one
   visible body blank line.
5. Which composition, if any, should become the basis for the next A1
   annotation or implementation step.
