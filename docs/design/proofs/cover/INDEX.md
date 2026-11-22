# Cover layout proofs — merged index (disposable)

**Status:** disposable review artefact. Nothing here is an approved cover, a
product template, or part of a Bookify build. This directory is shared with the
two proof agents; every file added by this merge step carries the
`cover-layout-*` prefix.

## What was done

Two existing proof PDFs were concatenated **in source order** with the installed
`pdfunite` (Poppler). No page was re-rendered, re-typeset, rotated, cropped or
otherwise edited; no design value changed.

```sh
cd /home/tris/bookify/build/design/cover
pdfunite part-a.pdf part-b.pdf cover-layout-proofs.pdf

pdftoppm -png -r 100 cover-layout-proofs.pdf cover-layout-pages/ref
pdftoppm -png -r 150 cover-layout-proofs.pdf /tmp/opencode/m150/pg   # parity check only

magick montage \
  -label 'ref 1 · part-a p1' cover-layout-pages/ref-1.png \
  -label 'ref 2 · part-a p2' cover-layout-pages/ref-2.png \
  -label 'ref 3 · part-a p3' cover-layout-pages/ref-3.png \
  -label 'ref 4 · part-a p4' cover-layout-pages/ref-4.png \
  -label 'ref 5 · part-b p1' cover-layout-pages/ref-5.png \
  -label 'ref 6 · part-b p2' cover-layout-pages/ref-6.png \
  -label 'ref 7 · part-b p3' cover-layout-pages/ref-7.png \
  -tile 4x2 -geometry 520x736+22+22 -background white \
  -pointsize 26 -fill '#4d4d4d' cover-layout-contact.png
```

## Reference map (refs 1–7)

Reference numbers are the parsed `Cover.pdf` pages the two proofs were built
from: refs 1–4 are `Cover.pdf` pages 1–4 (part A), refs 5–7 are pages 5–7
(part B). Merged PDF page *n* = ref *n*; no reordering happened.

| Ref | Merged page | Source file / page | Raster (100 dpi) | Composition (topology only) |
| --- | --- | --- | --- | --- |
| 1 | 1 | `part-a.pdf` p1 | `cover-layout-pages/ref-1.png` | Right-offset illustration panel above a lower-left title block; secondary metadata under the title; centred top and foot metadata. |
| 2 | 2 | `part-a.pdf` p2 | `cover-layout-pages/ref-2.png` | Centred illustration upper/middle, centred title and support line below it, centred foot metadata. |
| 3 | 3 | `part-a.pdf` p3 | `cover-layout-pages/ref-3.png` | Typographic only, no illustration: title at ~25 % page height with support under it, a second metadata line low on the page, centred top/foot metadata. |
| 4 | 4 | `part-a.pdf` p4 | `cover-layout-pages/ref-4.png` | Title and support near the top, then a wide near-full-measure landscape panel; centred foot metadata. |
| 5 | 5 | `part-b.pdf` p1 | `cover-layout-pages/ref-5.png` | Diagonal pale field on the lower right; upright title and support stepped right along the edge; vector burst lower-left straddling the field edge. |
| 6 | 6 | `part-b.pdf` p2 | `cover-layout-pages/ref-6.png` | Tall pale block, left/lower; strongly off-centre right column with 90° clockwise (vertical) title, meta and panel label. |
| 7 | 7 | `part-b.pdf` p3 | `cover-layout-pages/ref-7.png` | Sparse: compact upper information line, centred title with support, separate burst lower-left, quiet lower information line. |

Visible words on every page are placeholders only (`Cover`,
`Additional information`, `Illustration`, `Decorative illustration`). No title,
author, date, institution, ISBN or other factual content is invented anywhere in
the merged file.

## Current Bookify tokens used (not invented here)

Read from `typst/theme.typ` and the A4 page setup at this checkout. These are the
live house values both source proofs were built with; this merge step added no
values of its own.

| Token / value | Current value |
| --- | --- |
| Paper | A4, 595.276 × 841.890 pt (210 × 297 mm) |
| `tokens.space.page_margin` | 60 pt, all sides → 475.276 × 721.890 pt text block |
| `tokens.measure.page_height` | 297 mm (cover block height) |
| `tokens.measure.body` | 475.276 pt (full measure) |
| `tokens.type.cover_title` | 34 pt, weight 500, +18.56 pt extra leading → 41 pt pitch |
| `tokens.type.cover_subtitle` | 12.6 pt italic, `ink.grey_1`, +9.40 pt extra → 17.72 pt pitch |
| `tokens.type.cover_meta` | 8.4 pt, `ink.grey_1`, +6.46 pt extra → 12 pt pitch |
| `tokens.type.cover_index` | 8.6 pt (rule token used only; no index type is set) |
| `tokens.rule.figure_stroke` | 0.55 pt (panel outline, part A) |
| `tokens.rule.cover_index` | 0.4 pt (panel diagonals and label chip, part A) |
| `tokens.ink.text` | `#000000` |
| `tokens.ink.grey_1` | `#4d4d4d` |
| `tokens.ink.grey_3` | `#a8a8a8` |
| `tokens.ink.pale` | `#e6e6e6` |
| `tokens.space.after_block` | 5.4 pt |
| Font | Spectral Regular / Medium / Italic, vendored in `assets/fonts` |

