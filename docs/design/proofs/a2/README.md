# A2 disposable layout proof

**Status:** disposable proof only. Not a product template, not an approved design,
and not part of any production output. It exists to judge an A2 two-column
composition and the user-supplied numbering / heading-clearance rules.

- Reference input: parsed pages **A2 5–6** — two flowing text columns, an optional
  figure embedded inside the right column, continuation on the next page.
- Product files: unchanged. Only `build/design/a2/`, `docs/design-map.md`, and
  `docs/design/textbook-layout.md` were edited for this proof.
- Network/model: none. Typst and all fonts are vendored and used offline.

## What the proof contains

Two A4 pages, no forced blank page:

1. **Page 1** opens with the A2 annotation, a numbered chapter title, and a
   standfirst across the full measure, then two flowing columns. The left column
   carries the numbered section/subsection hierarchy; the right column carries the
   terminal branches, the neutral vector figure, and text before and after it.
2. **Page 2** continues the same column flow from the bottom of page 1, carries the
   continued numbered branches, and ends naturally at the bottom of the second
   page.

No table block appears in the proof. Sample prose is public-safe Lorem text only;
the figure is a native vector placeholder and carries no data.

## Fixed structural rules applied

### 1. Always a numerical hierarchy

The visible path is complete and does not skip a level:

```
Chapter 2: Two-Column Flow
  2. Example 1                 (level-2 heading)
    2.1 Example 2              (level-3 heading)
      2.1 a)                   (terminal branch, run-in)
      2.1 b)                   (terminal branch, run-in)
      2.1 c)                   (terminal branch, run-in)
      2.1.1 Continuing Branch  (level-3 heading; branch continues)
        2.1.1.1 Deeper Branch  (level-3 heading; branch continues)
```

The chapter title includes its number. The first body heading is `2. Example 1`;
the next is `2.1 Example 2`; terminal branches are `2.1 a)`–`2.1 c)`; the continued
branch is `2.1.1`, then `2.1.1.1`. No number is omitted.

Terminal branches are run-in labels at body size with the existing bold face, not
new block styles. `2.1.1.1` is a block heading using the existing h3 role because
the live theme defines h1–h3 only; no h4 size or weight was invented. The number
path, not a new style, carries the extra depth.

### 2. A visible blank line after every heading

The fixed user rule is applied to the chapter heading and every numbered body
heading. One blank body line is reserved as white space between the heading's
descender ink and the following content's ascender ink:

```
blank line       = 0.660 × 10.1 pt + 8.63 pt = 15.30 pt
heading-blank(s) = 0.240 × s + 0.090 × 10.6 pt + 15.30 pt + 0.5 pt
```

The `+0.5 pt` is the existing `tokens.space.heading_clearance`, so rounding cannot
fall below one line. It is a local proof helper; the product theme is untouched.

Measured from the 300 dpi render (ink-row scan, not source values):

| Heading | Measured white gap |
| --- | ---: |
| `Chapter 2: Two-Column Flow` | 16.08 pt |
| `2. Example 1` | 16.08 pt |
| `2.1 Example 2` | 15.60 pt |
| `2.1.1 Continuing Branch` | 15.60 pt |
| `2.1.1.1 Deeper Branch` | 15.84 pt |

**Minimum measured gap: 15.60 pt** (≥ one 15.30 pt body line). The same
`heading-blank` helper is used for every heading in either column, so clearance is
column-independent. In this composition the body headings currently fall in the
left column; the chapter heading and its standfirst span the full measure.

## Exact Bookify baseline values used

Imported from `typst/theme.typ`; no values were copied from the reference pages.

