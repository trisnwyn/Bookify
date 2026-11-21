# WeasyPrint — reverse-engineering report

Read-only study of <https://github.com/Kozea/WeasyPrint> for possible reuse in Bookify.
Nothing in Bookify was modified to produce this report, and no WeasyPrint code was
added to the repository.

| Field | Value |
| --- | --- |
| Repository | `Kozea/WeasyPrint` |
| Commit studied | `0dffae41ffd1ceb78f4c45f5894ceece0b1dcb9d` (2026-11-19) |
| Version | 70.0 (released 2026-09-08) |
| Licence | BSD-3-Clause, © 2011-2021 Simon Sapin and contributors |
| Language | Python ≥ 3.11 |
| Size | 33,360 lines of library code across 69 modules; 47,037 lines of tests |
| Test surface | 1,527 test functions in 69 files (17 layout, 24 draw modules) |
| Native dependencies | Pango, HarfBuzz, fontconfig (through cffi bindings in `text/ffi.py`) |

---

## 1. What it is, precisely

WeasyPrint is an **HTML + CSS → PDF** converter whose distinguishing feature is that it
implements the CSS *paged media* model rather than the screen model. One call renders a
whole document to a list of fixed-size pages:

```python
from weasyprint import HTML
HTML(string='<h1>Title</h1>').write_pdf('out.pdf')
```

There is no JavaScript, no browser engine, no network service, and no layout editor. It
parses HTML with `tinyhtml5`, cascades CSS with `tinycss2` + `cssselect2`, builds a CSS
**box tree**, paginates it, paints it, and serialises the result with `pydyf`. It is,
in effect, a small deterministic rendering engine with a print-shaped output.