## Deliberately not taken from the references

Neither source proof copied reference values, and the merge changed nothing, so
the merged file still carries none of them:

- **No reference measurements.** No page position, object offset, box size or
  margin from `Cover.pdf` was reused. All geometry is reflowed inside the
  current 60 pt A4 text block; the references run fields and illustrations to
  the trim, and nothing here is bled or clipped.
- **No reference type sizes or leading.** The references' display-scale cover
  type is not reproduced; every page is set at 34 / 12.6 / 8.4 pt with the
  house leading, which makes these pages read as quiet book compositions rather
  than poster-scale clones.
- **No reference fonts.** Only the three vendored Spectral subsets are embedded
  (`pdffonts`: Spectral-Regular, Spectral-Medium, Spectral-Italic, all `emb yes
  sub yes uni yes`). No system font, no reference face.
- **No reference colour or artwork.** Grayscale text plus neutral placeholder
  panels: a pale `#e6e6e6` fill with `#a8a8a8` hairlines and diagonals in part A,
  a native Typst vector burst inside a pale field in part B. No raster image
  (`pdfimages -list` is empty in both sources), no accent colour, no reference
  art.
- **No reference copy.** Placeholder strings only, as listed above.

## Verification (run against the merged file)

| Check | Command | Result |
| --- | --- | --- |
| Page count | `pdfinfo cover-layout-proofs.pdf` | **7 pages** |
| Page size | `pdfinfo -f n -l n`, n = 1…7 | all **595.276 × 841.89 pt (A4)**, rotation 0 |
| Searchable text | `pdftotext -f n -l n` | text on all 7 pages; extracted reading order per page: p1 11 words, p2 9, p3 9, p4 9, p5 10, p6 10, p7 8 |
| Page identity | `pdftotext` per page compared with `cmp` | **part-a p1–4 == merged p1–4** and **part-b p1–3 == merged p5–7**, byte-identical text |
| Raster identity | `pdftoppm -r 150` re-render, `cmp` against the earlier agent rasters | **all 7 page rasters byte-identical** to `pages/part-a-page-*.png` and `part-b-pages/page-*.png`, so the prior evidence transfers unchanged |
| Fonts | `pdffonts` | three embedded subset Unicode Spectral faces, listed twice (one set per source document); no external reference |
| Blank pages | 100 dpi raster ink census | no blank page; marked pixels per page 2311 / 2092 / 2114 / 2092 / 34065 / 28428 / 50038 at the text threshold, and 235014 / 221165 / 3745 / 305102 / 244552 / 271388 / 52272 including pale fills |
| Clipping | 100 dpi ink bounding box vs trim, tolerance 0.01 pt | all marks inside the page; **minimum trim clearance 59.60 pt** (p1 and p4, the 0.55 pt panel stroke), next 59.76 pt (p5, p6), worst-case still ≈ 59.6 pt on every side |
| Text outside margin | `pdftotext -bbox-layout` boxes vs 60…535.276 × 60…781.890 | all word boxes inside the text block on all 7 pages |
| Source untouched | `sha256sum part-a.pdf part-b.pdf` after the run | unchanged; both still match their README hashes |

Measured 100 dpi boxes per merged page (absolute A4 points, text box from
`pdftotext -bbox-layout`, ink box from the raster):

| Ref | Text box x0,y0 → x1,y1 | All-ink box x0,y0 → x1,y1 | Min trim clearance |
| --- | --- | --- | ---: |
| 1 | 60.00, 62.05 → 406.11, 779.98 | 59.76, 64.08 → 535.68, 776.16 | 59.60 pt |
| 2 | 237.67, 62.05 → 357.61, 779.98 | 131.04, 64.08 → 464.40, 776.16 | 64.08 pt |
| 3 | 237.67, 62.05 → 357.61, 779.98 | 236.88, 64.08 → 357.84, 776.16 | 64.08 pt |
| 4 | 237.67, 62.05 → 357.61, 779.98 | 59.76, 64.08 → 535.68, 776.16 | 59.60 pt |
| 5 | 158.96, 64.65 → 453.90, 773.32 | 59.76, 66.96 → 534.24, 781.20 | 59.76 pt |
| 6 | 75.57, 64.65 → 534.28, 744.43 | 59.76, 66.96 → 534.24, 760.32 | 59.76 pt |
| 7 | 186.96, 64.65 → 379.94, 773.32 | 67.68, 66.96 → 380.16, 769.68 | 66.96 pt |

