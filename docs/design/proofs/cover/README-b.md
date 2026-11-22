# Part B — disposable cover layout proof

**Status:** disposable proof only. It is not a product template, not an approved
cover design, and not part of any production output. It exists to judge three
cover compositions taken from parsed `Cover.pdf` pages 5–7.

- **Reference input:** `/tmp/opencode/cover-ref/ref-5.png`, `ref-6.png`, `ref-7.png`
  (parsed pages 5–7 of the user's `Cover.pdf`).
- **Layout only:** the proof recreates composition, grouping and reading order.
  It does **not** copy reference measurements, reference type sizes or reference
  fonts. All visual values come from the live Bookify theme.
- **Product files:** no production file was modified by this proof. Nothing under
  `src/`, `typst/`, `content/`, `docs/` or `dist/` was edited. The working tree
  already had unrelated uncommitted changes before this proof; they are outside
  `build/design/cover/` and are not part of this artifact.
- **Network/model:** none. Typst 0.15.1 and the vendored Spectral faces are used
  offline inside `bwrap --unshare-net`.

## Files

| Path | Purpose |
| --- | --- |
| `part-b.pdf` | Three A4 pages, one composition per reference page, searchable text |
| `part-b-pages/page-1.png` … `page-3.png` | 150 dpi page renders |
| `part-b-contact.png` | 3-up contact sheet; its labels exist only in this PNG |
| `part-b.json` | Tokens, nominal/measured boxes, clearances, checks, hashes |
| `part-b.typ` | Disposable Typst source |
| `part-b-measure.py` | Renders 300 dpi, reads PDF text boxes, writes `part-b.json` |
| `README-b.md` | This note |

## Commands (offline)

```bash
cd /home/tris/bookify
bwrap --unshare-net --bind / / --chdir /home/tris/bookify -- \
  ./tools/typst/typst compile \
  --ignore-system-fonts --ignore-embedded-fonts \
  --font-path assets/fonts --package-path vendor/typst \
  --package-cache-path .cache/empty-pkg \
  --creation-timestamp 1750000000 --root . \
  build/design/cover/part-b.typ build/design/cover/part-b.pdf

pdftoppm -png -r 150 build/design/cover/part-b.pdf build/design/cover/part-b-pages/page
magick montage -label 'reference 5 · page 1' build/design/cover/part-b-pages/page-1.png \
  -label 'reference 6 · page 2' build/design/cover/part-b-pages/page-2.png \
  -label 'reference 7 · page 3' build/design/cover/part-b-pages/page-3.png \
  -tile 3x1 -geometry +24+24 -background white \
  -pointsize 30 -fill '#4d4d4d' build/design/cover/part-b-contact.png
python3 build/design/cover/part-b-measure.py
```

## Geometry and tokens

| Item | Value |
| --- | --- |
| Page | A4, 595.2756 × 841.8898 pt (210 × 297 mm) |
| Margin | 60 pt all sides (`space.page_margin`) |
| Content box | 60, 60 → 535.2756, 781.8898 pt |
| Content size | 475.2756 × 721.8898 pt |
| Title | `type.cover_title` 34 pt, weight 500, leading extra 18.56 → 41 pt pitch |
| Support | `type.cover_subtitle` 12.6 pt, italic, `ink.grey_1`; leading extra 9.40 → 17.72 pt pitch |
| Meta | `type.cover_meta` 8.4 pt, `ink.grey_1`; 6.46 extra → 12 pt pitch |
| Ink | `ink.text` `#000000`; `ink.grey_1` `#4d4d4d`; `ink.pale` `#e6e6e6` |
| Rules | none; the reference compositions need no rule ornament |
| Font | Spectral Regular / Medium / Italic only, vendored in `assets/fonts` |
| Illustration | native Typst polygon burst, `ink.text`; label `ink.pale`; no raster |

All coordinates below are **absolute A4 points from the top-left trim**. The
content box is the only drawing region; the illustration and fields are held
inside it by construction, not by a page-edge accident.

## Composition choices

### Page 1 — reference 5

Asymmetric diagonal field with a pale lower-right plane whose edge runs from the
content-left at y = 600 pt to content-right at y = 440 pt. The upright title and
support step right with that edge (`205 pt` then `245 pt`), so the diagonal is a
**layout relation**, not a copied rotation. The vector burst anchors the opposite
lower-left region and straddles the field edge.

The reference rotates its title along the edge. This proof keeps it upright on
purpose: the brief permits the diagonal only as a layout relation, and upright
type keeps the PDF text extractable as whole words. The title's ink is clear of
the field; only the last word of the support crosses onto pale, where black
remains legible.

### Page 2 — reference 6

Large pale illustration block on the left/lower area (235 × 590 pt) and a
strongly off-centre right vertical title/meta pair. The 90° clockwise rotation is
kept because the 34 pt title is still clearly readable top-to-bottom and extracts
as `Cover`. The meta column sits 11.79 pt left of the title ink. The decorative
label inside the block is also vertical, top-to-bottom. This is the asymmetry of
the reference, not a horizontal substitute.

### Page 3 — reference 7

Sparse, intentional composition: one compact upper information line, a central
title with its support, a separate illustration lower-left, and a quiet lower
information line. No rotation. The white space is the composition.

## Measured boxes

Values are `[x0, y0, x1, y1]` in absolute A4 points. `part-b.json` carries the
same boxes plus nominal source boxes and text-line bboxes.

| Page | Element | Measured box |
| --- | --- | --- |
| 1 | Title `Cover` | 265.00, 441.43 → 354.56, 493.18 |
| 1 | Support | 305.00, 484.97 → 424.94, 504.15 |
| 1 | Pale field | 60.04, 440.28 → 534.28, 780.84 |
| 1 | Illustration | 65.52, 510.96 → 294.48, 729.12 |
| 1 | `Illustration` label | 158.96, 611.65 → 201.04, 624.43 |
| 1 | `Decorative illustration` | 370.00, 701.65 → 453.90, 714.43 |
| 1 | Top / bottom info | 254.48, 64.65 → 340.79, 77.43 / 254.48, 760.54 → 340.79, 773.32 |
| 2 | Pale block | 60.04, 169.80 → 295.00, 759.96 |
| 2 | Title `Cover` (rotated) | 476.82, 215.00 → 528.57, 304.56 |
| 2 | Meta (rotated) | 445.85, 215.00 → 465.03, 334.94 |
| 2 | Illustration | 81.60, 428.16 → 274.56, 621.84 |
| 2 | `Illustration` label | 156.96, 516.65 → 199.04, 529.43 |
| 2 | `Decorative illustration` (rotated) | 75.57, 650.00 → 88.35, 733.90 |
| 2 | Top / bottom info | 254.48, 64.65 → 340.79, 77.43 / 447.97, 731.65 → 534.28, 744.43 |
| 3 | Title `Cover` | 250.00, 196.43 → 339.56, 248.18 |
| 3 | Support | 260.00, 244.97 → 379.94, 264.15 |
| 3 | Illustration | 68.64, 425.52 → 347.28, 704.64 |
| 3 | `Illustration` label | 186.96, 556.65 → 229.04, 569.43 |
| 3 | Top / bottom info | 254.48, 64.65 → 340.79, 77.43 / 254.48, 760.54 → 340.79, 773.32 |

Ink clearances read from the 300 dpi raster, not from source spacing:

| Page | Clearance | Value |
| --- | --- | ---: |
| 1 | Title ink → support ink | 11.04 pt |
| 2 | Meta ink → rotated title ink (horizontal) | 11.79 pt |
| 3 | Title ink → support ink | 16.08 pt |

Field/illustration measured-vs-nominal deltas are at or below 0.8 pt, i.e. one
300 dpi pixel; the page-1 field right and bottom edges stop 1 pt inside the content box
so antialias cannot enter the 60 pt margin.

## Verification

- **Pages:** 3; one A4 page per reference composition.
- **Margins:** all page ink, all pale field ink, and all text are inside the
  60 pt margin; nothing is outside the A4 trim.
- **Text:** selectable and searchable, and extracted in reading order per page.
  Counts: `Cover` × 3, `Additional information` × 9, `Illustration` × 3,
  `Decorative illustration` × 2.
- **Placeholders:** no other visible words. No invented title, edition, year,
  institution, city or ISBN.
- **Fonts:** three Spectral subsets, all embedded (`Spectral-Regular`,
  `Spectral-Medium`, `Spectral-Italic`); no reference font, no system font.
- **Images:** `pdfimages -list` is empty; the illustration is native vector.
- **Offline:** compiled under `bwrap --unshare-net` with vendored Typst and fonts.

## Deliberate differences from the references

- Type is house-scale (34 / 12.6 / 8.4 pt), not the references' oversized cover
  type. The references' exact measurements and fonts were not reused.
- All geometry stays inside the 60 pt safe margin; the references run fields and
  illustrations off the trim. Nothing here is clipped.
- The illustration is a neutral radial burst placeholder. It is not the
  reference art and carries no data.
- Page 1 uses upright title/support stepped along the diagonal edge (the brief
  allows the diagonal as a layout relation). Page 2 keeps the reference's
  readable vertical arrangement. Page 3 stays upright and sparse.
- The JSON `text_lines` field groups words by PDF baseline, so rotated page-2
  phrases appear as fragments there. `searchable_text` is the authoritative
  reading-order extraction and is clean for all three pages.

## Hashes

| Artifact | SHA-256 |
| --- | --- |
| `part-b.pdf` | `644807862d128b2578ac4eed07b634da6117fcd2ed4cf16f3c143844feca11c3` |
| `part-b.typ` | `c666e9b9b5cf06c3fcf2f53b81135b4ec4caa16cc1b1ddc492c95157cdd4ff6f` |
| `part-b-measure.py` | `4f694c98ddacff708932f56615af741a2748315c16c4579770d6624e65239686` |
| `part-b-contact.png` | `65eb35c4553f0f39e1bb00aa456d9e599ce0b714548b5a0fb53ccc433cd04e2b` |
| `page-1.png` | `2392cab01353250b94fd7b9706d92b2942dd02a286b977f788987b4057ab6b26` |
| `page-2.png` | `68ec0764b0e99aedb647da32c400f69fb2ed4d28b996588a0aee28904de1ebbf` |
| `page-3.png` | `03b73cc279c358667e63f785e58142ce128efb030fdd98eff74f617387e15462` |

The `measure_sha256` embedded in `part-b.json` changes whenever `part-b-measure.py`
changes, so the JSON is a self-describing snapshot rather than a fixed binary
manifest.