| Token | Value |
| --- | --- |
| Page | A4, 595.2756 × 841.8898 pt |
| Margin | 60 pt all sides |
| Text measure | 475.28 pt (595.276 − 120) |
| Body | 10.1 pt, leading extra 8.63 pt, total pitch 15.30 pt |
| Lead / standfirst | 10.6 pt, leading extra 9.40 pt, total 16.40 pt, grey `#4d4d4d` |
| H1 | 25 pt, weight 500, leading extra 13.5 pt, total 30.00 pt |
| H2 | 12.6 pt, weight 600, leading extra 8.18 pt, total 16.50 pt |
| H3 | 10.3 pt, weight 600, leading extra 7.20 pt, total 14.00 pt |
| Caption | 8.2 pt, leading extra 5.79 pt, total 11.20 pt, italic, grey `#4d4d4d` |
| Small | 8.4 pt, leading extra 6.46 pt, total 12.00 pt |
| Paragraph block below | 14.03 pt (`8.63 + 5.4`); measured baseline delta 20.70 pt |
| Heading above H1/H2/H3 | 17 / 32 / 25 pt |
| Heading below (theme) | 7.454 / 4.5 / 4.5 pt, overridden locally by the blank-line helper |
| Figure stroke | 0.55 pt |
| Ink | text `#000000`; grey_1 `#4d4d4d`; grey_2 `#7a7a7a`; grey_3 `#a8a8a8`; pale `#e6e6e6` |
| Fonts | Spectral Regular / Medium / SemiBold / Bold / Italic; Noto Serif CJK JP available; no new font |

Two equal columns use `tokens.space.side_gutter` as the gutter:

```
column width = (475.28 − 16) / 2 = 229.638 pt
column 1 x   = 60.000 .. 289.638 pt
column 2 x   = 305.638 .. 535.276 pt
gutter       = 289.638 .. 305.638 pt (16 pt)
```

## Measured page geometry (300 dpi / PDF text bbox)

Nominal column boxes are above. Text bboxes below are actual rendered extents from
`pdftotext -bbox-layout`; they include Typst's 2.08 pt hanging punctuation at the
right edge of each column.

| Measurement | Page 1 | Page 2 |
| --- | --- | --- |
| Title block bbox | 60.00, 56.65 → 428.86, 122.10 | — |
| Column 1 text bbox | 60.00, 124.16 → 291.72, 777.70 | 60.00, 55.97 → 291.72, 757.73 |
| Column 2 text bbox | 305.64, 125.16 → 537.36, 765.61 | 305.64, 55.97 → 537.36, 772.27 |
| Words in columns | 489 | 596 |
| Figure unit bbox | 305.52, 486.96 → 535.20, 665.76 | — |
| Figure label + caption bbox | 339.79, 484.03 → 493.92, 667.59 | — |
| Figure text clearance | 6.08 pt above, 6.17 pt below | — |
| Folio bbox | 295.11, 795.86 → 300.16, 811.23 | same |
| Full-page ink bbox | 59.76, 59.76 → 536.88, 806.40 | 60.00, 58.80 → 536.88, 806.40 |

Checks:

- No word crosses the 16 pt gutter (`words_crossing_gutter` is empty on both pages).
- Hanging punctuation reaches 291.72 pt / 537.36 pt, i.e. 2.08 pt into the gutter;
  it remains 13.92 pt clear of the opposite column and 57.9 pt inside the trim.
- Body text stays inside the 60 pt text block vertically; the lowest body ink is
  777.70 pt on page 1 and 772.27 pt on page 2 (text block bottom 781.89 pt).
- Figure and text are disjoint: text above ends above 486.96 pt; text below starts
  below 667.59 pt.
- No raster image is present (`pdfimages -list` is empty); the chart is native
  vector drawing. All fonts are embedded and subset.
- Extracted text is searchable; `pdftotext -layout` contains all headings, terminal
  labels, caption, and body prose (1,107 words).

## Visual observations

- Page 1 reads as a single A2 opening: annotation, chapter title, one-line
  standfirst, then two columns. The h2 `2. Example 1` and h3 `2.1 Example 2` are
  visibly separated from following prose by one blank body line.
- The right column is a true column: `2.1 a)`–`2.1 c)` flow at the top, the figure
  sits mid-column, and five lines of prose follow it before the page break. The
  figure does not split and does not become a full-width plate.
- Page 2 continues the same flow rather than restarting a section. `2.1.1` and
  `2.1.1.1` each stand clear of their following paragraph. The last line lands at
  772.27 pt, so the page ends naturally without a forced blank page.