The public API is deliberately narrow (`docs/api_reference.rst`): `HTML`, `CSS`,
`Attachment`, `Document`, `DocumentMetadata`, `Page`, `URLFetcher`,
`FontConfiguration`, `CounterStyle`. Everything else is documented as "use at your own
risk". The project also states plainly that *each release changes rendering*, not just
the API — version bumps are browser-like, not semver (issue #900, cited in the docs).
That is the single most important fact for anyone planning to depend on it: **output is
not stable across versions**, by design and by declaration.

What it is *not*:

- not a book design tool — it has no manuscript model, no content schema, no figure
  engine, no rights tracking, no verification gate;
- not a PDF post-processor — it can only write PDFs it has laid out itself;
- not a font-shaping toolkit you can borrow piecemeal — shaping happens inside Pango
  through cffi and is not separable from the layout engine;
- not dependency-light — it needs a working Pango/HarfBuzz/fontconfig stack at runtime.

---

## 2. Architecture, traced from the entry point

The pipeline is five stages, each in its own package. This is the real call graph, read
from `weasyprint/document.py` and `weasyprint/pdf/__init__.py`.

```
HTML.render()                                  __init__.py:196
 └ Document._render()                          document.py:181
    1. _build_layout_context()
       ├ tinyhtml5 parse            → etree          html.py
       ├ CSS collection + preprocess → stylesheets   css/__init__.py
       └ get_all_computed_styles()  → cascade        css/__init__.py
    2. build_formatting_structure()                formatting_structure/build.py
       anonymous boxes, tables, lists, counters, footnotes, string-set
    3. layout_document()                          layout/__init__.py:51
       make_pages() → block/inline/page/table/flex/grid/column/float/absolute
       repagination loop, max_loops=8
       post-pass: string-set, bookmark labels, margin boxes
    4. Document([Page(page_box), …])              document.py:210
    5. write_pdf() → generate_pdf()               pdf/__init__.py:120
       resources → page streams + draw_page() → links/annotations/forms
       → outlines → info dict → embedded fonts → tags → output intents
       → variant function (pdfa / pdfua / pdfx) → pydyf.PDF.write()
```

### Stage 1 — CSS cascade (`css/`, 8,540 lines)

A hand-written CSS 2.1 + selected CSS 3/4 implementation: property definitions and
defaults in `properties.py` (414 lines of tables), validation for roughly 220 properties in
`validation/properties.py` (2,165) and shorthands in `validation/expanders.py` (1,140),
computed-value resolution in `computed_values.py`, `@page` selectors and media queries in
`media_queries.py`, and a full CSS Counter Styles Level 3 implementation in
`counters.py`.

### Stage 2 — formatting structure (`formatting_structure/`, 2,434 lines)

`build.py` (1,333) turns the styled element tree into a **box tree** of 31 box classes
(`boxes.py`, 970): block, inline, line, table wrappers, flex, grid, absolute, float,
replaced, footnote area, margin boxes. It also mines the document for things pagination
will need later — footnote calls, `string-set` values, bookmark labels, counters, and
`target-counter()` dependencies — into a `TargetCollector` (`css/targets.py`).

### Stage 3 — pagination (`layout/`, 10,034 lines)

The heart of the project, and the part that makes it interesting for a book pipeline.
`layout/__init__.py::layout_document()` runs **repagination passes**, up to eight:

```python
for loop in range(max_loops):          # max_loops = 8
    pages = list(make_pages(...))
    reloop = any(
        page_data.content_changed or
        (page_data.pages_wanted and initial_total_pages != actual_total_pages)
        for page_data in context.page_maker)
    if not reloop:
        break
```

Each pass re-runs the box layout; a pass is repeated only while something that depends on
page geometry actually changed — page counters used in headers, footnotes that push
content, `target-counter()` values inside a table of contents. After convergence, a final
pass resolves `string-set` values and bookmark labels, then lays out the page margin
boxes. This is a **convergence loop, not a fixed-iteration loop** — a distinction the
proposal's W5 takes directly into Bookify's illustration placement.

Around that loop sit the individual layout modules: `block.py` (1,130), `inline.py`
(1,246 — line breaking, justification, hyphenation, floats integration), `page.py` (994 —
margin boxes, page selection, blank pages), `table.py` (1,109), `flex.py` (965), `grid.py`
(1,490), `column.py` (407), `absolute.py`, `float.py`, `leader.py` (TOC dot leaders),
`preferred.py` (min/max content widths).

### Stage 4 — painting (`draw/`, 1,752 lines)

`draw_page()` walks the laid-out page and emits PDF operators into a `pydyf.Stream`:
borders (781 lines of corner and radius geometry), backgrounds and gradients, text runs
with per-glyph positions, and replaced content. Colours go through ICC-aware handling
(`draw/color.py`).

### Stage 5 — PDF assembly (`pdf/`, 2,591 lines)

`generate_pdf()` is an ordered serialiser, and the order is what makes conformance
possible:

| Step | Module | What it emits |
| --- | --- | --- |
| Fonts | `pdf/fonts.py` (677) | HarfBuzz subsetting, CID fonts, ToUnicode CMaps, variation instancing |
| Links & anchors | `pdf/anchors.py` (469) | link annotations, form fields, named destinations |
| Outlines | `pdf/anchors.py::add_outlines` | nested `/Outlines` tree from bookmark levels |
| Info dict | `pdf/__init__.py:250` | `/Title`, `/Author`, `/Subject`, `/Keywords`, `/Creator`, dates |
| Tags | `pdf/tags.py` (367) | `/StructTreeRoot`, `/StructElem`, MCID→element `/ParentTree` |
| Output intent | `pdf/__init__.py:334` | ICC profile, `/GTS_PDFA1` |
| Variants | `pdf/pdfa.py`, `pdf/pdfua.py`, `pdf/pdfx.py` | XMP packet, conformance ids, removals |

The variant layer is a clean little state machine. `pdfa.py` maps 11 standards to
`(function, defaults)`, deletes what each level forbids (attachments for A-1, non-PDF
attachments for A-2, `/Info` for A-4), forces `/Annot` flags, and writes the XMP
descriptor. `pdfua.py` is 17 lines because everything it needs — tagging — already
happened upstream. `pdf/metadata.py::DocumentMetadata` is the field mapping: HTML
`<title>` → `/Title` + `dc:title`, `<meta name=author>` → `/Author` + `dc:creator`,
`<html lang>` → `dc:language`, `dcterms.created` → `/CreationDate` + `xmp:CreateDate`.

---

## 3. Paged-media feature inventory

These are the features that make WeasyPrint relevant to a book publisher, taken from
`docs/api_reference.rst` and confirmed in the source.

| Feature | Where | Book relevance |
| --- | --- | --- |
| `@page` margin boxes (16 slots) | `layout/page.py` | running heads, folios, folio bands |
| `string-set` / `content()` | `layout/__init__.py` post-pass | running chapter titles |
| Running *elements* (CSS GCPM) | `layout/page.py` | placed page furniture, not just strings |
| Named pages (`page: name`) | `layout/page.py` | chapter opener vs body vs plate pages |
| `:left` / `:right` / `:first` / `:blank` | `layout/page.py` | recto/verso distinction |
| `break-before: recto\|verso\|left\|right` + auto blank page | `layout/block.py:1130`, `layout/page.py:743` | print-ready chapter starts |
| Footnotes (`float: footnote`) | `layout/__init__.py`, `formatting_structure/` | scholarly apparatus |
| `target-counter()` / `target-text()` | `css/targets.py`, repagination loop | TOC page numbers, "see §2.1 on p. 14" |
| `leader()` | `layout/leader.py` | dotted TOC leaders |
| Bookmarks (`bookmark-level/-label/-state`) | `anchors.py:133`, `pdf/anchors.py:59` | PDF outline, nested with level skipping |
| Multi-column | `layout/column.py` | body columns |
| Hyphenation (Pyphen) with `hyphenate-limit-chars (5,2,2)`, `hyphenate-limit-zone`, `hyphenate-character` | `text/line_break.py`, `css/properties.py:166` | justified prose quality |
| Language-aware line breaking | `text/line_break.py:607` (Pango log attrs) | per-script break rules |
| PDF/A-1b/1a/2b/2u/2a/3b/3u/3a/4/4f/4e + PDF/UA-1/2 | `pdf/pdfa.py`, `pdf/pdfua.py` | archival and accessibility output |
| Tagged PDF | `pdf/tags.py` | screen-reader structure |
| Custom `URLFetcher` | `urls.py:236` | resource allow-listing, offline enforcement |
| ICC colour profiles, output intent | `pdf/__init__.py:148` | print colour |

---

## 4. Quality signals

**Testing is the strongest part of the project.** 47k lines of tests for 33k lines of
code, and the interesting ones are not unit tests:

- `tests/draw/` renders HTML to a page image and compares it to a declared **ASCII pixel
  map** (`tests/draw/__init__.py`, `PIXELS_BY_CHAR` / `parse_pixels` / `assert_pixels`).
  Each draw test states expected geometry as text that reads like a picture, so a
  regression diff is legible in review. A companion `assert_same_renderings(tolerance=)`
  checks two documents render identically.
- `tests/layout/` asserts box trees directly (`serialize` / `assert_tree` in
  `testing_utils.py`), so pagination bugs are diagnosed structurally rather than visually.
- `FakeHTML` + `capture_logs` + `assert_no_logs` fail a test on any unexpected warning.

**Engineering discipline:** one module per concern, nearly all modules under ~1,000 lines (the generated
property and expander tables are the exceptions), no god object,
`ruff` configured strictly (`T20` bans `print`), commented references to the CSS spec
section beside the code that implements it.

**Known weaknesses:** CSS coverage is a subset and documented as such; flex/grid are
partial; `column-fill` balancing and `column-span` are limited; the project explicitly
refuses backward compatibility on rendering (docs cite issue #900); and 70.0 was a
security release (CVE-2026-55073, EPS rendering and URL-fetcher handling). Anything
embedding untrusted HTML has to track releases.

---

## 5. Dependency and licence chain

| Package | Licence | Note |
| --- | --- | --- |
| WeasyPrint 70.0 | BSD-3-Clause | MIT-compatible for reuse with notice retention |
| pydyf ≥ 0.13 | BSD-3-Clause | PDF object serialiser; small, readable, reusable |
| tinyhtml5, tinycss2, cssselect2 | MIT / BSD-3-Clause | parsers |
| fonttools ≥ 4.59 | MIT | subsetting, variation instancing |
| Pillow ≥ 12.1 | MIT-CMU | raster decode |
| cffi | MIT | Pango/HarfBuzz binding |
| **Pyphen ≥ 0.9** | **GPL-2.0+ / LGPL-2.1+ / MPL-1.1 (tri-licence)** | hyphenation dictionaries |

The Pyphen row is the one that matters for Bookify. WeasyPrint itself is BSD-3 and safe
to copy from with attribution. Pyphen is *not*: any code lifted from it must be taken
under MPL-1.1 (file-level copyleft, modified files published), because the GPL/LGPL
options would infect an MIT project. WeasyPrint only calls Pyphen's public API, so a
dependency on WeasyPrint does not put Bookify's own code under MPL — but copying the
hyphenation engine itself would.

---

## 6. Empirical probes against the Bookify tree

Run on this machine against the pinned toolchain, not inferred from documentation.

### 6.1 Bookify's PDFs carry no document metadata

`pdfinfo -meta dist/specimen.pdf` and `pdfinfo dist/specimen.pdf`:

- the XMP packet contains only `xmp:CreatorTool`, `dc:language`, `xmp:CreateDate`,
  `xmp:ModifyDate`, `xmpTPg:NPages`, `dc:format`, `xmpMM:InstanceID`;
- there is **no `dc:title`, no `dc:creator`, no `dc:description`**, and the PDF Info
  dictionary has no `/Title`, `/Author`, `/Subject` or `/Keywords`.

Cause: `typst/templates/book.typ` and `typst/theme.typ` never call `set document(...)`,
so Typst has nothing to write. The manuscript's `metadata.title`, `metadata.author` and
`metadata.languages` reach the cover and the build report, but not the file. Every one of
the 15 PDFs in `dist/` has the same shape.

Consequence: a reader's library, a PDF/A validator, a DOI deposit or a catalogue record
sees an untitled, unattributed file, and `bookify verify` passes it, because no check
reads PDF metadata.

*(Fixed on 2026-11-21 by W1 and W2 of the proposal: the template now sets the document
title and author, and `docmeta` fails a file whose identity does not match its
manuscript. The finding is kept as the evidence the change rests on.)*

### 6.2 The pinned Typst already supports PDF/A and PDF/UA

`tools/typst/typst compile --help` (Typst 0.15.1) lists `--pdf-standard` with `a-1b`,
`a-1a`, `a-2b`, `a-2u`, `a-2a`, `a-3b`, `a-3u`, `a-3a`, `a-4`, `a-4f`, `a-4e`, `ua-1`,
plus `--no-pdf-tags` (tagging is on by default).

A four-line probe compiled with `--pdf-standard a-2b,ua-1` produced a 1.7 PDF with
`/StructTreeRoot`, `/MarkInfo`, `/Lang`, `/Outlines`, `/Metadata`, an `OutputIntent`
containing `GTS_PDFA1`, and XMP carrying `pdfaid:part 2`, `pdfaid:conformance B`,
`pdfuaid:part 1`. So archival conformance is **one flag away** for Bookify; the missing
piece is not the capability, it is the decision and the check.

### 6.3 Verification can read that metadata with no new dependency

`pdfinfo -meta` (already pinned, Poppler 26.01) prints the full XMP packet, and
`pdfinfo` already reports `Tagged`, `Metadata Stream` and `PDF version`. So a metadata or
PDF/A check needs no new library — only a stdlib XML parse of the XMP plus the existing
`pdfinfo` fields.

### 6.4 No language is declared for hyphenation, and the result is visible

No `set text(lang: ...)` and no `hyphenate:` setting exists anywhere in `typst/`, while
`metadata.languages` records the book's languages. A justified narrow-measure probe with
the pinned Typst produced:

Narrow measure, one column, `set par(justify: true)`, `pdftotext` output verbatim:

```
Ngoài ra, chương
trình nghiên cứu về
sự phát triển của
ngôn ngữ học so sánh
đã được triển khai
rộng khắp trên toàn
quốc trong nhiều
năm qua.
The extraordinarily
complicated interna­
tionalization
char­
acterization process
continues unabated.
```

Two defects in one page: Vietnamese gets no hyphenation at all (so the justified lines
stretch unevenly), and English broke `char-` and left the fragment alone on its own line.
WeasyPrint's default `hyphenate-limit-chars: (5, 2, 2)` exists precisely to forbid that
second outcome — a minimum of five characters in the word, two before the break, two
after it.

### 6.5 Bookify paginates with a fixed loop; WeasyPrint converges

`SPEC-publish-engine.md` §"Illustration placement rule" recompiles at most three times
and fails with `ILLUSTRATION_LIMIT` on a fourth disagreement. `layout_document()` instead
asks *did anything change* after each pass (`content_changed`, page-count-dependent
counters) and stops when nothing did, with a hard ceiling of eight as a safety net. Same
problem class, better convergence test: a stable layout is proven by absence of change,
not by running out of attempts.

---

## 7. Reusability classified

Each subsystem judged on three axes: can it run without the rest of WeasyPrint; is the
knowledge portable out of a CSS engine; is the licence clean for Bookify.

| Subsystem | Lines | Extractable? | Portable knowledge? | Verdict |
| --- | --- | --- | --- | --- |
| `pdf/metadata.py` + `pdf/pdfa.py` + `pdf/pdfua.py` + `pdf/tags.py` | ~900 | Runs inside pydyf, but the *field mapping and conformance obligations* are spec knowledge | **Yes — highest value** | **Adopt as a specification** |
| `css/counters.py` (`CounterStyle`) | 294 | Yes, pure Python, no imports beyond `urls` | Yes (CSS Counter Styles 3) | **Vendor only when needed** |
| `anchors.py::make_page_bookmark_tree` | 40 | No — needs page/bookmark tuples | Yes: the skipped-level nesting algorithm | **Read as reference** |
| `pdf/fonts.py` | 677 | No — cffi + HarfBuzz + pydyf | Partly: ToUnicode/subset obligations | **Reference only** |
| `layout/*` | 10,034 | No — bound to the box model and `LayoutContext` | Yes: break rules, convergence loop, page-side semantics | **Read as reference** |
| `text/*` | 2,152 | No — Pango through cffi | Partly: hyphenation limits, language-aware breaking | **Reference only** |
| `css/*` validation | 8,540 | Technically yes | Yes: a complete property/default table | Only if Bookify accepts CSS |
| `draw/*`, `svg/*` | 4,509 | No — pango-cairo, pydyf streams | No | **Not reusable** |
| `formatting_structure/*` | 2,434 | No — CSS box tree | Partly (anonymous box rules) | **Not reusable** |
| `urls.py::URLFetcher` | 195 | Yes (stdlib `urllib` subclass) | Yes: allow-list scheme policy | **Pattern, not code** |
| `tests/draw` pixel-map idiom | — | Test-only | **Yes**: legible render regressions | **Borrow the idiom** |

Summary of what is actually re-usable: **one specification (PDF metadata/conformance),
one algorithm (counter styles), one pattern (converging pagination), one test idiom
(pixel maps), one policy (URL allow-listing).** The engine itself is not reusable, because
Bookify's composition target is Typst, not CSS.

---

## 8. What would break if WeasyPrint replaced Typst

Recorded because it is the obvious question and deserves a concrete answer rather than a
preference.

1. **The design system is measured, not declared.** `typst/theme.typ` derives every
   leading from the pinned faces' measured metrics (0.660 em line box, 0.750 em ascent,
   0.240 em descent) and `verify` proves the result at 300 dpi. CSS's `line-height`
   model would replace that with a different box model, invalidating the rhythm
   baselines, the plate widths (475.28 pt), the 46 % side column and the cover ink gate.
2. **Figures.** Charts are Matplotlib vector output and diagrams are CeTZ; both land as
   PDF vectors through Typst. WeasyPrint would need them as SVG or raster, and its SVG
   support — while real (2,757 lines) — is a different renderer with different text
   metrics.
3. **The one-illustration-per-page rule** is enforced by a two-pass compile plus a
   placement map. Rebuilding it on top of CSS layout means re-implementing the rule in a
   different break model, with no gain.
4. **Toolchain purity.** Today the build needs one static Typst binary, Poppler and
   bwrap. WeasyPrint adds Pango, HarfBuzz, fontconfig and eight Python packages to the
   pinned set, all of which change rendering between versions by the project's own
   policy.
5. **The manuscript model.** Bookify's input is a closed YAML schema. WeasyPrint's input
   is HTML+CSS. Bridging means either generating HTML from the manuscript (a second
   renderer to keep in sync) or accepting HTML as a source format (a schema change).

None of these are fatal in isolation; together they mean a rewrite of the parts of
Bookify that are already verified, for no capability Bookify lacks — except the ones in
§3, which can be obtained without replacing anything.