Text boxes exceed 60 pt at the top by 2.05 pt (part A) / 4.65 pt (part B) only
in the *line box* sense: those boxes include the face's ascender allowance above
the 34 pt/8.4 pt glyph ink, while the raster ink starts at 64.08 pt (part A) and
66.96 pt (part B). No glyph ink crosses the 60 pt margin; the source READMEs
record the same rounding difference.

**Known limitation of `pdfunite`:** the merged document keeps every page's
content, fonts and text, but drops the per-document metadata and the PDF
structure tree (`pdfinfo` shows no Title/Author/Creator, `Tagged: no`), because
Poppler concatenates content streams without rebuilding the catalog. That is
acceptable for a disposable proof and is called out here rather than silently
implied; it is not a page-content change. Regenerate a tagged single document
from the two `.typ` sources if a tagged proof is ever needed.

## Files added by this merge step

| Path | Purpose |
| --- | --- |
| `cover-layout-proofs.pdf` | 7-page merged proof: part A pp. 1–4, then part B pp. 1–3 |
| `cover-layout-contact.png` | 4 × 2 contact sheet, refs 1–7 in source order, labels in the PNG only |
| `cover-layout-pages/ref-1.png` … `ref-7.png` | 100 dpi page rasters of the merged PDF |
| `INDEX.md` | This index and verification record |

## Hashes

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `cover-layout-proofs.pdf` | 43,822 | `5e5289c89e900342112cc2dc6820654f66e287fac93da4bf33120f745ab941ad` |
| `cover-layout-contact.png` | 229,143 | `6f80dfdb6bfc57c8fe96308c2975315ae6ac4da7b496bb0377de573227b9fd75` |
| `cover-layout-pages/ref-1.png` | 22,987 | `6308b6659d6631f5be5ba7a66d1111223bf4f21d554e5b1a75353e5810765371` |
| `cover-layout-pages/ref-2.png` | 20,634 | `54f945a144a03a4f380f62af4e21af62883fd15ff31da3412a24aca3151ea329` |
| `cover-layout-pages/ref-3.png` | 16,242 | `fa3002b9e5fc6bee90b4106ec6bdf7ebc3f90311efadcc91414dc6ced52d40d8` |
| `cover-layout-pages/ref-4.png` | 27,168 | `c52fa432ba2ff0e8593c71674c1bffe9746df3e96b8e139c9f2f7327cf5b1dab` |
| `cover-layout-pages/ref-5.png` | 27,699 | `b2d3bd9ff860e1a190324dcdf3270b92e74c567b094cf25de9813d8c4d9d329a` |
| `cover-layout-pages/ref-6.png` | 27,111 | `ee80ae7164352da663cff76879c27bdefbb4191936ad530e1913995b0a30721f` |
| `cover-layout-pages/ref-7.png` | 24,342 | `01bc37e1c52a8828cc4fb39fc8a8ca80d9196558e4a7b76e990eb307ee6d234b` |

Inputs, unchanged by this step (hashes as published in `README-a.md` /
`README-b.md` and re-checked after the merge):

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `part-a.pdf` | 24,259 | `d690dbc9a5cfcb90d18a0140b7029b31e434caded0076d8564ec938ffa73ccb3` |
| `part-b.pdf` | 23,455 | `644807862d128b2578ac4eed07b634da6117fcd2ed4cf16f3c143844feca11c3` |

`INDEX.md` is documentation and is not self-hashed.

## Boundary record

- Not touched: `docs/`, `src/`, `content/`, `typst/`, `schemas/`, `tests/`,
  `packaging/`, `assets/`, the production cover and the product tokens. The
  merge wrote only inside `build/design/cover/`.
- `part-a.pdf`, `part-b.pdf`, their `.typ` sources, `.json` measurements, 150 dpi
  page rasters and contact sheets were read only; their hashes are unchanged.
- Tools used: system `pdfunite`, `pdfinfo`, `pdftotext`, `pdftoppm`, `pdffonts`,
  `magick`/`montage`, `sha256sum`. No installs, no network, no new dependency and
  no Typst compile in this step.
- The merged PDF is an independent review artefact. It is not the product cover,
  is not referenced by any book build, and can be deleted with the rest of
  `build/`.