- The blank-line rule makes the hierarchy legible without changing type sizes:
  headings remain black; the standfirst stays grey; the figure remains neutral
  grey. There is no added colour or ornament.
- At 110 dpi the page looks balanced; at 300 dpi no collisions, clipping, or
  overlapping glyphs were found. The only tight gap is the deliberately compact
  figure caption zone, which is not a heading.

## Reproduction

```sh
cd /home/tris/bookify

# Build (offline, pinned Typst + vendored fonts, fixed timestamp)
SOURCE_DATE_EPOCH=0 tools/typst/typst compile \
  --root . --ignore-system-fonts --font-path assets/fonts \
  --creation-timestamp 0 \
  build/design/a2/proof.typ build/design/a2/proof.pdf

# Render and extract evidence
pdftoppm -r 300 -png build/design/a2/proof.pdf build/design/a2/pages/page
pdftotext -bbox-layout build/design/a2/proof.pdf build/design/a2/proof.bbox.html
pdftotext -layout build/design/a2/proof.pdf build/design/a2/proof.txt
python3 build/design/a2/measure.py > build/design/a2/measure.json

# Contact sheet
montage build/design/a2/pages/page-1.png build/design/a2/pages/page-2.png \
  -tile 2x1 -geometry 700x+24+24 -background '#e6e6e6' -border 0 \
  build/design/a2/contact.png
```

Typst: 0.15.1 (`tools/typst/typst`, sha256
`29273eaa04f6d00edd0c2bec578f565fc9c65be856bfbffc894567c68ed0b237` per
`toolchain.lock.json`).

## Hashes (SHA-256)

```
1de2a7599155324bebcfce9a2c5af22eb86adb8833916a236d8f328e76fc3602  proof.typ
4f64d9c249739473055bbb5007c60661d7ed49346d9ada51da52e26c6e1d7a3a  proof.pdf
1e9e9b7a1037ea8a2bb630aec93b4cff4e8d7a62c40b9bd685c109067e6979f6  measure.py
997b6f3c5f9f15dddb65fc616416d69d2ff41daec0ec19d264935a0d9c8db679  measure.json
5d0f6c74b9916796d7439c37cf17e1207d48c08e81e66ccbe51177875b83915e  proof.bbox.html
4d83a0f2328ceac152170cfab0b06383e8e4548a2c60c30cb127600e3cf85d17  proof.txt
e7827df33e5b3de9069dc71161d419fa2ffc18b2fef450d79172ee5b91b9b3b3  pages/page-1.png
6085ea2da80c368fb175749d13885b910291947902ae1f249825eae3b85ac715  pages/page-2.png
d9e50cbcb7295f2bd9d799adcb57cdacfa858cc74cddc472b54cfd1c71162937  contact.png
```

The PDF hash was verified stable across two consecutive builds with the command
above. The proof PDF is 2 pages; page size 595.276 × 841.89 pt.

## Files

| Path | Role |
| --- | --- |
| `proof.typ` | Disposable source; imports the live theme and block presets |
| `proof.pdf` | Two-page A4 proof |
| `pages/page-1.png`, `pages/page-2.png` | 300 dpi page renders |
| `contact.png` | Two-page contact sheet |
| `proof.bbox.html` | Text bboxes from `pdftotext -bbox-layout` |
| `proof.txt` | Searchable extracted text |
| `measure.py` | Disposable measurement helper (text bbox, ink rows, heading gaps) |
| `measure.json` | Recorded measurements used above |

## Limitations

- This is a composition proof, not an approval of column count. Q2 in
  `docs/design/textbook-layout.md` remains open, and no product template or theme
  token changed.
- The live theme defines only h1–h3 block roles. `2.1.1.1` therefore uses the h3
  role rather than a new h4 style; terminal branches use a body bold run-in. If
  distinct h4 typography is wanted, that is a separate design decision.
- No heading currently sits in the right column; the same `heading-blank` helper is
  used for all headings, so any future right-column heading receives the measured
  15.60 pt minimum clearance.
